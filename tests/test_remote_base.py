"""Test the remote base class"""
import os
import tempfile

import pytest

from photoriver2.remotes import BaseRemote


def test_init():
    assert BaseRemote() is not None


def test_state_load():
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


def test_state_save(tmpdir):
    obj = BaseRemote()
    obj.state_file = os.path.join(tmpdir, "base.json")
    obj.new_state = {"a": 1, "b": 2}
    obj.save_new_state()
    with open(os.path.join(tmpdir, "base.json"), "rb") as infile:
        assert infile.read() == b'{"a": 1, "b": 2}'


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
        (
            {"photos": [{"name": "IMG001"}], "albums": []},
            {"photos": [{"name": "IMG001"}], "albums": [{"name": "Spring", "photos": ["IMG001"]}]},
            [
                {"action": "new_album", "name": "Spring", "photos": ["IMG001"]},
            ],
        ),
        (
            {"photos": [{"name": "IMG001"}], "albums": [{"name": "Spring", "photos": ["IMG001"]}]},
            {"photos": [{"name": "IMG001"}], "albums": []},
            [{"action": "del_album", "name": "Spring"}],
        ),
        (
            {"photos": [{"name": "IMG001"}], "albums": [{"name": "Spring", "photos": ["IMG001"]}]},
            {"photos": [{"name": "IMG001"}], "albums": [{"name": "Spring", "photos": []}]},
            [{"action": "del_album_photo", "album_name": "Spring", "name": "IMG001"}],
        ),
        (
            {"photos": [{"name": "IMG001"}], "albums": [{"name": "Spring", "photos": []}]},
            {"photos": [{"name": "IMG001"}], "albums": [{"name": "Spring", "photos": ["IMG001"]}]},
            [{"action": "new_album_photo", "album_name": "Spring", "name": "IMG001"}],
        ),
    ],
)
def test_get_updates(state_old, state_new, expected):
    obj = BaseRemote()
    obj.old_state = state_old
    obj.new_state = state_new
    assert obj.get_updates() == expected


@pytest.mark.parametrize(
    "state_our,state_their,expected",
    [
        ({"photos": [], "albums": []}, {"photos": [], "albums": []}, []),
        (
            {"photos": [{"name": "IMG001"}], "albums": []},
            {"photos": [], "albums": []},
            [],
        ),
        (
            {"photos": [], "albums": []},
            {"photos": [{"name": "IMG001"}], "albums": []},
            [{"action": "new", "name": "IMG001"}],
        ),
        (
            {"photos": [{"name": "2020/01/IMG001"}, {"name": "2020/01/IMG002"}], "albums": []},
            {"photos": [{"name": "2020/02/IMG001"}, {"name": "2020/01/IMG002"}], "albums": []},
            [{"action": "new", "name": "2020/02/IMG001"}],
        ),
        (
            {"photos": [{"name": "IMG001"}], "albums": []},
            {"photos": [{"name": "IMG001"}], "albums": [{"name": "Spring", "photos": ["IMG001"]}]},
            [
                {"action": "new_album", "name": "Spring", "photos": ["IMG001"]},
            ],
        ),
        (
            {"photos": [{"name": "IMG001"}], "albums": [{"name": "Spring", "photos": ["IMG001"]}]},
            {"photos": [{"name": "IMG001"}], "albums": []},
            [],
        ),
        (
            {"photos": [{"name": "IMG001"}], "albums": [{"name": "Spring", "photos": ["IMG001"]}]},
            {"photos": [{"name": "IMG001"}], "albums": [{"name": "Spring", "photos": []}]},
            [],
        ),
        (
            {"photos": [{"name": "IMG001"}], "albums": [{"name": "Spring", "photos": []}]},
            {"photos": [{"name": "IMG001"}], "albums": [{"name": "Spring", "photos": ["IMG001"]}]},
            [{"action": "new_album_photo", "album_name": "Spring", "name": "IMG001"}],
        ),
    ],
)
def test_get_merge_updates(state_our, state_their, expected):
    obj1 = BaseRemote()
    obj1.new_state = state_their

    obj2 = BaseRemote()
    obj2.new_state = state_our

    assert obj2.get_merge_updates(obj1) == expected
