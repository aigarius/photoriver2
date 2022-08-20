"""Parses config file and initializes all configured remotes"""

import configparser
import os

from photoriver2.remote_local import LocalRemote
from photoriver2.remote_google import GoogleRemote


def parse_config(config_path="/river/config", config_text=None):
    if not config_text:
        with open(os.path.join(config_path, "photoriver2.ini"), "rt") as infile:
            config_text = infile.read()
    config = configparser.ConfigParser()
    config.read_string(config_text)

    config_data = {"remotes": {}, "config_path": config_path}
    for section in config.sections():
        config_data["remotes"][section] = dict(config.items(section=section))
    if not "base" in config_data["remotes"]:
        raise RuntimeError("Configuration must contain a local remote called 'base'")
    return config_data


def init_remotes(config_data):
    remotes = {}
    for name in config_data["remotes"]:
        if config_data["remotes"][name]["type"] == "local":
            remotes[name] = LocalRemote(
                name=name,
                folder=config_data["remotes"][name]["folder"],
                blacklist=config_data["remotes"][name]["folder"],
            )
        if config_data["remotes"][name]["type"] == "google":
            remotes[name] = GoogleRemote(
                name=name,
                token_cache=os.path.join(config_data["config_path"], config_data["remotes"][name]["token_cache"]),
                blacklist=config_data["remotes"][name]["folder"],
            )
    return remotes
