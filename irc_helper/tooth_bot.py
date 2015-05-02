#!/usr/bin/env python3
"""
A file that is focused on making a IRCHelper like Toothless, from #httyd.
"""

import os
import random
import sys
import re
import requests
import time
import json
from bs4 import BeautifulSoup

parent_directory = os.sep.join(os.path.abspath(__file__).split(os.sep)[:-2])
if parent_directory not in sys.path:
    sys.path.insert(0, parent_directory)

import irc_helper


# From Django
url_validator = re.compile(
    r"^(?:(?:http|ftp)s?://)"  # http:// or https://
    r"((?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|"  # domain...
    r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})"  # ...or ip
    r"(?::\d+)?"  # optional port
    r"(?:/?|[/?]\S+)$", re.IGNORECASE)

FLAGS = {
    "admin": "a",
    "whitelist": "w",
    "ignore": "i",
}


class ToothlessError(irc_helper.IRCError):
    pass


# noinspection PyUnusedLocal
class Toothless(irc_helper.IRCHelper):
    def __init__(self, config_file, close_afterwards=True):

        needed = ("user", "nick", "channel", "host", "port", "database_name")
        self.stomach = set()
        self.config = json.loads(config_file.read())
        self.messages = self.config.get("messages", {})
        self.connection = self.config.get("connection", {})
        if "user" not in self.connection and "user_name" in self.connection:
            self.connection["user"] = self.connection["user_name"]
            del self.connection["user_name"]
        if "password" in self.connection:
            # To Implement.
            pass
        if "server" in self.connection:
            self.connection["host"] = self.connection["server"].get("host") or self.connection["server"].get("address")
            self.connection["port"] = self.connection.get("port", 6667)
            del self.connection["server"]
        self.connection["database_name"] = self.config.get("database_name")

        super().__init__(**{k:v for k, v in self.connection.items() if k in needed})

        self.apply_commands()
        if close_afterwards:
            config_file.close()

    def handle_block(self, block):
        block_data = super().handle_block(block)
        if block_data.get("command", "").upper() == "JOIN":
            if FLAGS["ignore"] not in self.get_flags(block_data.get("sender", "")):
                greeting = random.choice(self.messages.get("greetings", ["doesn't know how to greet {nick}!"]))
                if "{nick}" in greeting:
                    greeting = greeting.format(nick=block_data.get("sender"))
                else:
                    greeting += block_data.get("sender", "")
                self.send_action(greeting)
        if block_data.get("sender") == "Toothless" and block_data.get("recipient") == self.nick:
            try:
                trigger, response = block_data.get("message", "").split(" -> ", 1)
            except ValueError:
                # Signifies that the message is not a command.
                pass
            else:
                @self.basic_command()
                def dummy():
                    return trigger, response
        return block_data

    def join_channel(self, channel):
        super().join_channel(channel)
        self.send_action(self.messages.get("announce_arrival", "enters the arena!"))

    def add_flag(self, username, flag):
        if flag in FLAGS:
            flag = FLAGS.get(flag)
        elif flag not in FLAGS.values():
            raise ToothlessError("Unknown flag! Valid flags are {}".format(", ".join(FLAGS.values())))
        self.irc_cursor.execute("SELECT * FROM Flags")
        if self.irc_cursor.fetchone() is None:
            self.irc_cursor.execute("INSERT INTO Flags VALUES (0,?,?)", (username, flag))
        else:
            self.irc_cursor.execute("SELECT * FROM Flags WHERE username=?", (username,))
            if self.irc_cursor.fetchone() is None:
                self.irc_cursor.execute("INSERT INTO Flags(username,flags) VALUES (?,?)", (username, flag))
            else:
                old_flags = self.get_flags(username)
                new_flags = "".join(sorted(old_flags + tuple(flag)))
                self.irc_cursor.execute("UPDATE Flags WHERE username=? SET flags=?", (username, new_flags))

    def get_flags(self, username):
        self.irc_cursor.execute("SELECT flags FROM Flags WHERE username=?", (username,))
        raw_flags = self.irc_cursor.fetchone()
        if raw_flags:
            raw_flags = raw_flags[0]
        else:
            raw_flags = ""
        return tuple(raw_flags)

    def apply_commands(self):
        """
        A base set of commands.
        Arguments:
            bot: A IRCHelper instance.
        Effect:
            Adds a bunch of sample commands to bot.
        """

        @self.advanced_command(False)
        def url_title(bot, message, sender):
            url_match = url_validator.search(message.strip())
            if not url_match:
                return
            req = requests.get(message.strip(), headers={"User-Agent": "Py3 TitleFinder"})
            if req.ok:
                soup = BeautifulSoup(req.text)
                bot.send_action(self.messages.get("urltitle", "finds the URL title to be: \"{title}\"").format(title=soup.title.text))
                # TODO Implement proper Youtube API
            else:
                bot.send_action("wasn't able to get URL info! [{}]".format(sender, req.status_code))

        @self.advanced_command(False)
        def learn_trigger(bot, message, sender):
            command = " ".join(message.split(" ")[:2]).lower()
            respond_to = (bot.nick.lower() + "! learn").lower()
            if command == respond_to and len(message.split("->", 1)) >= 2:
                if FLAGS["whitelist"] in bot.get_flags(sender):
                    bot.irc_cursor.execute("SELECT * FROM Commands WHERE trigger=? AND response=?",
                                           message.split(" ", 2)[2].split(" -> ", 1))
                    if bot.irc_cursor.fetchone() is None:
                        bot.send_action(self.messages.get("learn", "has been trained by {nick}!").format(nick=sender))

                        @self.basic_command()
                        def learn_comm():
                            return message.split(" ", 2)[2].split(" -> ", 1)
                    else:
                        bot.send_action(self.messages.get("learn_superfluous", "already knows that trick!"))
                elif FLAGS["whitelist"] not in bot.get_flags(sender):
                    bot.send_action(self.messages.get("learn_deny", "doesn't want to be trained by {nick}!").format(nick=sender))
                else:
                    bot.send_action(self.messages.get("learn_error", "tilts his head in confusion towards {nick}...").format(nick=sender))

        @self.advanced_command(False)
        def forget_trigger(bot, message, sender):
            command = " ".join(message.split(" ")[:2]).lower()
            respond_to = (bot.nick.lower() + "! forget").lower()
            if command == respond_to and len(message.split(" ")) >= 3:
                trigger = message.split(" ", 2)[2]
                bot.irc_cursor.execute("SELECT response FROM Commands WHERE trigger=?", (trigger,))
                response = (bot.irc_cursor.fetchone() or [None])[0]
                if response is not None:
                    bot.send_action(self.messages.get("forget", "forgot one of his tricks!").format(nick=sender))
                    bot.forget_basic_command(trigger)
                else:
                    bot.send_action(self.messages.get("forget_superfluous", "doesn't know that trick!").format(nick=sender))

        @self.advanced_command(False)
        def attack(bot, message, sender):
            command = " ".join(message.split(" ")[:2]).lower()
            respond_to = (bot.nick.lower() + "! attack").lower()
            if command == respond_to and len(message.split(" ")) >= 3:
                chosen_attack = random.choice(
                    self.messages.get("attacks", ["doesn't have a valid attack for {target}!"]))
                victim = message.split(" ")[2]
                if "{target}" in chosen_attack:
                    chosen_attack = chosen_attack.format(target=victim)
                else:
                    chosen_attack += victim
                bot.send_action(chosen_attack)

        @self.advanced_command(False)
        def eat(bot, message, sender):
            command = " ".join(message.split(" ")[:2]).lower()
            respond_to = (bot.nick.lower() + "! eat").lower()
            if command == respond_to and len(message.split(" ")) >= 3:
                victim = message.split(" ", 2)[2]
                if victim not in self.config.get("inedible_victims"):
                    bot.send_action(self.messages.get("eat", "gulps down {victim}!").format(victim=victim))
                    bot.stomach.add(victim)
                else:
                    bot.send_action(self.messages.get("eat_inedible", "doesn't feel like eating {victim}!").format(victim=victim))

        @self.advanced_command(False)
        def spit(bot, message, sender):
            bot.stomach = list(bot.stomach)
            command = " ".join(message.split(" ")[:2]).lower()
            respond_to = (bot.nick.lower() + "! spit").lower()
            if command == respond_to and len(message.split(" ")) >= 3:
                victim = message.split(" ", 2)[2]
                if victim in bot.stomach:
                    del bot.stomach[bot.stomach.index(victim)]
                    bot.send_action("spits out {}!".format(victim))
                else:
                    bot.send_action("hasn't eaten {} yet!".format(victim))
            bot.stomach = set(bot.stomach)

        @self.advanced_command(False)
        def show_stomach(bot, message, sender):
            command = " ".join(message.split(" ")[:2]).lower()
            respond_to = (bot.nick.lower() + "! stomach").lower()
            if command == respond_to:
                stomachs = ", ".join(bot.stomach)
                if stomachs:
                    bot.send_action("is digesting {}!".format(stomachs))
                else:
                    bot.send_action("hasn't eaten anything yet!")

        @self.advanced_command(False)
        def vomit(bot, message, sender):
            command = " ".join(message.split(" ")[:2]).lower()
            respond_to = (bot.nick.lower() + "! vomit").lower()
            if command == respond_to:
                if bot.stomach:
                    bot.send_action(self.messages.get("vomit", "empties his stomach!"))
                    bot.stomach = set()
                else:
                    bot.send_action(self.messages.get("vomit_superfluous", "hasn't eaten anything yet!"))

        @self.advanced_command(True)
        def clear_commands(bot, message, sender):
            if message.lower().strip() == "purge_commands" and FLAGS["admin"] in bot.get_flags(sender):
                bot.irc_cursor.execute()
                if not bot.irc_cursor.fetchall():
                    bot.send_action(self.messages.get("purge_commands_superfluous", "hasn't learned any tricks to forget!"), sender)
                else:
                    bot.irc_cursor.execute("DELETE FROM Commands")
                    bot.send_action(self.messages.get("purge_commands", "forgot all of his tricks!"), sender)

        @self.advanced_command(True)
        def whitelist(bot, message, sender):
            nicknames = message.lower().strip().split(" ")
            if nicknames[0] == "append_whitelist":
                for i in nicknames[1:]:
                    bot.add_flag(i, FLAGS["whitelist"])

        @self.advanced_command(True)
        def terminate(bot, message, sender):
            if message == "terminate" and FLAGS["admin"] in bot.get_flags(sender):
                raise KeyboardInterrupt

        @self.advanced_command(True)
        def list_commands(bot, message, sender):
            if message == "list_commands":
                bot.irc_cursor.execute("SELECT trigger,response FROM Commands")
                for trigger, response in bot.irc_cursor.fetchall():
                    bot.send_message(self.messages.get("print_command", "{trigger} -> {response}").format(trigger=trigger, response=response), sender)
                    time.sleep(.01)

        @self.advanced_command(True)
        def copy_original(bot, message, sender):
            if message == "copy_original" and FLAGS["admin"] in self.get_flags(sender):
                bot.copying = True
                bot.send_action(self.messages.get("copy_original", "will start copying the original."), sender)
                bot.send_message("list_commands", "Toothless")
                bot.irc_cursor.execute("SELECT * FROM Commands")

        @self.advanced_command(True)
        def add_flag_pm(bot, message, sender):
            if FLAGS["admin"] in bot.get_flags(sender) and message.split(" ")[0] == "add_flag":
                user, flag = message.split(" ")[1:3]
                bot.add_flag(user, flag)
                flags = "".join(bot.get_flags(user.lower()))
                bot.send_action(self.messages.get("flag_added", "succesfully added {flag} to {user}, new flags: {flags}.").format(user=user, flag=flag, flags=flags), sender)
