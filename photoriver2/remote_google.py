"""Remotes implementation - state of a Google Photo Library"""
import pickle
import logging
import os
import time

from datetime import datetime

import requests

from photoriver2.remote_base import BaseRemote
from photoriver2.gphoto_api import GPhoto

logger = logging.getLogger(__name__)

class DataExpired(Exception):
    pass

class GoogleRemote(BaseRemote):
    """Remote representing a Google Library with photos"""

    def __init__(self, token_cache, *args, **kwargs):
        self.api = GPhoto(token_cache)
        super().__init__(*args, **kwargs)

    def get_data(self, photo):
        if not "raw" in photo:
            photo = self.find_photo(photo["name"])
        try:
            return self.api.read_photo(photo)
        except requests.exceptions.HTTPError:
            logger.warning("Error reading photo data, likely the state expired")
            raise DataExpired

    def get_photos(self):
        logger.info("Getting photos list from Google")
        photos = [x for x in self.api.get_photos(archived=True)]
        now = datetime.now()

        for photo in photos:
            photo["modified"] = now.isoformat()
            photo["name"] = self._get_name(photo)
        photos = sorted(photos, key=lambda x: x["name"])
        logger.info("Getting photos list from Google - done, found %s", len(photos))
        return photos

    @staticmethod
    def _get_name(photo):
        filename = photo["filename"]
        if not "." in filename:
            filename += ".jpg"
        path_date = datetime.strptime(photo["raw"]["mediaMetadata"]["creationTime"][:18], "%Y-%m-%dT%H:%M:%S")
        local_name = f"{path_date.year:04d}/{path_date.month:02d}/{path_date.day:02d}/{filename}"
        return local_name

    def get_albums(self):
        logger.info("Getting albums list from Google")
        albums = self.api.get_albums()
        for album in albums:
            if "/" in album["name"]:
                album["name"] = album["name"].replace("/", "_")
            logger.info("Remote %s: Loading photo info of album %s: ", self.name, album["name"])
            album["photos"] = sorted([self._get_name(x) for x in self.api.get_photos(album_id=album["id"])])
        logger.info("Getting albums list from Google - done, found %s", len(albums))
        return sorted(albums, key=lambda x: x["name"])

    def do_updates(self, updates):

        # Do the downloads as a batch
        # TODO this function should not have that much knowledge about local file remote internal data structures
        new_media = self.api.batch_upload([os.path.join(x.remote.folder, x.name) for x in updates if x.action == "new"])
        # TODO append to self.state["photos"]

        for update in updates:
            if update.action == "new_album":
                logger.info("Remote %s: creating album %s", self.name, update.name)
                album_data = self.api.create_album(update.name)
                # TODO append to self.state["albums"]
                new_media = self.api.batch_upload([os.path.join(x.remote.folder, x) for x in update.photo["photos"]], album_data["id"])
                # TODO append to self.state["photos"]

        new_album_photos = [x for x in updates if x.action == "new_album_photo"]
        updated_albums = set(x.album_name for x in new_album_photos)
        for album in updated_albums:
            album_id = [x["id"] for x in self.state["albums"] if x["name"] == album][0]
            self.api.batch_upload([os.path.join(x.remote.folder, x.name) for x in new_album_photos if x.album_name == album], album_id)
