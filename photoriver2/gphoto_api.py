"""Google Photo API abstraction module"""
import json
import logging
import os.path

from io import open

import requests
import six

logger = logging.getLogger(__name__)

AUTH_URL = "https://accounts.google.com/o/oauth2/auth"
CLIENT_ID = "834388343680-embh8gpuiavu35801g2564sfrkir3rfb.apps.googleusercontent.com"
CLIENT_SECRET = "jMX0btH5hLlfJgxXF6-bUgf6"
REDIRECT_URI = "urn:ietf:wg:oauth:2.0:oob"
TOKEN_URI = "https://accounts.google.com/o/oauth2/token"

URL_PHOTOS = "https://photoslibrary.googleapis.com/v1/mediaItems"
URL_ALBUMS = "https://photoslibrary.googleapis.com/v1/albums"
AUTH_SCOPE = "https://www.googleapis.com/auth/photoslibrary"


class GPhoto:
    """Implement the Google Photo Library API"""

    def __init__(self, token_cache=".cache"):
        self.token_cache = token_cache
        self.token = None
        self.refresh_token = None

        if not self._refresh_token():
            # If we don't have a cached token - get an authorization
            url = "{}?client_id={}&redirect_uri={}&scope={}&response_type=code".format(
                AUTH_URL, CLIENT_ID, REDIRECT_URI, AUTH_SCOPE
            )
            code = six.moves.input("URL: {0}\nPaste authorization code: ".format(url))
            token_json = requests.post(
                TOKEN_URI,
                data={
                    "code": code,
                    "client_id": CLIENT_ID,
                    "client_secret": CLIENT_SECRET,
                    "redirect_uri": "urn:ietf:wg:oauth:2.0:oob",
                    "grant_type": "authorization_code",
                },
            ).json()
            self.token = token_json["access_token"]
            self.refresh_token = token_json["refresh_token"]
            self._write_refresh_token()
        self.headers = {"Authorization": "Bearer {}".format(self.token)}

    def _refresh_token(self):
        self._read_refresh_token()
        if not self.refresh_token:
            return False
        token_json = requests.post(
            TOKEN_URI,
            data={
                "refresh_token": self.refresh_token,
                "client_id": CLIENT_ID,
                "client_secret": CLIENT_SECRET,
                "grant_type": "refresh_token",
            },
        ).json()
        self.token = token_json["access_token"]
        return True

    def _read_refresh_token(self):
        if not os.path.exists(self.token_cache):
            return False
        cache = {}
        with open(self.token_cache, "rb") as cache_file:
            try:
                cache = json.loads(cache_file.read().decode("utf8"))
            except json.JSONDecodeError:
                pass
        self.refresh_token = cache.get("gphoto_refresh_token", None)
        return True

    def _write_refresh_token(self):
        cache = {}
        if os.path.exists(self.token_cache):
            with open(self.token_cache, "rb") as cache_file:
                try:
                    cache = json.loads(cache_file.read().decode("utf8"))
                except json.JSONDecodeError:
                    pass
        cache["gphoto_refresh_token"] = self.refresh_token
        with open(self.token_cache, "wb") as cache_file:
            cache_file.write(json.dumps(cache).encode("utf8"))

    def _extract_albums(self, data):
        albums = {}
        logger.info("Received data about %i albums", len(data.get("albums", [])))
        for entry in data.get("albums", []):
            logger.debug("Processing: %s", entry)
            title = entry.get("title", entry["id"])
            if title not in albums:
                albums[title] = {}
            albums[title]["id"] = entry["id"]
            albums[title]["user_url"] = entry["productUrl"]
            albums[title]["count"] = int(entry.get("mediaItemsCount", 0))
        return albums

    def get_albums(self):
        logger.info("Retrieving album list")
        payload = {"pageSize": 50}

        data = self._load_new_data(URL_ALBUMS, "get", payload)
        albums = self._extract_albums(data)
        while "nextPageToken" in data:
            payload["page_token"] = data["nextPageToken"]
            data = self._load_new_data(URL_ALBUMS, "get", payload)
            albums.update(self._extract_albums(data))

        logger.info(
            "Retrieving album list - done: found %i albums with %i items",
            len(albums),
            sum([x["count"] for x in albums.values()]),
        )
        return albums

    def _load_new_data(self, url, method, payload):
        feed = getattr(requests, method)(url, params=payload, headers=self.headers).text.encode("utf8")
        return json.loads(feed)

    def _extract_photos(self, data):
        logger.info("Received %i items", len(data.get("mediaItems", [])))
        photos = []
        for entry in data.get("mediaItems", []):
            logger.debug("Processing: %s", entry)
            photos.append(
                {
                    "filename": entry["filename"],
                    "id": entry["id"],
                    "description": entry.get("description", entry["filename"]),
                    "raw": entry,
                }
            )
        return photos

    def get_photos(self, album_id=None):
        logger.info("Retrieving album photos for album %s", album_id)
        payload = {"pageSize": 100}
        method = "get"
        url = URL_PHOTOS
        if album_id:
            payload["albumId"] = album_id
            method = "post"
            url += ":search"

        data = self._load_new_data(url, method, payload)
        photos = self._extract_photos(data)
        while "nextPageToken" in data:
            payload["page_token"] = data["nextPageToken"]
            data = self._load_new_data(url, method, payload)
            photos.extend(self._extract_photos(data))

        logger.info(
            "Retrieving album photos - done: found %i photos",
            len(photos),
        )
        return photos

    def create_album(self, title):
        raise NotImplementedError

    def upload(self, photofile, filename, album_id):
        raise NotImplementedError
