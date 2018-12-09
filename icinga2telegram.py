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
import telegram

from datetime import datetime
from emoji import emojize
from jinja2 import Template

@click.command()
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
def cli(token, chat, time, timeformat, emoji,
        hostname, hostdisplayname, hostoutput, hoststate, address, address6,
        servicename, servicedisplayname, serviceoutput, servicestate,
        notification_type, notification_author, notification_comment, icingaweb2url):

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

    message = template.render(time = time_human, emoji_emojized = emoji_emojized, hostname = hostname, hostdisplayname = hostdisplayname,
                              hostoutput = hostoutput, hoststate = hoststate, address = address, address6 = address6,
                              servicename = servicename, servicedisplayname = servicedisplayname,
                              serviceoutput = serviceoutput, servicestate = servicestate,
                              notification_type = notification_type, notification_author = notification_author,
                              notification_comment = notification_comment, icingaweb2url = icingaweb2url)

    bot = telegram.Bot(token=token)
    bot.send_message(chat, message, parse_mode=telegram.ParseMode.MARKDOWN, disable_web_page_preview=True)
