"""Remotes implementation - state of a Google Photo Library"""
import logging

from datetime import datetime

from photoriver2.remote_base import BaseRemote
from photoriver2.gphoto_api import GPhoto

logger = logging.getLogger(__name__)


class GoogleRemote(BaseRemote):
    """Remote representing a Google Library with photos"""

    api = None

    def __init__(self, token_cache, *args, **kwargs):
        self.api = GPhoto(token_cache)
        super().__init__(*args, **kwargs)

    def get_photos(self):
        photos = self.api.get_photos()
        now = datetime.now()

        for photo in photos:
            # pylint: disable=cell-var-from-loop
            photo["modified"] = now
            photo["data"] = lambda n=self.api, m=photo: n.read_photo(m)
            photo["name"] = self._get_name(photo)
        return sorted(photos, key=lambda x: x["name"])

    def _get_name(self, photo):
        filename = photo["filename"]
        path_date = datetime.strptime(photo["raw"]["mediaMetadata"]["creationTime"][:18], "%Y-%m-%dT%H:%M:%S")
        return "{:04d}/{:02d}/{:02d}/{}".format(path_date.year, path_date.month, path_date.day, filename)

    def get_albums(self):
        albums = self.api.get_albums()
        for album in albums:
            album["photos"] = [self._get_name(x) for x in self.api.get_photos(album_id=album["id"])]
        return sorted(albums, key=lambda x: x["name"])

    def _do_photo_updates(self, updates):
        pass
        #  raise NotImplementedError

    def _do_album_updates(self, updates):
        pass
        #  raise NotImplementedError
