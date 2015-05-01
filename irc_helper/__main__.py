#!/usr/bin/env python3
# Since Imports are based on sys.path, we need to add the parent directory.
import os
import sys
parent_directory = os.sep.join(os.path.abspath(__file__).split(os.sep)[:-2])
if parent_directory not in sys.path:
    sys.path.insert(0, parent_directory)

import irc_helper
import json


with open("config.json") as config_file:
    config = json.loads(config_file.read())


bot = irc_helper.IRCHelper(**config)
irc_helper.IRCHelper.apply_commands(bot)

try:
    bot.run()
except (Exception, KeyboardInterrupt) as e:
    bot.quit()
    if not isinstance(e, KeyboardInterrupt):
        raise
else:
    bot.quit()