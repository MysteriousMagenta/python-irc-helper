#!/usr/bin/env python3
# Since Imports are based on sys.path, we need to add the parent directory.
import os
import sys
import sqlite3
import re
import requests

import time

from bs4 import BeautifulSoup

# From Django
url_validator = re.compile(
    r"^(?:(?:http|ftp)s?://)"  # http:// or https://
    r"((?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|"  # domain...
    r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})"  # ...or ip
    r"(?::\d+)?"  # optional port
    r"(?:/?|[/?]\S+)$", re.IGNORECASE)

parent_directory = os.sep.join(os.path.abspath(__file__).split(os.sep)[:-2])
if parent_directory not in sys.path:
    sys.path.insert(0, parent_directory)

from irc_helper import IRCBot, IRCError

FLAGS = {
    "admin": "a",
    "whitelist": "w",
    "ignore": "i",
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
        if block_data.get("sender") != self.user and block_data.get("message"):
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

    def add_flag(self, username, flag):
        if flag in FLAGS:
            flag = FLAGS.get(flag)
        elif flag not in FLAGS.values():
            raise IRCError("Unknown flag! Valid flags are {}".format(", ".join(FLAGS.values())))
        self.irc_cursor.execute("SELECT * FROM Flags WHERE username=?", (username,))
        if self.irc_cursor.fetchone() is None:
            self.irc_cursor.execute("INSERT INTO Flags VALUES (0,?,?)", (username, flag))
        else:
            old_flags = self.get_flags(username)
            new_flags = "".join(sorted(old_flags + flag))
            self.irc_cursor.execute("UPDATE Flags WHERE username=? SET flags=?", (username, new_flags))

    def get_flags(self, username):
        self.irc_cursor.execute("SELECT flags FROM Flags WHERE username=?", (username,))
        raw_flags = self.irc_cursor.fetchone()
        if raw_flags:
            raw_flags = raw_flags[0]
        else:
            raw_flags = ""
        return tuple(raw_flags)

    def quit(self):
        self.started = False
        self.leave_channel()
        self.socket.close()
        self.command_database.commit()
        self.command_database.close()

    @staticmethod
    def apply_commands(bot):
        """
        A base set of commands.
        Arguments:
            bot: A IRCHelper instance.
        Effect:
            Adds a bunch of sample commands to bot.
        """

        @bot.advanced_command(False)
        def url_title(bot_, message, sender):
            url_match = url_validator.search(message.strip())
            if not url_match:
                return
            req = requests.get(message.strip(), headers={"User-Agent": "Py3 TitleFinder"})
            if req.ok:
                soup = BeautifulSoup(req.text)
                bot_.send_message("{}: The URL title is \"{}\"".format(sender, soup.title.text))
                # TODO Implement proper Youtube API
            else:
                bot_.send_message("{}: Wasn't able to get URL info! [{}]".format(sender, req.status_code))
            return True

        @bot.advanced_command(False)
        def learn_trigger(bot_, message, sender):
            command = " ".join(message.split(" ")[:2]).lower()
            respond_to = (bot_.nick.lower() + "! learn").lower()
            if command == respond_to and len(message.split("->", 1)) >= 2 and FLAGS["whitelist"] in bot_.get_flags(
                    sender):
                bot_.send_message("Has learned {}!".format(message.split(" ", 2)[2]))

                @bot.basic_command()
                def learn_comm():
                    return message.split(" ", 2)[2].split(" -> ", 1)
            return command == respond_to or None

        @bot.advanced_command(False)
        def forget_trigger(bot_, message, sender):
            command = " ".join(message.split(" ")[:2]).lower()
            respond_to = (bot_.nick.lower() + "! forget").lower()
            if command == respond_to and len(message.split(" ")) >= 3:
                bot_.forget_basic_command(message.split(" ", 2)[2])
            return command == respond_to or None

        @bot.advanced_command(False)
        def attack(bot_, message, sender):
            command = " ".join(message.split(" ")[:2]).lower()
            respond_to = (bot_.nick.lower() + "! attack").lower()
            if command == respond_to and len(message.split(" ")) >= 3:
                bot_.send_action("pounces on {}!".format(message.split(" ")[1]))
            return command == respond_to or None

        @bot.advanced_command(False)
        def eat(bot_, message, sender):
            command = " ".join(message.split(" ")[:2]).lower()
            respond_to = (bot_.nick.lower() + "! eat").lower()
            if command == respond_to and len(message.split(" ")) >= 3:
                victim = message.split(" ", 2)[2]
                bot_.send_action("eats {}!".format(victim))
                if "stomach" not in bot_.__dict__:
                    bot_.stomach = []
                bot_.stomach.append(victim)
            return command == respond_to or None

        @bot.advanced_command(False)
        def spit(bot_, message, sender):
            command = " ".join(message.split(" ")[:2]).lower()
            respond_to = (bot_.nick.lower() + "! spit").lower()
            if command == respond_to and len(message.split(" ")) >= 3:
                victim = message.split(" ", 2)[2]
                if "stomach" not in bot_.__dict__:
                    bot_.stomach = []
                try:
                    victim_id = bot_.stomach.index(victim)
                except ValueError:
                    return
                else:
                    if victim_id != -1:
                        del bot_.stomach[victim_id]
                        bot_.send_action("spits out {}!".format(victim))
            return command == respond_to or None

        @bot.advanced_command(False)
        def show_stomach(bot_, message, sender):
            command = " ".join(message.split(" ")[:2]).lower()
            respond_to = (bot_.nick.lower() + "! stomach").lower()
            if "stomach" not in bot_.__dict__:
                bot_.stomach = []
            if command == respond_to:
                stomachs = ", ".join(bot_.stomach)
                if stomachs:
                    bot_.send_action("has eaten {}".format(stomachs))
            return command == respond_to or None

        @bot.advanced_command(False)
        def vomit(bot_, message, sender):
            if "stomach" not in bot_.__dict__:
                bot_.stomach = []
            command = " ".join(message.split(" ")[:2]).lower()
            respond_to = (bot_.nick.lower() + "! vomit").lower()
            if command == respond_to:
                if bot_.stomach:
                    bot_.send_action("spits out everyone!")
                    bot_.stomach = []
                else:
                    bot_.send_action("hasn't eaten anyone!")
            return command == respond_to or None

        @bot.advanced_command(True)
        def clear_commands(bot_, message, sender):
            if message.lower().strip() == "purge_commands" and FLAGS["admin"] in bot_.get_flags(sender):
                bot_.cursor.execute("DELETE FROM Commands")

        @bot.advanced_command(True)
        def whitelist(bot_, message, sender):
            nicknames = message.lower().strip().split(" ")
            if nicknames[0] == "append_whitelist":
                for i in nicknames[1:]:
                    bot_.add_flag(i, FLAGS["whitelist"])

        @bot.advanced_command(True)
        def terminate(bot_, message, sender):
            if message == "terminate" and FLAGS["admin"] in bot_.get_flags(sender):
                bot_.quit()

        @bot.advanced_command(True)
        def list_commands(bot_, message, sender):
            if message == "list_commands":
                bot_.irc_cursor.execute("SELECT trigger,response FROM Commands")
                for trigger, response in bot_.irc_cursor.fetchall():
                    bot_.send_message("{} -> {}".format(trigger, response), sender)
                    time.sleep(.01)
