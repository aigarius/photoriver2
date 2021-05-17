"""Remotes implementation - state of a local folder"""
import logging
import os
import shutil

import requests

from photoriver2.remote_base import BaseRemote

IMAGE_EXTENSIONS = ("JPEG", "JPG", "HEIC", "CR2", "TIFF", "TIF")

logger = logging.getLogger(__name__)


def deconflict(path):
    if not os.path.exists(path):
        return path
    if "." in os.path.basename(path):
        base, ext = path.rsplit(".", 1)
    else:
        base = path
        ext = ""
    if base[-3] != "_" or not base[-2:].isdigit():
        return deconflict(base + "_01." + ext)
    return deconflict("{}_{:02}.{}".format(base[:-3], int(base[-2:]) + 1, ext))


class LocalRemote(BaseRemote):
    """Remote representing a local folder with photos"""

    folder = None

    def __init__(self, folder, *args, **kwargs):
        self.folder = folder
        super().__init__(*args, **kwargs)

    def get_photos(self):
        photos = []
        for root, _, files in os.walk(self.folder):
            for afile in files:
                name = os.path.relpath(os.path.join(root, afile), self.folder)
                if "." in name and name.rsplit(".", 1)[1].upper() in IMAGE_EXTENSIONS:
                    if not os.path.islink(os.path.join(root, afile)):
                        # pylint: disable=cell-var-from-loop
                        photos.append({"name": name, "data": lambda n=os.path.join(root, afile): open(n, "rb")})
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

    # TODO figure out solution to match 2008/8/3/IMG1232.JPG to 2008/08/03/IMG1232.JPG
    def _do_photo_updates(self, updates):
        for update in updates:
            if update["action"] == "new":
                if not os.path.exists(self._abs(update["name"])):
                    logger.info("Remote %s: adding photo %s", self.name, update["name"])
                    os.makedirs(self._abs(os.path.dirname(update["name"])), exist_ok=True)
                    try:
                        with open(self._abs(update["name"]), "wb") as outfile:
                            infile = update["data"]()
                            outfile.write(infile.read())
                            infile.close()
                    except (requests.exceptions.HTTPError, OSError, IOError):
                        os.remove(self._abs(update["name"]))
                        raise
            elif update["action"] == "del":
                if os.path.exists(self._abs(update["name"])):
                    logger.info("Remote %s: deleting photo %s", self.name, update["name"])
                    os.remove(self._abs(update["name"]))
            elif update["action"] == "mv":
                if os.path.exists(self._abs(update["name"])):
                    if not os.path.exists(self._abs(update["new_name"])):
                        logger.info("Remote %s: moving photo %s to %s", self.name, update["name"], update["new_name"])
                        os.makedirs(self._abs(os.path.dirname(update["new_name"])), exist_ok=True)
                        os.rename(self._abs(update["name"]), self._abs(update["new_name"]))

    def _do_album_updates(self, updates):
        for update in updates:
            if update["action"] == "new_album":
                album_path = self._abs(os.path.join("albums", update["name"]))
                if not os.path.exists(album_path):
                    logger.info("Remote %s: creating album %s", self.name, update["name"])
                    os.makedirs(album_path)
                    for aphoto in update["photos"]:
                        os.symlink(
                            os.path.relpath(self._abs(aphoto), album_path),
                            os.path.join(album_path, os.path.basename(aphoto)),
                        )
            elif update["action"] == "del_album":
                album_path = self._abs(os.path.join("albums", update["name"]))
                logger.info("Remote %s: deleting album %s", self.name, update["name"])
                shutil.rmtree(album_path, ignore_errors=True)
            elif update["action"] == "new_album_photo":
                album_path = self._abs(os.path.join("albums", update["album_name"]))
                found = False
                for image in os.listdir(album_path):
                    if os.path.realpath(os.path.join(album_path, image)) == self._abs(update["name"]):
                        found = True
                if not found:
                    logger.info(
                        "Remote %s: adding photos %s to album %s", self.name, update["name"], update["album_name"]
                    )
                    link_path = os.path.join(album_path, os.path.basename(update["name"]))
                    link_path = deconflict(link_path)
                    os.symlink(
                        os.path.relpath(self._abs(update["name"]), album_path),
                        link_path,
                    )
            elif update["action"] == "del_album_photo":
                album_path = self._abs(os.path.join("albums", update["album_name"]))
                for image in os.listdir(album_path):
                    if os.path.realpath(os.path.join(album_path, image)) == self._abs(update["name"]):
                        logger.info(
                            "Remote %s: removing photos %s to album %s",
                            self.name,
                            update["name"],
                            update["album_name"],
                        )
                        os.remove(os.path.join(album_path, image))
