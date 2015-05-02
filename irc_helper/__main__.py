#!/usr/bin/env python3
# Since Imports are based on sys.path, we need to add the parent directory.
import os
import sys

parent_directory = os.sep.join(os.path.abspath(__file__).split(os.sep)[:-2])
if parent_directory not in sys.path:
    sys.path.insert(0, parent_directory)

import irc_helper


bot = irc_helper.Toothless(open("config.json"))

try:
    bot.run()
except KeyboardInterrupt:
    pass
finally:
    bot.quit(bot.messages.get("disconnect", "Gotta go save Hiccup from yet another gliding accident..."))