#!/usr/bin/env python3
import time
from irc_helper.irc_protocol import IRCBot, IRCError
from irc_helper.main_bot import IRCHelper, FLAGS

import re as _re
import requests as _requests
from bs4 import BeautifulSoup as _BeautifulSoup


# From Django
url_validator = _re.compile(
    r"^(?:(?:http|ftp)s?://)"  # http:// or https://
    r"((?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|"  # domain...
    r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})"  # ...or ip
    r"(?::\d+)?"  # optional port
    r"(?:/?|[/?]\S+)$", _re.IGNORECASE)

# Use this function to apply all the commands
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
        domain = url_match.group(1)
        if len(domain.split(".")) > 1:
            domain = domain.split(".")[1]
        req = _requests.get(message.strip(), headers={"User-Agent": "Py3 TitleFinder"})
        if req.ok:
            soup = _BeautifulSoup(req.text)
            bot_.send_message("{}: The URL title is \"{}\"".format(sender, soup.title.text))
            # TODO Implement proper Youtube API
        else:
            bot_.send_message("{}: Wasn't able to get URL info! [{}]".format(sender, req.status_code))
        return True

    @bot.advanced_command(False)
    def learn_trigger(bot_, message, sender):
        command = " ".join(message.split(" ")[:2]).lower()
        respond_to = (bot_.nick.lower() + "! learn").lower()
        if command == respond_to and len(message.split("->", 1)) >= 2:
            bot_.send_message("Has learned {}!".format(message.lstrip(command)))
            @bot.basic_command()
            def learn_comm():
                return message.lstrip(command).split(" -> ", 1)
        return command == respond_to or None

    @bot.advanced_command(False)
    def forget_trigger(bot_, message, sender):
        command = " ".join(message.split(" ")[:2]).lower()
        respond_to = (bot_.nick.lower() + "! forget").lower()
        if command == respond_to and len(message.split(" ")) >= 3:
            bot_.forget_basic_command(message.split(" ", 1)[1])
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