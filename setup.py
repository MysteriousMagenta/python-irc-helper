#!/usr/bin/env python3
import setuptools


scripts = [
    "irc_helper/irc_helper.py",
    "irc_helper/irc_protocol.py"
]

setuptools.setup(
    name="irc_helper",
    version="1.0",
    packages=packs,
    scripts=scripts,
    install_requires=reqs,
    description="Small Lib that helps with IRC, namely IRC Bots.",
)
