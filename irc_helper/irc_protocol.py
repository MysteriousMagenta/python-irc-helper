#!/usr/bin/env python3
"""
Small file that handles IRC Handling.
Currently doesn't comply with RFC section 2.3.1, but it'll get there.
I just have to find out the freaking format :/
"""
import socket


class IRCError(Exception):
    pass


class IRCBot(object):
    def __init__(self, user, nick, channel, host, port=6667):
        self.connection_data = (host, port)
        self.user = user
        self.nick = nick
        self.base_channel = channel
        self.channel = None
        self.started = False
        # Will implement actual logging later.
        self.log = print
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.connect(self.connection_data)
        self.start_up()

    def start_up(self):
        while True:
            block = self.get_block()
            if self.handle_ping(block):
                continue
            elif "found your hostname" in block.lower():
                self.socket.send("USER {0} 0 * :{0}\r\n".format(self.user).encode())
                self.socket.send("NICK {}\r\n".format(self.nick).encode())
            elif "end of /motd" in block.lower():
                self.started = True
                return

    def join_channel(self, channel):
        self.channel = channel
        self.socket.send("JOIN {}\r\n".format(channel).encode())

    def get_block(self):
        return self.socket.recv(4096).decode()

    def send_message(self, message, send_to=None):
        if send_to is None:
            if self.channel is None:
                raise IRCError("Tried calling send_message without being in a channel and with no recipient!")
            send_to = self.channel
        self.socket.send("PRIVMSG {} :{}\r\n".format(send_to, message).encode())

    def handle_block(self, block):
        message_parts = block.split(" ", 1)
        sender = message_parts[0][1:].split("!", 1)[0]
        command = message_parts[1].strip()
        if self.handle_ping(block) or sender in (self.nick, self.user) or sender == self.connection_data[0]:
            return
        command, recipient, message = command.split(" ", 2)
        message = message[1:]
        # Are there any other commands I need to handle?
        if command.upper() == "PRIVMSG":
            self.log("[{} to {}] {}".format(sender, recipient, message))
        else:
            self.log("Unknown Command '{}'".format(command))


    def handle_ping(self, message):
        is_ping = message.upper().startswith("PING")
        if is_ping:
            self.log("[+] Received Ping!")
            data = "".join(message.split(" ", 1)[1:])[1:]
            self.socket.send("PONG :{}\r\n".format(data).encode())
        return is_ping


    def run(self):
        while True:
            if self.started and self.channel is None:
                self.join_channel(self.base_channel)
            msg = self.get_block()
            for line in msg.splitlines():
                self.handle_block(line)
