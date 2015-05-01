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
ATTACKS = [
    "shoots a plasma bolt at {target}!",
    "hurls a pebble at {target}!",
    "tackles {target}!",
    "tail-whips {target}!",
    "charges {target}!",
    "unsheathes his teeth and bites {target}!"
]

GREETS = [
    "welcomingly nuzzles and licks {nick}",
    "welcomingly nuzzles {nick}",
    "welcomingly licks {nick}",
    "welcomingly tail-slaps {nick}",
    "playfully nuzzles and licks {nick}",
    "playfully nuzzles {nick}",
    "playfully licks {nick}",
    "playfully tail-slaps {nick}",
    "tosses a pebble at {nick}",
    "joyfully waggles his tail at {nick}'s arrival",
    "cheerfully waggles his tail at {nick}'s arrival",
    "playfully waggles his tail at {nick}'s arrival",
    "welcomes {nick} with a cheerful warble"
]


# noinspection PyUnusedLocal
class Toothless(irc_helper.IRCHelper):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.stomach = set()
        self.apply_commands()


    def handle_block(self, block):
        block_data = super().handle_block(block)
        if block_data.get("command", "").upper() == "JOIN":
            if FLAGS["ignore"] not in self.get_flags(block_data.get("sender", "")):
                greeting = random.choice(GREETS)
                if "{nick}" in greeting:
                    greeting = greeting.format(nick=block_data.get("sender"))
                else:
                    greeting += block_data.get("sender", "")
                self.send_action(greeting)

    def join_channel(self, channel):
        super().join_channel(channel)
        self.send_action("enters the arena!")

    def add_flag(self, username, flag):
        if flag in FLAGS:
            flag = FLAGS.get(flag)
        elif flag not in FLAGS.values():
            raise irc_helper.IRCError("Unknown flag! Valid flags are {}".format(", ".join(FLAGS.values())))
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
                bot.send_action("thinks the URL title is \"{}\"".format(sender, soup.title.text))
                # TODO Implement proper Youtube API
            else:
                bot.send_action("wasn't able to get URL info! [{}]".format(sender, req.status_code))
            return True

        @self.advanced_command(False)
        def learn_trigger(bot, message, sender):
            command = " ".join(message.split(" ")[:2]).lower()
            respond_to = (bot.nick.lower() + "! learn").lower()
            if command == respond_to and len(message.split("->", 1)) >= 2 and FLAGS["whitelist"] in bot.get_flags(
                    sender):
                bot.irc_cursor.execute("SELECT * FROM Commands WHERE trigger=? AND response=?",
                                       message.split(" ", 2)[2].split(" -> ", 1))
                if bot.irc_cursor.fetchone() is None:
                    bot.send_action("has been trained by {}!".format(sender))

                    @self.basic_command()
                    def learn_comm():
                        return message.split(" ", 2)[2].split(" -> ", 1)
                else:
                    bot.send_action("already knows that!")
            elif FLAGS["whitelist"] not in bot.get_flags(sender):
                bot.send_action("doesn't want to be trained by {}!".format(sender))
            return command == respond_to or None

        @self.advanced_command(False)
        def forget_trigger(bot, message, sender):
            command = " ".join(message.split(" ")[:2]).lower()
            respond_to = (bot.nick.lower() + "! forget").lower()
            if command == respond_to and len(message.split(" ")) >= 3:
                trigger = message.split(" ", 2)[2]
                bot.irc_cursor.execute("SELECT response FROM Commands WHERE trigger=?", (trigger,))
                response = (bot.irc_cursor.fetchone() or [None])[0]
                print(trigger, response)
                if response is not None:
                    bot.send_action("forgot {} -> {}".format(trigger, response))
                    bot.forget_basic_command(trigger)
                else:
                    bot.send_action("doesn't know that!")
            return command == respond_to or None

        @self.advanced_command(False)
        def attack(bot, message, sender):
            command = " ".join(message.split(" ")[:2]).lower()
            respond_to = (bot.nick.lower() + "! attack").lower()
            if command == respond_to and len(message.split(" ")) >= 3:
                attack = random.choice(ATTACKS)
                victim = message.split(" ")[1]
                if "{target}" in attack:
                    attack = attack.format(target=victim)
                else:
                    attack += victim
                bot.send_action(attack)
            return command == respond_to or None

        @self.advanced_command(False)
        def eat(bot, message, sender):
            command = " ".join(message.split(" ")[:2]).lower()
            respond_to = (bot.nick.lower() + "! eat").lower()
            if command == respond_to and len(message.split(" ")) >= 3:
                victim = message.split(" ", 2)[2]
                bot.send_action("eats {}!".format(victim))
                bot.stomach.add(victim)
            return command == respond_to or None

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
            return command == respond_to or None

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
            return command == respond_to or None

        @self.advanced_command(False)
        def vomit(bot, message, sender):
            command = " ".join(message.split(" ")[:2]).lower()
            respond_to = (bot.nick.lower() + "! vomit").lower()
            if command == respond_to:
                if bot.stomach:
                    bot.send_action("empties his stomach!")
                    bot.stomach = set()
                else:
                    bot.send_action("hasn't eaten anything yet!")
            return command == respond_to or None

        @self.advanced_command(True)
        def clear_commands(bot, message, sender):
            if message.lower().strip() == "purge_commands" and FLAGS["admin"] in bot.get_flags(sender):
                bot.cursor.execute("DELETE FROM Commands")

        @self.advanced_command(True)
        def whitelist(bot, message, sender):
            nicknames = message.lower().strip().split(" ")
            if nicknames[0] == "append_whitelist":
                for i in nicknames[1:]:
                    bot.add_flag(i, FLAGS["whitelist"])

        @self.advanced_command(True)
        def terminate(bot, message, sender):
            if message == "terminate" and FLAGS["admin"] in bot.get_flags(sender):
                bot.quit()

        @self.advanced_command(True)
        def list_commands(bot, message, sender):
            if message == "list_commands":
                bot.irc_cursor.execute("SELECT trigger,response FROM Commands")
                for trigger, response in bot.irc_cursor.fetchall():
                    bot.send_message("{} -> {}".format(trigger, response), sender)
                    time.sleep(.01)