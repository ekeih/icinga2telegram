# Send your Icinga2 alerts to Telegram
# Copyright (C) 2018  Max Rosin
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

import click
import json
import logging
import pathlib
import telegram

from datetime import datetime
from emoji import emojize
from jinja2 import Template
from telegram.ext import CallbackQueryHandler, CommandHandler, Updater

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.DEBUG)
logging.getLogger('JobQueue').setLevel(logging.INFO)
logging.getLogger('telegram').setLevel(logging.INFO)
logging.getLogger('requests').setLevel(logging.INFO)
logging.getLogger('telegram.vendor.ptb_urllib3').setLevel(logging.ERROR)

SPOOL = '/tmp/icinga2telegram/spool'
pathlib.Path(SPOOL).mkdir(parents=True, exist_ok=True)

icinga2client = None


def acknowledge_host(hostname, author):
    """
    Acknowledge a host alert.
    :param hostname: The hostname.
    :param author: The author.
    """
    icinga2client.actions.acknowledge_problem(object_type='Host',
                                              filters='host.name == "{}"'.format(hostname),
                                              author=author,
                                              comment='ACK via icinga2telegram',
                                              sticky=False,
                                              notify=True)


def acknowledge_service(hostname, servicename, author):
    """
    Acknowledge a service alert.
    :param hostname: The hostname.
    :param servicename: The servicename.
    :param author: The author.
    """
    icinga2client.actions.acknowledge_problem(object_type='Service',
                                              filters='host.name == "{}" && service.name "{}"'.format(hostname, servicename),
                                              author=author,
                                              comment='ACK via icinga2telegram',
                                              sticky=False,
                                              notify=True)


def handler_start(bot, update):
    """Telegram command handler for /start and /whoami. Sends the chat ID to the user."""
    logging.debug('{}: start/whois handler'.format(update.message.chat_id))
    bot.send_message(chat_id=update.message.chat_id, text='Your chat ID is: {}'.format(update.message.chat_id))


def handler_acknowledge(_, update):
    """Telegram query handler to acknowledge an alert."""
    logging.debug('{}: acknowledge handler for message {}'.format(update.callback_query.message.chat_id, update.callback_query.data))
    try:
        spool_file_path = '{}/{}-{}.json'.format(SPOOL,update.callback_query.message.chat_id, update.callback_query.data)

        with open(spool_file_path, 'r') as spool_file:
            logging.debug('{}: Reading message from {}'.format(update.callback_query.message.chat_id, spool_file_path))
            spool_content = json.load(spool_file)

        if 'servicename' in spool_content:
            acknowledge_service(spool_content['hostname'], spool_content['servicename'], update.callback_query.from_user.mention_markdown())
        else:
            acknowledge_host(spool_content['hostname'], update.callback_query.from_user.mention_markdown())

        update.callback_query.message.edit_text(update.callback_query.message.text_markdown,
                                                parse_mode = telegram.ParseMode.MARKDOWN,
                                                disable_web_page_preview = True)
        pathlib.Path(spool_file_path).unlink()
    except Exception as e:
        logging.error('Unable to acknowledge the alert: {}'.format(e))
        update.callback_query.answer(text='Unable to acknowledge the alert. Please use icingaweb2 instead.')


@click.group()
def cli():
    pass


@cli.command()
@click.option('--token', required=True, help='API token of the Telegram bot')
@click.option('--icinga2-cacert', help='CA certificate of your Icinga2 API')
@click.option('--icinga2-api-url', required=True, help='Icinga2 API URL/')
@click.option('--icinga2-api-user', required=True, help='Icinga2 API user')
@click.option('--icinga2-api-password', required=True, help='Icinga2 API password')
def daemon(token, icinga2_cacert, icinga2_api_url, icinga2_api_user, icinga2_api_password):
    global icinga2client
    try:
        import icinga2api.client
    except ImportError:
        import sys
        logging.error('If you want to run icinga2telegram as a daemon to handle acknowledgements you need to install icinga2api.')
        sys.exit(1)
    icinga2client = icinga2api.client.Client(url=icinga2_api_url,
                                             username=icinga2_api_user,
                                             password=icinga2_api_password,
                                             ca_certificate=icinga2_cacert)
    updater = Updater(token=token)
    dispatcher = updater.dispatcher
    dispatcher.add_handler(CommandHandler('start', handler_start))
    dispatcher.add_handler(CommandHandler('whoami', handler_start))
    dispatcher.add_handler(CallbackQueryHandler(handler_acknowledge))
    updater.start_polling()
    updater.idle()


@cli.command()
@click.option('--token', required=True, help='API token of the Telegram bot')
@click.option('--chat', required=True, help='Chat ID if the Telegram chat')
@click.option('--time', required=True, type=click.INT, help='Time of the event as a UNIX timestamp')
@click.option('--timeformat', default='%H:%M:%S %d.%m.%Y', help='Output format of the time (default: %H:%M:%S %d.%m.%Y)')
@click.option('--emoji/--no-emoji', default=True, help='Enable or disable a helpful status emoji at the beginning of the message')
@click.option('--hostname', required=True)
@click.option('--hostdisplayname')
@click.option('--hostoutput')
@click.option('--hoststate', required=True, type=click.Choice(['UP', 'DOWN']))
@click.option('--address', required=True)
@click.option('--address6')
@click.option('--servicename')
@click.option('--servicedisplayname')
@click.option('--serviceoutput')
@click.option('--servicestate', type=click.Choice(['OK', 'WARNING', 'CRITICAL', 'UNKNOWN']))
@click.option('--notification-type', required=True, type=click.Choice(['ACKNOWLEDGEMENT', 'CUSTOM', 'DOWNTIMEEND', 'DOWNTIMEREMOVED', 'DOWNTIMESTART', 'FLAPPINGEND', 'FLAPPINGSTART', 'PROBLEM', 'RECOVERY']))
@click.option('--notification-author')
@click.option('--notification-comment')
@click.option('--icingaweb2url', required=True)
@click.option('--ack/--no-ack', default=False, help='Enable or disable the acknowledgement button for alerts. (Disabled by default.)')
def notification(token, chat, time, timeformat, emoji,
        hostname, hostdisplayname, hostoutput, hoststate, address, address6,
        servicename, servicedisplayname, serviceoutput, servicestate,
        notification_type, notification_author, notification_comment, icingaweb2url, ack):

    hostdisplayname = hostname if hostdisplayname is None else hostdisplayname
    time_human = datetime.fromtimestamp(time).strftime(timeformat)

    if servicename:
        servicedisplayname = servicename if servicedisplayname is None else servicedisplayname

    if emoji:
        if notification_type == 'ACKNOWLEDGEMENT':
            emoji_emojize = ':heavy_check_mark:'
        elif notification_type == 'CUSTOM':
            emoji_emojize = ':information_source:'
        elif notification_type == 'DOWNTIMEEND':
            emoji_emojize = ':play_button:'
        elif notification_type == 'DOWNTIMEREMOVED':
            emoji_emojize = ':eject_button:'
        elif notification_type == 'DOWNTIMESTART':
            emoji_emojize = ':stop_button:'
        elif notification_type == 'FLAPPINGEND':
            emoji_emojize = ':shuffle_tracks_button:'
        elif notification_type == 'FLAPPINGSTART':
            emoji_emojize = ':shuffle_tracks_button:'
        elif notification_type == 'PROBLEM':
            if servicestate is not None:
                if servicestate == 'CRITICAL':
                    emoji_emojize = ':broken_heart:'
                elif servicestate == 'WARNING':
                    emoji_emojize = ':yellow_heart:'
                else:
                    emoji_emojize = ':purple_heart:'
            else:
                emoji_emojize = ':broken_heart:'
        elif notification_type == 'RECOVERY':
            emoji_emojize = ':green_heart:'
        else:
            emoji_emojize = ':information_source:'
        emoji_emojized = emojize(emoji_emojize + ' ', use_aliases=True)
    else:
        emoji_emojized = ''

    template = Template("""
{% if servicename %}
{{ emoji_emojized }}{{ notification_type }} - [{{ servicedisplayname }}]({{ icingaweb2url }}/monitoring/service/show?host={{ hostname }}&service={{ servicename }}) is {{ servicestate }}
{% else %}
{{ emoji_emojized }}{{ notification_type }} - [{{ hostdisplayname }}]({{ icingaweb2url }}/monitoring/host/show?host={{ hostname }}) is {{ hoststate }}
{% endif %}

Host: [{{ hostdisplayname }}]({{ icingaweb2url }}/monitoring/host/show?host={{ hostname }}) ({{ hoststate }})
Address: {{ address }}
{% if address6 != None %}
Address: {{ address6 }}
{% endif %}
Date: {{ time }}

{% if servicename and serviceoutput %}
```
{{ serviceoutput }}
```
{% elif not servicename and hostoutput %}
```
{{ hostoutput }}
```
{% endif %}
{% if notification_author %}{{ notification_author }}{% endif %}{% if notification_comment %}: {{ notification_comment }}{% endif %}
""", trim_blocks=True)

    message_text = template.render(time = time_human, emoji_emojized = emoji_emojized, hostname = hostname, hostdisplayname = hostdisplayname,
                                   hostoutput = hostoutput, hoststate = hoststate, address = address, address6 = address6,
                                   servicename = servicename, servicedisplayname = servicedisplayname,
                                   serviceoutput = serviceoutput, servicestate = servicestate,
                                   notification_type = notification_type, notification_author = notification_author,
                                   notification_comment = notification_comment, icingaweb2url = icingaweb2url)

    bot = telegram.Bot(token=token)
    message = bot.send_message(chat, message_text, parse_mode=telegram.ParseMode.MARKDOWN, disable_web_page_preview=True)

    if notification_type == 'PROBLEM' and ack:
        keyboard = [[telegram.InlineKeyboardButton('Acknowledge', callback_data=message.message_id)]]
        reply_markup = telegram.InlineKeyboardMarkup(keyboard)

        message.edit_text(message_text, parse_mode=telegram.ParseMode.MARKDOWN, disable_web_page_preview=True, reply_markup=reply_markup)

        if servicename:
            spool_content = {
                'chat_id': message.chat_id,
                'message_id': message.message_id,
                'hostname': hostname,
                'servicename': servicename,
            }
        else:
            spool_content = {
                'chat_id': message.chat_id,
                'message_id': message.message_id,
                'hostname': hostname,
            }

        spool_file_path = '{}/{}-{}.json'.format(SPOOL, message.chat_id, message.message_id)

        with open(spool_file_path, 'w') as spool_file:
            logging.debug('{}: Storing message in {}'.format(message.chat_id, spool_file_path))
            json.dump(spool_content, spool_file, indent=2)
