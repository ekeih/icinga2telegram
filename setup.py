from setuptools import setup

with open("README.md", "r") as fh:
    long_description = fh.read()

setup(
    name='icinga2telegram',
    version='0.2.2',
    author='Max Rosin',
    url='https://github.com/ekeih/icinga2telegram',
    author_email='git@hackrid.de',
    description='Send your Icinga2 alerts to Telegram',
    long_description=long_description,
    long_description_content_type='text/markdown',
    license='LICENSE',
    py_modules=['icinga2telegram'],
    install_requires=[
        'Click',
        'emoji',
        'Jinja2',
        'python-telegram-bot',
    ],
    entry_points='''
        [console_scripts]
        icinga2telegram=icinga2telegram:cli
    ''',
)
