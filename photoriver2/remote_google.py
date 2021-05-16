"""Remotes implementation - state of a Google Photo Library"""
from photoriver2.remote_base import BaseRemote
from photoriver2.gphoto_api import GPhoto


class GoogleRemote(BaseRemote):
    """Remote representing a Google Library with photos"""

    api = None

    def __init__(self, token_cache, *args, **kwargs):
        self.api = GPhoto(token_cache)
        super().__init__(*args, **kwargs)

    def get_photos(self):
        photos = self.api.get_photos()

        for photo in photos:
            # pylint: disable=cell-var-from-loop
            photo["data"] = lambda n=self.api, m=photo["id"]: n.read_photo(m)
        return sorted(photos, key=lambda x: x["name"])

    def get_albums(self):
        albums = self.api.get_albums()
        for album in albums:
            album["photos"] = [x["id"] for x in self.api.get_photos(album_id=album["id"])]
        return sorted(albums, key=lambda x: x["name"])

    def _do_photo_updates(self, updates):
        raise NotImplementedError

    def _do_album_updates(self, updates):
        raise NotImplementedError
