"""Remotes implementation - state of an instance of a photo collection"""
import json
import logging
import os

IMAGE_EXTENSIONS = ("JPEG", "JPG", "HEIC", "CR2", "TIFF", "TIF")

logger = logging.getLogger(__name__)


class BaseRemote:
    """Common functionality between local folder remotes and online remotes"""

    new_state = None

    def __init__(self, name="local"):
        self.name = name
        self.state_file = os.path.join("/river/config", name + "_state.json")
        self.old_state = self.load_old_state(self.state_file)

    @staticmethod
    def load_old_state(config_file):
        if os.path.exists(config_file):
            with open(config_file, "r") as infile:
                return json.load(infile)
        else:
            return {"photos": [], "albums": []}

    def get_new_state(self):
        self.new_state = {"photos": self.get_photos(), "albums": self.get_albums()}
        return self.new_state

    def save_new_state(self):
        with open(self.state_file, "w") as infile:
            json.dump(self.new_state, infile)

    def get_photos(self):
        raise NotImplementedError

    def get_albums(self):
        raise NotImplementedError

    def get_updates(self):
        """Create a list of updates that happened from old state to new state"""
        return self._get_photo_updates() + self._get_album_updates()

    def do_updates(self, updates):
        self._do_photo_updates(updates)
        self._do_album_updates(updates)

    def _do_photo_updates(self, updates):
        raise NotImplementedError

    def _do_album_updates(self, updates):
        raise NotImplementedError

    def get_fixes(self):
        """Create a list of changes to the remote itself"""
        return []

    def do_fixes(self, fixes):  # pylint: disable=unused-argument
        """Apply the fixes"""
        return

    def get_merge_updates(self, other):
        """Return updates to add items from other remote"""
        updates = []
        for aphoto in other.new_state["photos"]:
            if not any(x["name"] == aphoto["name"] for x in self.new_state["photos"]):
                logger.info("Remote %s: new photo %s found in %s", self.name, aphoto["name"], other.name)
                update = aphoto.copy()
                update["action"] = "new"
                updates.append(update)
        # Find new albums
        new_albums = set()
        for album in other.new_state["albums"]:
            if not any(x["name"] == album["name"] for x in self.new_state["albums"]):
                logger.info("Remote %s: new album %s found in %s", self.name, album["name"], other.name)
                update = album.copy()
                update["action"] = "new_album"
                updates.append(update)
                new_albums.add(update["name"])
        # Find added/deleted photos to existing albums
        for album in other.new_state["albums"]:
            if album["name"] in new_albums:
                continue
            old_album = [x for x in self.new_state["albums"] if x["name"] == album["name"]][0]
            new_photos = set(album["photos"]) - set(old_album["photos"])
            for new_photo in new_photos:
                logger.info(
                    "Remote %s: new photo %s in album %s found in %s", self.name, new_photo, album["name"], other.name
                )
                updates.append(
                    {
                        "action": "new_album_photo",
                        "name": new_photo,
                        "album_name": album["name"],
                    }
                )
        return updates

    def _get_photo_updates(self):
        updates = []
        # Find deleted photos
        deleted = set()
        for aphoto in self.old_state["photos"]:
            if not any(x["name"] == aphoto["name"] for x in self.new_state["photos"]):
                logger.info("Remote %s: photo %s was deleted", self.name, aphoto["name"])
                update = aphoto.copy()
                update["action"] = "del"
                updates.append(update)
                deleted.add(os.path.basename(update["name"]))
        # Find new photos
        added = set()
        for aphoto in self.new_state["photos"]:
            if not any(x["name"] == aphoto["name"] for x in self.old_state["photos"]):
                logger.info("Remote %s: photo %s was added", self.name, aphoto["name"])
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
            logger.info("Remote %s: photo %s was moved to %s", self.name, update["name"], update["new_name"])
            updates.append(update)
        return updates

    def _get_album_updates(self):
        updates = []
        # Find new albums
        new_albums = set()
        for album in self.new_state["albums"]:
            if not any(x["name"] == album["name"] for x in self.old_state["albums"]):
                logger.info("Remote %s: album %s was added", self.name, album["name"])
                update = album.copy()
                update["action"] = "new_album"
                updates.append(update)
                new_albums.add(update["name"])
        # Find deleted albums
        del_albums = set()
        for album in self.old_state["albums"]:
            if not any(x["name"] == album["name"] for x in self.new_state["albums"]):
                logger.info("Remote %s: album %s was deleted", self.name, album["name"])
                update = album.copy()
                update["action"] = "del_album"
                del update["photos"]
                updates.append(update)
                del_albums.add(update["name"])
        # Find added/deleted photos to existing albums
        for album in self.new_state["albums"]:
            if album["name"] in new_albums:
                continue
            old_album = [x for x in self.old_state["albums"] if x["name"] == album["name"]][0]
            new_photos = set(album["photos"]) - set(old_album["photos"])
            del_photos = set(old_album["photos"]) - set(album["photos"])
            for new_photo in new_photos:
                logger.info("Remote %s: photo %s was added to album %s", self.name, new_photo, album["name"])
                updates.append(
                    {
                        "action": "new_album_photo",
                        "name": new_photo,
                        "album_name": album["name"],
                    }
                )
            for del_photo in del_photos:
                logger.info("Remote %s: photo %s was deleted from album %s", self.name, del_photo, album["name"])
                updates.append(
                    {
                        "action": "del_album_photo",
                        "name": del_photo,
                        "album_name": album["name"],
                    }
                )
        return updates
