#!/usr/bin/env python3
# Since Imports are based on sys.path, we need to add the parent directory.
import inspect
import os
import sys
import sqlite3
import re


parent_directory = os.sep.join(os.path.abspath(__file__).split(os.sep)[:-2])
if parent_directory not in sys.path:
    sys.path.insert(0, parent_directory)

from irc_helper import IRCBot


class IRCHelper(IRCBot):
    def __init__(self, database_name, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.commands = []
        self.database = sqlite3.connect(database_name)
        self.cursor = self.database.cursor()
        self.cursor.execute("SELECT name FROM sqlite_master WHERE type=\"table\"")
        tables = tuple(map(lambda x: x[0], self.cursor.fetchall()))
        if "Commands" not in tables:
            self.cursor.execute("CREATE TABLE Commands (id INTEGER PRIMARY KEY, trigger TEXT, response TEXT)")

    # To add a command.
    # For commands that are functions.
    def advanced_command(self, *args, **kwargs):
        return self.commands.append

    # Use this if your function returns (trigger, command)
    def basic_command(self, *args, **kwargs):
        def basic_decorator(command):
            trigger, response = command(*args, **kwargs)
            self.cursor.execute("SELECT * FROM Commands")
            if self.cursor.fetchone() is None:
                self.cursor.execute("INSERT INTO Commands VALUES (0,?,?)", (trigger, response))
            else:
                self.cursor.execute("INSERT INTO Commands(trigger,response) VALUES (?,?)", (trigger, response))
            return command
        return basic_decorator

    def handle_block(self, block):
        block_data = super().handle_block(block)
        if block_data.get("message"):
            for func_command in self.commands:
                if func_command(self, block_data.get("message"), block_data.get("sender")) is not None:
                    break
            self.cursor.execute("SELECT trigger,response FROM Commands")
            for trigger, response in self.cursor.fetchall():
                matched = re.match(trigger, block_data.get("message", ""))
                if matched:
                    self.send_message(response)
                    break

    def quit(self):
        self.database.close()