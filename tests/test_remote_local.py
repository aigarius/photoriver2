"""Test the local file remote class"""
import os

from photoriver2.remotes import LocalRemote


def test_init():
    assert LocalRemote() is not None


files = [
    "Archived/2019/01/49934.jpeg",
    "2020/01/49934.jpeg",
    "2020/01/49935.jpeg",
    "2020/01/49936.jpeg",
    "2020/02/49935.jpeg",
    "albums/tags",
]
links = {
    "albums/Spring/49935.jpeg": "2020/01/49935.jpeg",
    "albums/Spring/49936.jpeg": "2020/01/49936.jpeg",
    "albums/Autumn/49935.jpeg": "2020/02/49935.jpeg",
}


def _setup_tmpdir(tmpdir):
    for afile in files:
        full_path = os.path.join(tmpdir, afile)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        with open(full_path, "w"):
            pass
    for alink, dest in links.items():
        alink = os.path.join(tmpdir, alink)
        os.makedirs(os.path.dirname(alink), exist_ok=True)
        dest = os.path.relpath(os.path.join(tmpdir, dest), os.path.dirname(alink))
        os.symlink(dest, alink)


def test_get_photos(tmpdir):
    _setup_tmpdir(tmpdir)
    obj = LocalRemote()
    obj.folder = tmpdir
    assert obj.get_photos() == sorted([{"name": x} for x in files if ".jpeg" in x], key=lambda x: x["name"])


def test_get_albums(tmpdir):
    _setup_tmpdir(tmpdir)
    obj = LocalRemote()
    obj.folder = tmpdir
    assert obj.get_albums() == [
        {"name": "Autumn", "photos": ["2020/02/49935.jpeg"]},
        {"name": "Spring", "photos": ["2020/01/49935.jpeg", "2020/01/49936.jpeg"]},
    ]


def test_get_fixes(tmpdir):
    _setup_tmpdir(tmpdir)
    with open(os.path.join(tmpdir, "albums/Autumn/50000.jpeg"), "w"):
        pass
    obj = LocalRemote()
    obj.folder = tmpdir
    assert obj.get_fixes() == [{"action": "symlink", "name": "albums/Autumn/50000.jpeg", "to": "50000.jpeg"}]


# test_do_fixes

# test_do_updates

# test_load_config
