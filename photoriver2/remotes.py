"""Remotes implementation - state of an instance of a photo collection"""
import json
import os


class BaseRemote:
    """Common functionality between local folder remotes and online remotes"""

    new_state = None

    def __init__(self, name="local"):
        self.name = name
        self.config_file = os.path.join("/river/config", name + ".json")
        self.old_state = self.load_old_state(self.config_file)

    @staticmethod
    def load_old_state(config_file):
        if os.path.exists(config_file):
            with open(config_file, "r") as infile:
                return json.load(infile)
        else:
            return {}

    def get_new_state(self):
        return {"photos": self.get_photos(), "albums": self.get_albums()}

    def get_photos(self):
        raise NotImplementedError

    def get_albums(self):
        raise NotImplementedError


class LocalRemote(BaseRemote):
    """Remote representing a local folder with photos"""

    folder = None

    def get_photos(self):
        photos = []
        for root, _, files in os.walk(self.folder):
            for afile in files:
                name = os.path.relpath(os.path.join(root, afile), self.folder)
                photos.append({"name": name})
        return sorted(photos, key=lambda x: x["name"])

    def get_albums(self):
        albums = []
        if os.path.exists(os.path.join(self.folder, "albums")):
            dirs = os.scandir(os.path.join(self.folder, "albums"))
            for adir in dirs:
                if not adir.is_dir():
                    continue
                albums.append(
                    {
                        "name": adir.name,
                        "photos": os.listdir(adir.path),
                    }
                )
        return albums


class GoogleRemote(BaseRemote):
    """Connection to Google Photos service via a remote"""


class FlickrRemote(BaseRemote):
    """Connection to Flickr service via a remote"""
