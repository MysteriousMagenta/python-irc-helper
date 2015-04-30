#!/usr/bin/env python3
from irc_helper import IRCBot
import json

needed = ("nick", "user", "channel", "port", "host")
with open("config.json") as config_file:
    config = json.loads(config_file.read())

IRCBot(**{x:y for x, y in config.items() if x in needed}).run()