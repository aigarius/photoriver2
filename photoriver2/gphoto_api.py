"""Google Photo API abstraction module"""
import json
import logging
import os.path
import time

from io import open
from datetime import date, datetime, timedelta

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
        albums = []
        logger.info("Received data about %i albums", len(data.get("albums", [])))
        for entry in data.get("albums", []):
            logger.debug("Processing: %s", entry)
            album = {}
            album["name"] = entry.get("title", entry["id"])
            album["id"] = entry["id"]
            album["user_url"] = entry["productUrl"]
            album["count"] = int(entry.get("mediaItemsCount", 0))
            albums.append(album)
        return albums

    def get_albums(self):
        logger.info("Retrieving album list")
        payload = {"pageSize": 50}

        data = self._load_new_data(URL_ALBUMS, "get", payload)
        albums = self._extract_albums(data)
        while "nextPageToken" in data:
            payload["page_token"] = data["nextPageToken"]
            data = self._load_new_data(URL_ALBUMS, "get", payload)
            albums.extend(self._extract_albums(data))

        logger.info(
            "Retrieving album list - done: found %i albums with %i items",
            len(albums),
            sum([x["count"] for x in albums]),
        )
        return albums

    def _load_new_data(self, url, method, payload):
        if method == "get":
            response = requests.get(url, params=payload, headers=self.headers)
        elif method == "post":
            response = requests.post(url, data=json.dumps(payload), headers=self.headers)
        if response.status_code != 200:
            logger.error("Failed call to '%s' on '%s' with payload '%s'", method, url, payload)
            response.raise_for_status()
        feed = response.text.encode("utf8")
        return json.loads(feed)

    def _extract_photos(self, data):
        logger.debug("Received %i items", len(data.get("mediaItems", [])))
        photos = []
        for entry in data.get("mediaItems", []):
            if not entry.get("mediaType", "image/jpeg").startswith("image"):
                continue
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

    def get_photos(self, album_id=None, start_date=None, end_date=None):
        logger.info("Retrieving photos for album %s or time %s-%s", album_id, start_date, end_date)
        payload = {"pageSize": 100}
        method = "get"
        url = URL_PHOTOS
        if album_id:
            payload["albumId"] = album_id
            method = "post"
            url += ":search"
        elif start_date:
            method = "post"
            url += ":search"
            start_date = {
                "year": start_date.year,
                "month": start_date.month,
                "day": start_date.day,
            }
            if not end_date:
                end_date = date.today()
            end_date = {
                "year": end_date.year,
                "month": end_date.month,
                "day": end_date.day,
            }
            payload["filters"] = {"dateFilter": {"ranges": [{"startDate": start_date, "endDate": end_date}]}}

        data = self._load_new_data(url, method, payload)
        photos = self._extract_photos(data)
        total_count = len(photos)
        yield from photos
        while "nextPageToken" in data:
            payload["page_token"] = data["nextPageToken"]
            data = self._load_new_data(url, method, payload)
            photos = self._extract_photos(data)
            total_count += len(photos)
            logger.info("Total photos now retrieved: %s", total_count)
            yield from photos

        logger.info(
            "Retrieving photos - done: found %i photos",
            total_count,
        )

    def read_photo(self, photo):
        """Return a file-like object that can be read() to get photo file data"""
        if datetime.now() - photo.get("modified", datetime.now()) > timedelta(minutes=59):
            logger.warning("Media URL expired, refreshing")
            response = requests.get(URL_PHOTOS + "/" + photo["id"], headers=self.headers)
            response.raise_for_status()
            feed = response.text.encode("utf8")
            photo = json.loads(feed)
        response = requests.get(photo["raw"]["baseUrl"] + "=d", headers=self.headers, stream=True)
        if response.status_code != 200:
            time.sleep(1)
            response = requests.get(photo["raw"]["baseUrl"] + "=d", headers=self.headers, stream=True)
            if response.status_code != 200:
                time.sleep(1)
                response = requests.get(photo["raw"]["baseUrl"] + "=d", headers=self.headers, stream=True)
        response.raise_for_status()
        return response.raw

    def create_album(self, title):
        raise NotImplementedError

    def upload_media(self, filename):
        """Do the media upload step of adding a photo to GPhoto Library - returns a token for batch media creation"""
        headers = {
            "Content-type": "application/octet-stream",
            "X-Goog-Upload-Content-Type": "image/jpeg",
            "X-Goog-Upload-Protocol": "raw",
        }
        headers.update(self.headers)
        with open(filename, "rb") as infile:
            response = requests.post(
                "https://photoslibrary.googleapis.com/v1/uploads", headers=headers, data=infile.read()
            )
        response.raise_for_status()
        return response.text

    def create_media(self, data_items):
        """Batch media creation - takes up to 50 items of (filename, upload_token) and creates all at once"""
        data = {
            "newMediaItems": [],
        }
        for data_item in data_items:
            data["newMediaItems"].append(
                {
                    "simpleMediaItem": {
                        "fileName": os.path.basename(data_item[0]),
                        "uploadToken": data_item[1],
                    }
                }
            )
        response = requests.post(
            "https://photoslibrary.googleapis.com/v1/mediaItems:batchCreate", json=data, headers=self.headers
        )
        if response.status_code == 207:
            for item in response.json.get("newMediaItemResults", []):
                if item.get("status", {}).get("message", "Failed") != "Success":
                    logger.error("Problem with upload: %s", item)
                    bad_items = [x[0] for x in data_items if x[1] == item.get("uploadToken", "xxx")]
                    logger.error("Files missed uploads: %s", bad_items)
        response.raise_for_status()
