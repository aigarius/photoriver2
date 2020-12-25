"""Remotes implementation - state of an instance of a photo collection"""
import json
import os
import shutil

IMAGE_EXTENSIONS = ("JPEG", "JPG", "HEIC", "CR2", "TIFF", "TIF")


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
        return {"photos": self.get_photos(), "albums": self.get_albums()}

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

    def _get_photo_updates(self):
        updates = []
        # Find deleted photos
        deleted = set()
        for aphoto in self.old_state["photos"]:
            if not any(x["name"] == aphoto["name"] for x in self.new_state["photos"]):
                update = aphoto.copy()
                update["action"] = "del"
                updates.append(update)
                deleted.add(os.path.basename(update["name"]))
        # Find new photos
        added = set()
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

    def _get_album_updates(self):
        updates = []
        # Find new albums
        new_albums = set()
        for album in self.new_state["albums"]:
            if not any(x["name"] == album["name"] for x in self.old_state["albums"]):
                update = album.copy()
                update["action"] = "new_album"
                updates.append(update)
                new_albums.add(update["name"])
        # Find deleted albums
        del_albums = set()
        for album in self.old_state["albums"]:
            if not any(x["name"] == album["name"] for x in self.new_state["albums"]):
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
                updates.append(
                    {
                        "action": "new_album_photo",
                        "name": new_photo,
                        "album_name": album["name"],
                    }
                )
            for del_photo in del_photos:
                updates.append(
                    {
                        "action": "del_album_photo",
                        "name": del_photo,
                        "album_name": album["name"],
                    }
                )
        return updates


class LocalRemote(BaseRemote):
    """Remote representing a local folder with photos"""

    folder = None

    def get_photos(self):
        photos = []
        for root, _, files in os.walk(self.folder):
            for afile in files:
                name = os.path.relpath(os.path.join(root, afile), self.folder)
                if "." in name and name.rsplit(".", 1)[1].upper() in IMAGE_EXTENSIONS:
                    if not os.path.islink(os.path.join(root, afile)):
                        photos.append({"name": name})
        return sorted(photos, key=lambda x: x["name"])

    def get_albums(self):
        albums = []
        if os.path.exists(os.path.join(self.folder, "albums")):
            dirs = os.scandir(os.path.join(self.folder, "albums"))
            for adir in dirs:
                if not adir.is_dir():
                    continue
                photos = os.listdir(adir.path)
                # Resolve symlinks in paths of photos in albums
                photos = [os.path.relpath(os.path.realpath(os.path.join(adir.path, x)), self.folder) for x in photos]
                albums.append(
                    {
                        "name": adir.name,
                        "photos": sorted(photos),
                    }
                )
        return sorted(albums, key=lambda x: x["name"])

    def get_fixes(self):
        fixes = []
        # Files in albums/ should be symlinks
        for root, _, files in os.walk(os.path.join(self.folder, "albums")):
            for afile in files:
                if "." in afile and afile.rsplit(".", 1)[1].upper() in IMAGE_EXTENSIONS:
                    full_path = os.path.join(root, afile)
                    if not os.path.islink(full_path):
                        fixes.append(
                            {
                                "action": "symlink",
                                "name": os.path.relpath(full_path, self.folder),
                                "to": os.path.basename(full_path),
                            }
                        )
        return fixes

    def _abs(self, path):
        return os.path.join(self.folder, path)

    def do_fixes(self, fixes):
        for afix in fixes:
            if afix["action"] == "symlink":
                # Move the file over to new location (making parent folders as needed)
                os.makedirs(self._abs(os.path.dirname(afix["to"])))
                os.rename(self._abs(afix["name"]), self._abs(afix["to"]))
                # Create a relative symlink in the old place pointing to the new location
                os.symlink(
                    os.path.relpath(self._abs(afix["to"]), os.path.dirname(self._abs(afix["name"]))),
                    self._abs(afix["name"]),
                )

    def _do_photo_updates(self, updates):
        for update in updates:
            if update["action"] == "new":
                if not os.path.exists(self._abs(update["name"])):
                    os.makedirs(self._abs(os.path.dirname(update["name"])), exist_ok=True)
                    with open(self._abs(update["name"]), "wb") as outfile:
                        outfile.write(update["data"]())
            elif update["action"] == "del":
                if os.path.exists(self._abs(update["name"])):
                    os.remove(self._abs(update["name"]))
            elif update["action"] == "mv":
                if os.path.exists(self._abs(update["name"])):
                    if not os.path.exists(self._abs(update["new_name"])):
                        os.makedirs(self._abs(os.path.dirname(update["new_name"])), exist_ok=True)
                        os.rename(self._abs(update["name"]), self._abs(update["new_name"]))

    def _do_album_updates(self, updates):
        for update in updates:
            if update["action"] == "new_album":
                album_path = self._abs(os.path.join("albums", update["name"]))
                os.makedirs(album_path)
                for aphoto in update["photos"]:
                    os.symlink(
                        os.path.relpath(self._abs(aphoto), album_path),
                        os.path.join(album_path, os.path.basename(aphoto)),
                    )
            elif update["action"] == "del_album":
                album_path = self._abs(os.path.join("albums", update["name"]))
                shutil.rmtree(album_path, ignore_errors=True)
            elif update["action"] == "new_album_photo":
                album_path = self._abs(os.path.join("albums", update["album_name"]))
                os.symlink(
                    os.path.relpath(self._abs(update["name"]), album_path),
                    os.path.join(album_path, os.path.basename(update["name"])),
                )
            elif update["action"] == "del_album_photo":
                album_path = self._abs(os.path.join("albums", update["album_name"]))
                os.remove(os.path.join(album_path, os.path.basename(update["name"])))


class GoogleRemote(BaseRemote):
    """Connection to Google Photos service via a remote"""


class FlickrRemote(BaseRemote):
    """Connection to Flickr service via a remote"""
