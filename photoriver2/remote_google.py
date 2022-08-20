"""Remotes implementation - state of a Google Photo Library"""
import pickle
import logging
import os
import time

from datetime import datetime

from photoriver2.remote_base import BaseRemote
from photoriver2.gphoto_api import GPhoto

logger = logging.getLogger(__name__)


class GoogleRemote(BaseRemote):
    """Remote representing a Google Library with photos"""

    def __init__(self, token_cache, *args, **kwargs):
        self.api = GPhoto(token_cache)
        super().__init__(*args, **kwargs)

    def get_data(self, photo):
        return self.api.read_photo(photo)

    def get_photos(self):
        photos = self.api.get_photos()
        now = datetime.now()

        for photo in photos:
            photo["modified"] = now
            photo["name"] = self._get_name(photo)
        return sorted(photos, key=lambda x: x["name"])

    @staticmethod
    def _get_name(photo):
        filename = photo["filename"]
        path_date = datetime.strptime(photo["raw"]["mediaMetadata"]["creationTime"][:18], "%Y-%m-%dT%H:%M:%S")
        local_name = f"{path_date.year:04d}/{path_date.month:02d}/{path_date.day:02d}/{filename}"
        return local_name

    def get_albums(self):
        albums = self.api.get_albums()
        for album in albums:
            logger.info("Remote %s: Loading photo info of album %s: ", self.name, album["name"])
            album["photos"] = [self._get_name(x) for x in self.api.get_photos(album_id=album["id"])]
        return sorted(albums, key=lambda x: x["name"])

    def do_updates(self, updates):
        pass
        #  raise NotImplementedError
