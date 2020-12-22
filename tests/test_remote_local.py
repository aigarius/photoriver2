"""Test the local file remote class"""
import os

from photoriver2.remotes import LocalRemote


def test_init():
    assert LocalRemote() is not None


def test_get_photos(tmpdir):
    files = [
        "Archived/2019/01/49934.jpeg",
        "2020/01/49934.jpeg",
        "2020/01/49935.jpeg",
        "2020/01/49936.jpeg",
        "2020/02/49935.jpeg",
        "albums/Spring/49935.jpeg",
        "albums/Spring/49936.jpeg",
    ]
    for afile in files:
        full_path = os.path.join(tmpdir, afile)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        with open(full_path, "w"):
            pass
    obj = LocalRemote()
    obj.folder = tmpdir
    assert obj.get_photos() == sorted([{"name": x} for x in files], key=lambda x: x["name"])


def test_get_albums(tmpdir):
    files = [
        "Archived/2019/01/49934.jpeg",
        "2020/01/49934.jpeg",
        "2020/01/49935.jpeg",
        "2020/01/49936.jpeg",
        "2020/02/49935.jpeg",
        "albums/Spring/49935.jpeg",
        "albums/tags",
        "albums/Spring/49936.jpeg",
    ]
    for afile in files:
        full_path = os.path.join(tmpdir, afile)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        with open(full_path, "w"):
            pass
    obj = LocalRemote()
    obj.folder = tmpdir
    assert obj.get_albums() == [{"name": "Spring", "photos": ["49935.jpeg", "49936.jpeg"]}]
