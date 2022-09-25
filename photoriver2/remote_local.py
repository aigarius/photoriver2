"""Remotes implementation - state of a local folder"""
import concurrent.futures
import logging
import os
import shutil
import re
import datetime

import dateutil
import dateutil.tz
import dateutil.utils
import dateutil.parser
import requests

from PIL import Image, UnidentifiedImageError

from photoriver2.remote_base import BaseRemote, IMAGE_EXTENSIONS

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
    return deconflict(f"{base[:-3]}_{int(base[-2:])+1:02}.{ext}")


class LocalRemote(BaseRemote):
    """Remote representing a local folder with photos"""

    folder = None

    def __init__(self, folder, *args, **kwargs):
        self.folder = folder
        super().__init__(*args, **kwargs)

    def get_photos(self):
        logger.info("Getting photos list from %s", self.folder)
        photos = []
        for root, _, files in os.walk(self.folder):
            for afile in files:
                name = os.path.relpath(os.path.join(root, afile), self.folder)
                if "." in name and name.rsplit(".", 1)[1].upper() in IMAGE_EXTENSIONS:
                    if not os.path.islink(os.path.join(root, afile)):
                        # pylint: disable=cell-var-from-loop,consider-using-with
                        photos.append({"name": name, "filename": os.path.join(root, afile)})
        logger.info("Getting photos list from %s - done, found %s", self.folder, len(photos))
        return sorted(photos, key=lambda x: x["name"])

    def get_albums(self):
        logger.info("Getting albums from %s", self.folder)
        albums = []
        if os.path.exists(os.path.join(self.folder, "albums")):
            dirs = os.scandir(os.path.join(self.folder, "albums"))
            for adir in dirs:
                logger.debug("Looking into album %s", adir)
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
        logger.info("Getting albums from %s - done, found %s", self.folder, len(albums))
        return sorted(albums, key=lambda x: x["name"])

    def get_data(self, photo):  # TODO: replace with a context manager generator
        return open(photo["filename"], "rb")

    def get_fixes(self):
        fixes = []
        default_tz = dateutil.tz.gettz()
        Image.MAX_IMAGE_PIXELS = 150000000
        
        for root, _, files in os.walk(self.folder):
            for afile in files:
                if "." in afile and afile.rsplit(".", 1)[1].upper() in IMAGE_EXTENSIONS:
                    full_path = os.path.join(root, afile)
                    if os.path.islink(full_path):
                        continue
                    basename = os.path.basename(full_path)
                    try:
                        exif_data = Image.open(full_path)._getexif()
                    except (UnidentifiedImageError, Image.DecompressionBombError, AttributeError):
                        logger.debug("No exif date found on %s", full_path)
                        continue
                    # Look into EXIF data "DateTimeOriginal", "DateTimeDigitized" or "DateTime"
                    if not exif_data:
                        logger.debug("No exif date found on %s", full_path)
                        continue
                    exif_date = exif_data.get(36867, '').strip() or exif_data.get(36868, '').strip() or exif_data.get(306, '').strip()
                    if not exif_date or not exif_date.isprintable():
                        logger.debug("No exif date found on %s", full_path)
                        continue
                    # Assume that exif date is in local timezone
                    exif_date = datetime.datetime.strptime(exif_date[:18], "%Y:%m:%d %H:%M:%S")
                    exif_date.replace(tzinfo=default_tz)
                    # Correct date will be in UTC timezone
                    utc_date = exif_date.utctimetuple()
                    correct_path = f"{utc_date[0]:04d}/{utc_date[1]:02d}/{utc_date[2]:02d}/{basename}"
                    if correct_path != os.path.relpath(full_path, self.folder):
                        logger.debug("Paths do not match: should be %s and not %s", correct_path, os.path.relpath(full_path, self.folder))
                        fixes.append(
                            {
                                "action": "rename",
                                "name": os.path.relpath(full_path, self.folder),
                                "to": correct_path,
                            }
                        )


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
                os.makedirs(self._abs(os.path.dirname(afix["to"])), exist_ok=True)
                os.rename(self._abs(afix["name"]), self._abs(afix["to"]))
                # Create a relative symlink in the old place pointing to the new location
                os.symlink(
                    os.path.relpath(self._abs(afix["to"]), os.path.dirname(self._abs(afix["name"]))),
                    self._abs(afix["name"]),
                )
            elif afix["action"] == "rename":
                os.makedirs(self._abs(os.path.dirname(afix["to"])), exist_ok=True)
                os.rename(self._abs(afix["name"]), self._abs(afix["to"]))

    def put_data(self, update):
        """Put a photo from other remote into this one"""
        if not os.path.exists(self._abs(update.name)):
            logger.info("Remote %s: adding photo %s", self.name, update.name)
            os.makedirs(self._abs(os.path.dirname(update.name)), exist_ok=True)
            try:
                with open(self._abs(update.name), "wb") as outfile:
                    infile = update.data()
                    outfile.write(infile.read())
                    infile.close()
            except (requests.exceptions.HTTPError, OSError, IOError):
                os.remove(self._abs(update.name))
                raise

    def do_updates(self, updates):

        # Do the downloads as a batch
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            list(executor.map(self.put_data, [x for x in updates if x.action == "new"]))

        for update in updates:
            if update.action == "new_album":
                album_path = self._abs(os.path.join("albums", update.name))
                if not os.path.exists(album_path):
                    logger.info("Remote %s: creating album %s", self.name, update.name)
                    os.makedirs(album_path)
                    for aphoto in update.photo["photos"]:
                        if not os.path.exists(os.path.join(album_path, os.path.basename(aphoto))):
                            os.symlink(
                                os.path.relpath(self._abs(aphoto), album_path),
                                deconflict(os.path.join(album_path, os.path.basename(aphoto))),
                            )
            elif update.action == "new_album_photo":
                album_path = self._abs(os.path.join("albums", update.album_name))
                found = False
                for image in os.listdir(album_path):
                    if os.path.realpath(os.path.join(album_path, image)) == self._abs(update.name):
                        found = True
                if not found:
                    logger.info("Remote %s: adding photos %s to album %s", self.name, update.name, update.album_name)
                    link_path = os.path.join(album_path, os.path.basename(update.name))
                    link_path = deconflict(link_path)
                    os.symlink(
                        os.path.relpath(self._abs(update.name), album_path),
                        link_path,
                    )
