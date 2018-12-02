import click
import telegram

from datetime import datetime
from emoji import emojize
from jinja2 import Template

hoststates = {
    0: 'UP',
    1: 'DOWN'
}

servicestates = {
    0: 'OK',
    1: 'WARNING',
    2: 'CRITICAL',
    3: 'UNKNOWN',
    None: None
}

@click.command()
@click.option('--token', required=True, help='API token of the Telegram bot')
@click.option('--chat', required=True, help='Chat ID if the Telegram chat')
@click.option('--time', required=True, type=click.INT, help='Time of the event as a UNIX timestamp')
@click.option('--timeformat', default='%H:%M:%S %d.%m.%Y', help='Output format of the time (default: %H:%M:%S %d.%m.%Y)')
@click.option('--emoji/--no-emoji', default=True, help='Enable or disable a helpful status emoji at the beginning of the message')
@click.option('--hostname', required=True)
@click.option('--hostdisplayname')
@click.option('--hostoutput')
@click.option('--hoststate', required=True, type=click.IntRange(min=0, max=1))
@click.option('--address', required=True)
@click.option('--address6')
@click.option('--servicename')
@click.option('--servicedisplayname')
@click.option('--serviceoutput')
@click.option('--servicestate', type=click.IntRange(min=0, max=3))
@click.option('--notification-type', required=True, type=click.Choice(['Acknowledgement', 'Custom', 'DowntimeEnd', 'DowntimeRemoved', 'DowntimeStart', 'FlappingEnd', 'FlappingStart', 'Problem', 'Recovery']))
@click.option('--notification-author')
@click.option('--notification-comment')
@click.option('--icingaweb2url', required=True)
def cli(token, chat, time, timeformat, emoji,
        hostname, hostdisplayname, hostoutput, hoststate, address, address6,
        servicename, servicedisplayname, serviceoutput, servicestate,
        notification_type, notification_author, notification_comment, icingaweb2url):

    hoststate_human = hoststates[hoststate]
    hostdisplayname = hostname if hostdisplayname is None else hostdisplayname
    time_human = datetime.fromtimestamp(time).strftime(timeformat)

    servicestate_human = servicestates[servicestate]
    if servicename:
        servicedisplayname = servicename if servicedisplayname is None else servicedisplayname

    if emoji:
        if notification_type == 'Acknowledgement':
            emoji_emojize = ':heavy_check_mark:'
        elif notification_type == 'Custom':
            emoji_emojize = ':information_source:'
        elif notification_type == 'DowntimeEnd':
            emoji_emojize = ':play_button:'
        elif notification_type == 'DowntimeRemoved':
            emoji_emojize = ':eject_button:'
        elif notification_type == 'DowntimeStart':
            emoji_emojize = ':stop_button:'
        elif notification_type == 'FlappingEnd':
            emoji_emojize = ':shuffle_tracks_button:'
        elif notification_type == 'FlappingStart':
            emoji_emojize = ':shuffle_tracks_button:'
        elif notification_type == 'Problem':
            if servicestate is not None:
                if servicestate == 2:
                    emoji_emojize = ':broken_heart:'
                elif servicestate == 1:
                    emoji_emojize = ':yellow_heart:'
                else:
                    emoji_emojize = ':purple_heart:'
            else:
                emoji_emojize = ':broken_heart:'
        elif notification_type == 'Recovery':
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
""", trim_blocks=True)

    message = template.render(time = time_human, emoji_emojized = emoji_emojized, hostname = hostname, hostdisplayname = hostdisplayname,
                              hostoutput = hostoutput, hoststate = hoststate_human, address = address, address6 = address6,
                              servicename = servicename, servicedisplayname = servicedisplayname,
                              serviceoutput = serviceoutput, servicestate = servicestate_human,
                              notification_type = notification_type, notification_author = notification_author,
                              notification_comment = notification_comment, icingaweb2url = icingaweb2url)

    bot = telegram.Bot(token=token)
    bot.send_message(chat, message, parse_mode=telegram.ParseMode.MARKDOWN, disable_web_page_preview=True)