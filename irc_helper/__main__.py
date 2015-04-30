#!/usr/bin/env python3
# A Classic Example of "Why does this work?!"
import os
import sys
parent_directory = os.sep.join(os.path.abspath(__file__).split(os.sep)[:-2])
if parent_directory not in sys.path:
    sys.path.insert(0, parent_directory)

import irc_helper
import json


needed = ("nick", "user", "channel", "port", "host")
with open("config.json") as config_file:
    config = json.loads(config_file.read())

irc_helper.IRCBot(**{x:y for x, y in config.items() if x in needed}).run()