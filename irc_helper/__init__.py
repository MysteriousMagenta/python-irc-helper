#!/usr/bin/env python3
from irc_helper.irc_protocol import *
from irc_helper.main_bot import *

import re as _re
import requests as _requests
from bs4 import _soup


# From Django
url_validator = _re.compile(
    r"^(?:(?:http|ftp)s?://)"  # http:// or https://
    r"((?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|"  # domain...
    r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})"  # ...or ip
    r"(?::\d+)?"  # optional port
    r"(?:/?|[/?]\S+)$", re.IGNORECASE)

# Use this function to apply all the commands
def apply_commands(bot):
    """
    A base set of commands.
    Arguments:
        bot: A IRCHelper instance.
    Effect:
        Adds a bunch of sample commands to bot.
    """
    @bot.advanced_command()
    def url_title(bot_, message, sender):
        url_match = url_validator.search(message.strip())
        if not url_match:
            return
        domain = url_match.group(1)
        if len(domain.split(".")) > 1:
            domain = domain.split(".")[1]
        req = _requests.get(message.strip(), headers={"User-Agent": "Py3 TitleFinder"})
        if req.ok:
            if domain != "youtube":
                soup = _soup(req.text)
                bot_.send_message("{}: The URL title is \"{}\"".format(sender, soup.title.text))
            else:
                # To Implement.
                pass
        else:
            bot_.send_message("{}: Wasn't able to get URL info! [{}]".format(sender, req.status_code))

    @bot.advanced_command()
    def learn_trigger(bot_, message, sender):
        command = " ".join(message.split(" ")[:2]).lower()
        respond_to = (bot_.nick.lower() + "! learn").lower()
        if command == respond_to and len(message.split("->", 1)) >= 2:
            bot_.message("Has learned {}!".format(message.lstrip("learn ")))
            @bot.basic_command()
            def learn_comm():
                return message.lstrip("learn ").split(" -> ", 1)
            return True

    @bot.advanced_command()
    def forget_trigger(bot_, message, sender):
        command = " ".join(message.split(" ")[:2]).lower()
        respond_to = (bot_.nick.lower() + "! forget").lower()
        if command == respond_to:
            bot_.forget_basic_command(message.split(" ", 1)[1])
            return True

    @bot.advanced_command()
    def attack(bot_, message, sender):
        command = " ".join(message.split(" ")[:2]).lower()
        respond_to = (bot_.nick.lower() + "! attack").lower()
        if command == respond_to:
            bot_.send_action("pounces on {}!".format(message.split(" ")[1]))
            return True

    @bot.advanced_command()
    def eat(bot_, message, sender):
        command = " ".join(message.split(" ")[:2]).lower()
        respond_to = (bot_.nick.lower() + "! eat").lower()
        if command == respond_to:
            victim = message.split(" ", 2)[2]
            bot_.send_action("eats {}!".format(victim))
            if "stomach" not in bot_.__dict__:
                bot_.stomach = []
            bot_.stomach.append(victim)

    @bot.advanced_command()
    def spit(bot_, message, sender):
        command = " ".join(message.split(" ")[:2]).lower()
        respond_to = (bot_.nick.lower() + "! spit").lower()
        if command == respond_to:
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

    @bot.advanced_command()
    def show_stomach(bot_, message, sender):
        command = " ".join(message.split(" ")[:2]).lower()
        respond_to = (bot_.nick.lower() + "! stomach").lower()
        if "stomach" not in bot_.__dict__:
            bot_.stomach = []
        if command == respond_to:
            stomachs = ", ".join(bot_.stomach)
            if stomachs:
                bot_.send_action("has eaten {}".format(stomachs))

    @bot.advanced_command()
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