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
            return {"photos": [], "albums": []}

    def get_new_state(self):
        return {"photos": self.get_photos(), "albums": self.get_albums()}

    def get_photos(self):
        raise NotImplementedError

    def get_albums(self):
        raise NotImplementedError

    def get_updates(self):
        """Create a list of updates that happened from old state to new state"""
        updates = []
        added = set()
        deleted = set()
        # Find deleted photos
        for aphoto in self.old_state["photos"]:
            if not any(x["name"] == aphoto["name"] for x in self.new_state["photos"]):
                update = aphoto.copy()
                update["action"] = "del"
                updates.append(update)
                deleted.add(os.path.basename(update["name"]))
        # Find new photos
        for aphoto in self.new_state["photos"]:
            if not any(x["name"] == aphoto["name"] for x in self.old_state["photos"]):
                update = aphoto.copy()
                update["action"] = "new"
                updates.append(update)
                added.add(os.path.basename(update["name"]))
        # Identify moved files (same basename, del and new at the same check)
        moved = added & deleted
        moved_updates = [x for x in updates if os.path.basename(x["name"]) in moved]
        updates = [x for x in updates if os.path.basename(x["name"]) not in moved]
        for name in moved:
            update = [x for x in moved_updates if x["action"] == "del" and os.path.basename(x["name"]) == name][0]
            update["action"] = "mv"
            update["new_name"] = [
                x for x in moved_updates if x["action"] == "new" and os.path.basename(x["name"]) == name
            ][0]["name"]
            updates.append(update)
        return updates


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
        return sorted(albums, key=lambda x: x["name"])


class GoogleRemote(BaseRemote):
    """Connection to Google Photos service via a remote"""


class FlickrRemote(BaseRemote):
    """Connection to Flickr service via a remote"""
