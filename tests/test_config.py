"""Test config parsing and remote init"""

from photoriver2.config import parse_config, init_remotes


EXAMPLE_CONFIG = """
[main]
dry_run=true

[remote1]
type=local
folder=/tmp/1

[remote2]
type=local
folder=/tmp/2
"""

EXPECTED_CONFIG = {
    "options": {
        "dry_run": True,
    },
    "remotes": {
        "remote1": {
            "type": "local",
            "folder": "/tmp/1",
        },
        "remote2": {
            "type": "local",
            "folder": "/tmp/2",
        },
    },
}


def test_parse_config():
    assert parse_config(EXAMPLE_CONFIG) == EXPECTED_CONFIG


def test_init_remotes():
    remotes = init_remotes(EXPECTED_CONFIG)
    assert "remote1" in remotes
    assert "remote2" in remotes
    assert remotes["remote1"].name == "remote1"
    assert remotes["remote2"].name == "remote2"
    assert remotes["remote1"].folder == "/tmp/1"
    assert remotes["remote2"].folder == "/tmp/2"
