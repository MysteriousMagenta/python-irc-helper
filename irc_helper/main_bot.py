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

FLAGS = {
    "admin": "a",
    "whitelisted": "w",
    "ignored": "i",
}

class IRCHelper(IRCBot):
    def __init__(self, database_name, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.channel_commands = []
        self.private_commands = []
        self.command_database = sqlite3.connect(database_name)
        self.irc_cursor = self.command_database.cursor()
        self.irc_cursor.execute("SELECT name FROM sqlite_master WHERE type=\"table\"")
        tables = tuple(map(lambda x: x[0], self.irc_cursor.fetchall()))
        if "Commands" not in tables:
            self.irc_cursor.execute("CREATE TABLE Commands (id INTEGER PRIMARY KEY, trigger TEXT, response TEXT)")
        if "Flags" not in tables:
            self.irc_cursor.execute("CREATE TABLE Flags (id INTEGER PRIMARY KEY, username TEXT, flags TEXT)")

    # To add a command.
    # For commands that are functions.
    def advanced_command(self, private_message=False):
        return self.channel_commands.append if not private_message else self.private_commands.append

    # Use this if your function returns (trigger, command)
    def basic_command(self, *args, **kwargs):
        def basic_decorator(command):
            trigger, response = command(*args, **kwargs)
            self.irc_cursor.execute("SELECT * FROM Commands")
            if self.irc_cursor.fetchone() is None:
                self.irc_cursor.execute("INSERT INTO Commands VALUES (0,?,?)", (trigger, response))
            else:
                self.irc_cursor.execute("SELECT trigger FROM Commands WHERE trigger=? AND response=?",
                                            (trigger, response))
                if self.irc_cursor.fetchone() is None:
                    self.irc_cursor.execute("INSERT INTO Commands(trigger,response) VALUES (?,?)",
                                                (trigger, response))
            return command
        return basic_decorator

    def forget_basic_command(self, trigger):
        self.irc_cursor.execute("DELETE FROM Commands WHERE trigger=?", (trigger,))


    def handle_block(self, block):
        block_data = super().handle_block(block)
        if block_data.get("message"):
            if block_data.get("recipient") == self.channel:
                command_list = self.channel_commands
            elif block_data.get("recipient") == self.nick:
                command_list = self.private_commands
            else:
                command_list = []
            for func_command in command_list:
                if func_command(self, block_data.get("message"), block_data.get("sender")) is not None:
                    break
            self.irc_cursor.execute("SELECT trigger,response FROM Commands")
            for trigger, response in self.irc_cursor.fetchall():
                matched = re.match(trigger, block_data.get("message", ""))
                if matched:
                    self.send_message(response.replace("${nick}", block_data.get("sender")))
                    break

    def quit(self):
        self.leave_channel()
        self.socket.close()
        self.command_database.commit()
        self.command_database.close()