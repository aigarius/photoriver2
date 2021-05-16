"""Parses config file and initializes all configured remotes"""

import configparser

from photoriver2.remote_local import LocalRemote
from photoriver2.remote_google import GoogleRemote


def parse_config(config_text=None):
    if not config_text:
        with open("/river/config/photoriver2.ini", "rt") as infile:
            config_text = infile.read()
    config = configparser.ConfigParser()
    config.read_string(config_text)

    config_data = {"options": {}, "remotes": {}}
    config_data["options"]["dry_run"] = config.getboolean("main", "dry_run", fallback=False)
    for section in config.sections():
        if section == "main":
            continue
        config_data["remotes"][section] = dict(config.items(section=section))
    return config_data


def init_remotes(config_data):
    remotes = {}
    for name in config_data["remotes"]:
        if config_data["remotes"][name]["type"] == "local":
            remotes[name] = LocalRemote(name=name, folder=config_data["remotes"][name]["folder"])
        if config_data["remotes"][name]["type"] == "google":
            remotes[name] = GoogleRemote(name=name, token_cache=config_data["remotes"][name]["token_cache"])
    return remotes
