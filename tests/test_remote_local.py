"""Test the local file remote class"""
import os
import pytest

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
expected_photos = sorted([{"name": x} for x in files if ".jpeg" in x], key=lambda x: x["name"])
links = {
    "albums/Spring/49935.jpeg": "2020/01/49935.jpeg",
    "albums/Spring/49936.jpeg": "2020/01/49936.jpeg",
    "albums/Autumn/49935.jpeg": "2020/02/49935.jpeg",
}
expected_albums = [
    {"name": "Autumn", "photos": ["2020/02/49935.jpeg"]},
    {"name": "Spring", "photos": ["2020/01/49935.jpeg", "2020/01/49936.jpeg"]},
]


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
    assert obj.get_photos() == expected_photos


def test_get_albums(tmpdir):
    _setup_tmpdir(tmpdir)
    obj = LocalRemote()
    obj.folder = tmpdir
    assert obj.get_albums() == expected_albums


def test_get_fixes(tmpdir):
    _setup_tmpdir(tmpdir)
    with open(os.path.join(tmpdir, "albums/Autumn/50000.jpeg"), "w"):
        pass
    obj = LocalRemote()
    obj.folder = tmpdir
    assert obj.get_fixes() == [{"action": "symlink", "name": "albums/Autumn/50000.jpeg", "to": "50000.jpeg"}]


def test_do_fixes(tmpdir):
    _setup_tmpdir(tmpdir)
    with open(os.path.join(tmpdir, "albums/Autumn/50000.jpeg"), "w"):
        pass
    obj = LocalRemote()
    obj.folder = tmpdir
    obj.do_fixes([{"action": "symlink", "name": "albums/Autumn/50000.jpeg", "to": "2020/03/50000.jpeg"}])
    assert os.path.realpath(os.path.join(tmpdir, "albums/Autumn/50000.jpeg")) == os.path.join(
        tmpdir, "2020/03/50000.jpeg"
    )


@pytest.mark.parametrize(
    "updates,state_photos,state_albums",
    [
        (
            [{"action": "new", "name": "2021/01/rfse.jpeg", "data": lambda: b"Image"}],
            sorted(expected_photos + [{"name": "2021/01/rfse.jpeg"}], key=lambda x: x["name"]),
            expected_albums,
        ),
        (
            [{"action": "del", "name": "2020/01/49935.jpeg"}],
            [x for x in expected_photos if x["name"] != "2020/01/49935.jpeg"],
            expected_albums,
        ),
        (
            [{"action": "mv", "name": "2020/01/49935.jpeg", "new_name": "2020/02/66930.jpeg"}],
            sorted(
                [
                    x
                    if x["name"] != "2020/01/49935.jpeg"
                    else dict(list(x.items()) + [("name", "2020/02/66930.jpeg")])
                    for x in expected_photos
                ],
                key=lambda x: x["name"],
            ),
            expected_albums,
        ),
        (
            [
                {"action": "new_album", "name": "Fall", "photos": ["2020/01/49934.jpeg"]},
            ],
            expected_photos,
            sorted(expected_albums + [{"name": "Fall", "photos": ["2020/01/49934.jpeg"]}], key=lambda x: x["name"]),
        ),
        (
            [{"action": "del_album", "name": "Spring"}],
            expected_photos,
            [x for x in expected_albums if x["name"] != "Spring"],
        ),
        (
            [{"action": "del_album_photo", "album_name": "Spring", "name": "2020/01/49935.jpeg"}],
            expected_photos,
            [
                x if x["name"] != "Spring" else dict(list(x.items()) + [("photos", ["2020/01/49936.jpeg"])])
                for x in expected_albums
            ],
        ),
        (
            [{"action": "new_album_photo", "album_name": "Spring", "name": "2020/01/49934.jpeg"}],
            expected_photos,
            [
                x
                if x["name"] != "Spring"
                else dict(list(x.items()) + [("photos", sorted(x["photos"] + ["2020/01/49934.jpeg"]))])
                for x in expected_albums
            ],
        ),
    ],
)
def test_do_updates(tmpdir, updates, state_photos, state_albums):
    _setup_tmpdir(tmpdir)
    obj = LocalRemote()
    obj.folder = tmpdir
    obj.do_updates(updates)
    assert obj.get_photos() == state_photos
    assert obj.get_albums() == state_albums


# test_load_config
