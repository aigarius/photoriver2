"""Test the remote base class"""
import tempfile

import pytest

from photoriver2.remotes import BaseRemote


def test_init():
    assert BaseRemote() is not None


def test_config_load():
    with tempfile.NamedTemporaryFile() as tmp:
        tmp.write(b'{"a":1,"b":2}')
        tmp.flush()
        assert BaseRemote.load_old_state(tmp.name) == {"a": 1, "b": 2}


def test_get_new_state():
    obj = BaseRemote()
    obj.get_photos = lambda: [{"name": "Photo1"}]
    obj.get_albums = lambda: [{"name": "Album1", "photos": ["Photo1"]}]
    assert obj.get_new_state() == {
        "photos": [{"name": "Photo1"}],
        "albums": [{"name": "Album1", "photos": ["Photo1"]}],
    }


@pytest.mark.parametrize(
    "state_old,state_new,expected",
    [
        ({"photos": [], "albums": []}, {"photos": [], "albums": []}, []),
        (
            {"photos": [{"name": "IMG001"}], "albums": []},
            {"photos": [], "albums": []},
            [{"action": "del", "name": "IMG001"}],
        ),
        (
            {"photos": [], "albums": []},
            {"photos": [{"name": "IMG001"}], "albums": []},
            [{"action": "new", "name": "IMG001"}],
        ),
        (
            {"photos": [{"name": "2020/01/IMG001"}, {"name": "2020/01/IMG002"}], "albums": []},
            {"photos": [{"name": "2020/02/IMG001"}, {"name": "2020/01/IMG002"}], "albums": []},
            [{"action": "mv", "name": "2020/01/IMG001", "new_name": "2020/02/IMG001"}],
        ),
    ],
)
def test_get_updates(state_old, state_new, expected):
    obj = BaseRemote()
    obj.old_state = state_old
    obj.new_state = state_new
    assert obj.get_updates() == expected
