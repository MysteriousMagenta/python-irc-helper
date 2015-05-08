#!/usr/bin/env python3
import os.path
from setuptools import setup, find_packages

if os.path.exists("requirements.txt"):
    with open("requirements.txt") as req_file:
        reqs = [i for i in req_file if i]
else:
    reqs = []

packs = find_packages()
if not packs:
    raise Exception("Couldn't find any packages!")


setup(
    name="irc_helper",
    version=1.0,
    description="A module that helps with IRC, namely IRC Bots.",
    author="SquishyStrawberry",
    install_requires=reqs,
    packages=packs
)
