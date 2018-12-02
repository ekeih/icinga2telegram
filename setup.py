from setuptools import setup

setup(
    name='icinga2-telegram',
    version='0.1',
    py_modules=['icinga2-telegram'],
    install_requires=[
        'Click',
        'emoji',
        'Jinja2',
        'python-telegram-bot',
    ],
    entry_points='''
        [console_scripts]
        icinga2-telegram=main:cli
    ''',
)
