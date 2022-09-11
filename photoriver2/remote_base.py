"""Remotes implementation - state of an instance of a photo collection"""
import json
import logging
import os

IMAGE_EXTENSIONS = ("JPEG", "JPG", "HEIC", "CR2", "TIFF", "TIF", "GIF", "FLV", "MOV", "MP4", "PNG", "AVI", "3GP", "M4V")

logger = logging.getLogger(__name__)


class Update:
    """Incapsulates information about a change that needs to be applied"""

    def __init__(self, action, remote, photo=None, name=None, album_name=None, *args, **kwargs):
        self.action = action
        self.name = name or photo["name"]
        self.remote = remote
        self.photo = photo.copy() if photo else None
        self.album_name = album_name

    def data(self):
        return self.remote.get_data(self.photo)


class BaseRemote:
    """Common functionality between local folder remotes and online remotes"""

    new_state = None

    def __init__(self, name="local", *args, **kwargs):
        self.name = name
        self.state_file = os.path.join("/river/config", name + "_state.json")
        self.state = self.load_old_state(self.state_file)

    @staticmethod
    def load_old_state(state_file):
        if os.path.exists(state_file):
            with open(state_file, "r") as infile:
                return json.load(infile)
        else:
            return {"photos": [], "albums": []}

    def get_new_state(self, no_state_cache=False):
        self.state = {"photos": self.get_photos(), "albums": self.get_albums()}
        with open(self.state_file, "w") as infile:
            json.dump(self.state, infile, default=str)
        return self.state

    def get_photos(self):
        raise NotImplementedError

    def get_albums(self):
        raise NotImplementedError

    def get_data(self, photo):
        """Returns binary data of an individual photo"""
        raise NotImplementedError

    def prepare_data(self, updates):
        """Batch action to prepare for download of photos in the updates"""
        return

    def get_fixes(self):
        """Create a list of changes to the remote itself"""
        return []

    def do_fixes(self, fixes):  # pylint: disable=unused-argument
        """Apply the fixes"""
        return

    def find_album(self, name):
        matching = [x for x in self.state["albums"] if x["name"] == name]
        if matching:
            return matching[0]
        return None

    def find_photo(self, name):
        matching = [x for x in self.state["photos"] if x["name"] == name]
        if matching:
            return matching[0]
        return None

    def get_merge_updates(self, other):
        """Return updates to add items from other remote"""
        updates = []
        # Find new photos
        for aphoto in other.state["photos"]:
            if not self.find_photo(aphoto["name"]):
                logger.info("Remote %s: new photo %s found in %s", self.name, aphoto["name"], other.name)
                updates.append(Update(action="new", photo=aphoto, remote=other))

        # Find new albums
        new_albums = set()
        for album in other.state["albums"]:
            if not self.find_album(album["name"]):
                logger.info("Remote %s: new album %s found in %s", self.name, album["name"], other.name)
                updates.append(Update(action="new_album", photo=album, remote=other))
                new_albums.add(album["name"])

        # Find added photos to existing albums
        for album in other.state["albums"]:
            if album["name"] in new_albums:
                continue
            old_album = self.find_album(album["name"])
            if not old_album:
                logger.error("Album not found while trying to add photos to it: %s not in %s", album["name"], self.state["albums"])
                continue
            print(album["photos"])
            print(old_album["photos"])
            new_photos = set(album["photos"]) - set(old_album["photos"])
            for new_photo in new_photos:
                logger.info("Remote %s: photo %s was added to album %s", self.name, new_photo, album["name"])
                updates.append(Update(action="new_album_photo", name=new_photo, remote=other, album_name=album["name"]))

        return updates
