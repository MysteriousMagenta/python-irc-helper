#!/usr/bin/env python3
"""
A file that is focused on making a IRCHelper like Toothless, from #httyd.
"""

import os
import random
import sys
import re
import requests
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

    def __init__(self, config_file):

        needed = ("user", "nick", "channel", "host", "port", "database_name", "response_delay")
        self.stomach = set()
        self.config_file = config_file
        self.config = json.loads(self.config_file.read())
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

        super().__init__(**{k: v for k, v in self.connection.items() if k in needed})

        self.apply_commands()
        self.add_flag("MysteriousMagenta", "a")



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
        username = username.lower()
        if flag in FLAGS:
            flag = FLAGS[flag]
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
                new_flags = "".join(sorted(set(old_flags + tuple(flag))))
                self.irc_cursor.execute("UPDATE Flags SET flags=? WHERE username=?", (new_flags, username))

    def remove_flag(self, username, flag):
        username, flag = username.lower(), flag.lower()
        if flag in FLAGS:
            flag = FLAGS.get(flag)
        elif flag not in FLAGS.values():
            raise ToothlessError("Unknown flag! Valid flags are {}".format(", ".join(FLAGS.values())))
        old_flags = self.get_flags(username)
        new_flags = "".join(old_flags).replace(flag, "")
        self.irc_cursor.execute("UPDATE Flags SET flags=? WHERE username=?", (new_flags, username))

    def get_flags(self, username):
        username = username.lower()
        self.irc_cursor.execute("SELECT flags FROM Flags WHERE username=?", (username,))
        raw_flags = self.irc_cursor.fetchone()
        if raw_flags:
            raw_flags = raw_flags[0]
        else:
            raw_flags = ""
        return tuple(raw_flags)

    def has_flag(self, flag, username):
        flag, username = flag.lower(), username.lower()
        if flag in FLAGS:
            flag = FLAGS[flag].lower()
        elif flag not in FLAGS.items():
            raise ToothlessError("Unknown flag! Valid flags are {}".format(", ".join(FLAGS.values())))
        flags = self.get_flags(username)
        return flag in flags

    def apply_commands(self):
        """
        A base set of commands.
        Arguments:
            bot: A IRCHelper instance.
        Effect:
            Adds a bunch of sample commands to bot.
        """

        @self.advanced_command(False)
        def url_title(bot: Toothless, message: str, sender: str):
            url_match = url_validator.search(message.strip())
            if not url_match:
                return
            req = requests.get(message.strip(), headers={"User-Agent": "Py3 TitleFinder"})
            if req.ok:
                soup = BeautifulSoup(req.text)
                bot.send_action(self.messages.get("urltitle", "finds the URL title to be: \u0002\"{title}\"").format(
                    title=soup.title.text))
                # TODO Implement proper Youtube API
            else:
                bot.send_action("wasn't able to get URL info! [{}]".format(sender, req.status_code))

        @self.advanced_command(False)
        def learn_trigger(bot: Toothless, message: str, sender: str):
            command = " ".join(message.split(" ")[:2]).lower()
            respond_to = (bot.nick.lower() + "! learn").lower()
            if command == respond_to and len(message.split("->", 1)) >= 2:
                if bot.has_flag("whitelist", sender) or bot.has_flag("admin", sender):
                    bot.irc_cursor.execute("SELECT * FROM Commands WHERE trigger=? AND response=?",
                                           message.split(" ", 2)[2].split(" -> ", 1))
                    if bot.irc_cursor.fetchone() is None:
                        bot.send_action(self.messages.get("learn", "has been trained by {nick}!").format(nick=sender))

                        @self.basic_command()
                        def learn_comm():
                            return message.split(" ", 2)[2].split(" -> ", 1)
                    else:
                        bot.send_action(self.messages.get("learn_superfluous", "already knows that trick!"))
                elif not bot.has_flag("whitelist", sender):
                    bot.send_action(
                        self.messages.get("learn_deny", "doesn't want to be trained by {nick}!").format(nick=sender))
                else:
                    bot.send_action(
                        self.messages.get("learn_error", "tilts his head in confusion towards {nick}...").format(
                            nick=sender))

        @self.advanced_command(False)
        def forget_trigger(bot: Toothless, message: str, sender: str):
            command = " ".join(message.split(" ")[:2]).lower()
            respond_to = (bot.nick.lower() + "! forget").lower()
            if (bot.has_flag("whitelist", sender) or bot.has_flag("admin", sender)) and command == respond_to and len(
                    message.split(" ")) >= 3:
                trigger = message.split(" ", 2)[2]
                bot.irc_cursor.execute("SELECT response FROM Commands WHERE trigger=?", (trigger,))
                response = (bot.irc_cursor.fetchone() or [None])[0]
                if response is not None:
                    bot.send_action(self.messages.get("forget", "forgot one of his tricks!").format(nick=sender))
                    bot.forget_basic_command(trigger)
                else:
                    bot.send_action(
                        self.messages.get("forget_superfluous", "doesn't know that trick!").format(nick=sender))

        @self.advanced_command(False)
        def attack(bot: Toothless, message: str, sender: str):
            command = " ".join(message.split(" ")[:2]).lower()
            respond_to = (bot.nick.lower() + "! attack").lower()
            if command == respond_to and len(message.split(" ")) >= 3:
                chosen_attack = random.choice(
                    self.messages.get("attacks", ["doesn't have a valid attack for {target}!"]))
                victim = message.split(" ", 2)[2]
                if "{target}" in chosen_attack:
                    chosen_attack = chosen_attack.format(target=victim)
                else:
                    chosen_attack += victim
                bot.send_action(chosen_attack)

        @self.advanced_command(False)
        def eat(bot: Toothless, message: str, sender: str):
            command = " ".join(message.split(" ")[:2]).lower()
            respond_to = (bot.nick.lower() + "! eat").lower()
            if command == respond_to and len(message.split(" ")) >= 3:
                victim = message.split(" ", 2)[2]
                if victim not in self.config.get("inedible_victims"):
                    bot.send_action(self.messages.get("eat", "gulps down {victim}!").format(victim=victim))
                    bot.stomach.add(victim)
                else:
                    bot.send_action(
                        self.messages.get("eat_inedible", "doesn't feel like eating {victim}!").format(victim=victim))

        @self.advanced_command(False)
        def spit(bot: Toothless, message: str, sender: str):
            bot.stomach = list(bot.stomach)
            command = " ".join(message.split(" ")[:2]).lower()
            respond_to = (bot.nick.lower() + "! spit").lower()
            if command == respond_to and len(message.split(" ")) >= 3:
                victim = message.split(" ", 2)[2]
                if victim in bot.stomach:
                    # noinspection PyUnresolvedReferences
                    del bot.stomach[bot.stomach.index(victim)]
                    bot.send_action("spits out {}!".format(victim))
                else:
                    bot.send_action("hasn't eaten {} yet!".format(victim))
            bot.stomach = set(bot.stomach)

        @self.advanced_command(False)
        def show_stomach(bot: Toothless, message: str, sender: str):
            command = " ".join(message.split(" ")[:2]).lower()
            respond_to = (bot.nick.lower() + "! stomach").lower()
            if command == respond_to:
                stomachs = ", ".join(bot.stomach)
                if stomachs:
                    bot.send_action(bot.messages.get("stomach", "is digesting {victims}...").format(victims=stomachs))
                else:
                    bot.send_action(bot.messages.get("stomach_empty", "isn't digesting anyone..."))

        @self.advanced_command(False)
        def vomit(bot: Toothless, message: str, sender: str):
            command = " ".join(message.split(" ")[:2]).lower()
            respond_to = (bot.nick.lower() + "! vomit").lower()
            if command == respond_to:
                if bot.stomach:
                    bot.send_action(self.messages.get("vomit", "empties his stomach!"))
                    bot.stomach = set()
                else:
                    bot.send_action(self.messages.get("vomit_superfluous", "hasn't eaten anything yet!"))

        @self.advanced_command(True)
        def clear_commands(bot: Toothless, message: str, sender: str):
            if bot.has_flag("admin", sender) and message.lower().strip() == "purge_commands":
                bot.irc_cursor.execute("SELECT * FROM Commands")
                if not bot.irc_cursor.fetchall():
                    bot.send_action(self.messages.get("purge_commands_superfluous",
                                                      "hasn't learned any tricks to forget!"), sender)
                else:
                    bot.irc_cursor.execute("DELETE FROM Commands")
                    bot.send_action(self.messages.get("purge_commands", "forgot all of his tricks!"), sender)

        @self.advanced_command(True)
        def whitelist(bot: Toothless, message: str, sender: str):
            nicknames = message.lower().strip().split(" ")
            if bot.has_flag("admin", sender) and nicknames[0] == "append_whitelist":
                for i in nicknames[1:]:
                    bot.add_flag(i, "whitelist")

        @self.advanced_command(True)
        def terminate(bot: Toothless, message: str, sender: str):
            if bot.has_flag("admin", sender) and message == "terminate":
                raise KeyboardInterrupt

        @self.advanced_command(True)
        def list_commands(bot: Toothless, message: str, sender: str):
            if message == "list_commands":
                bot.irc_cursor.execute("SELECT trigger,response FROM Commands")
                for trigger, response in bot.irc_cursor.fetchall():
                    bot.send_message(
                        self.messages.get("print_command", "{trigger} -> {response}").format(trigger=trigger,
                                                                                             response=response),
                        sender)

        @self.advanced_command(True)
        def copy_original(bot: Toothless, message: str, sender: str):
            if bot.has_flag("admin", sender) and message == "copy_original":
                bot.copying = True
                bot.send_action(self.messages.get("copy_original", "will start copying the original."), sender)
                bot.send_message("list_commands", "Toothless")
                bot.irc_cursor.execute("SELECT * FROM Commands")

        @self.advanced_command(True)
        def add_flag_pm(bot: Toothless, message: str, sender: str):
            if bot.has_flag("admin", sender) and message.split(" ")[0] == "add_flag":
                user, flag = map(lambda x: x.lower(), message.split(" ")[1:3])
                try:
                    bot.add_flag(user, flag)
                except ToothlessError:
                    bot.send_action("doesn't know that flag!")
                else:
                    flags = "".join(bot.get_flags(user))
                    bot.send_action(self.messages.get("flag_added",
                                                      "successfully added {flag} to {user}, new flags: {flags}").format(
                        user=user, flag=flag, flags=flags), sender)

        @self.advanced_command(True)
        def rm_flag_pm(bot: Toothless, message: str, sender: str):
            if bot.has_flag("admin", sender) and message.split(" ")[0] == "remove_flag":
                user, flag = map(lambda x: x.lower(), message.split(" ")[1:3])
                try:
                    bot.remove_flag(user, flag)
                except ToothlessError:
                    bot.send_action("doesn't know that flag!")
                else:
                    flags = "".join(bot.get_flags(user))
                    bot.send_action(
                        self.messages.get("flag_remove",
                                          "successfully remove {flag} from {user}, new flags: {flags}").format
                        (user=user, flag=flag, flags=flags),
                        sender
                    )

        @self.advanced_command(True)
        def reload_config(bot: Toothless, message: str, sender: str):
            if bot.has_flag("admin", sender) and message.split(" ")[0].lower() == "reload_config":
                if not bot.config_file.closed:
                    bot.config_file.close()
                bot.config_file = open(bot.config_file.name, bot.config_file.mode)
                bot.config = json.loads(bot.config_file.read())
                bot.messages = bot.config.get("messages", {})
                bot.send_action(bot.messages.get("config_reloaded", "successfully reloaded his config!"), sender)
            elif not bot.has_flag("admin", sender):
                bot.send_action(bot.messages.get("deny_command", "won't listen to you!"), message)


        @self.advanced_command(True)
        def move_channel(bot: Toothless, message:str, sender:str):
            if bot.has_flag("admin", sender) and message.split(" ")[0].lower() == "move_channel":
                channel = message.split(" ")[1].lower()
                bot.leave_channel(bot.messages.get("switch_channel", "Gotta go to fly with Hiccup..."))
                bot.join_channel(channel)
