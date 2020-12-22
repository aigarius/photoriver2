"""Test the remote base class"""
import tempfile

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
