"""Verify Google Photo API functionality"""

from datetime import date
from unittest.mock import patch, Mock, call

import pytest

from photoriver2.gphoto_api import GPhoto, URL_PHOTOS


def _get_obj():
    with patch("photoriver2.gphoto_api.GPhoto._refresh_token", return_value=True):
        obj = GPhoto()
    obj.token = "foo_token_foo"
    obj.refresh_token = "foo_refresh_token_foo"
    return obj


def test_init():
    assert _get_obj()


@pytest.mark.parametrize(
    "inputs,photos",
    [
        ([{}], []),
        ([{"nextPageToken": "bar"}, {}], []),
        ([{"mediaItems": []}], []),
        (
            [{"mediaItems": [{"id": "123", "filename": "IMG1.JPG"}]}],
            [
                {
                    "description": "IMG1.JPG",
                    "filename": "IMG1.JPG",
                    "id": "123",
                    "raw": {"filename": "IMG1.JPG", "id": "123"},
                },
            ],
        ),
        (
            [
                {"mediaItems": [{"id": "123", "filename": "IMG1.JPG"}], "nextPageToken": "bar"},
                {"mediaItems": [{"id": "124", "filename": "IMG2.JPG"}]},
            ],
            [
                {
                    "description": "IMG1.JPG",
                    "filename": "IMG1.JPG",
                    "id": "123",
                    "raw": {"filename": "IMG1.JPG", "id": "123"},
                },
                {
                    "description": "IMG2.JPG",
                    "filename": "IMG2.JPG",
                    "id": "124",
                    "raw": {"filename": "IMG2.JPG", "id": "124"},
                },
            ],
        ),
    ],
)
def test_get_photos(inputs, photos):
    obj = _get_obj()
    _new_data = Mock(side_effect=inputs)
    with patch.object(obj, "_load_new_data", _new_data):
        assert obj.get_photos() == photos


@pytest.mark.parametrize(
    "kwargs,calls",
    [
        ({}, [call(URL_PHOTOS, "get", {"pageSize": 100})]),
        (
            {"start_date": date(2021, 3, 4), "end_date": date(2021, 3, 7)},
            [
                call(
                    URL_PHOTOS + ":search",
                    "post",
                    {
                        "pageSize": 100,
                        "filters": {
                            "dateFilter": {
                                "ranges": [
                                    {
                                        "startDate": {"year": 2021, "month": 3, "day": 4},
                                        "endDate": {"year": 2021, "month": 3, "day": 7},
                                    }
                                ]
                            }
                        },
                    },
                )
            ],
        ),
    ],
)
def test_get_photos_args(kwargs, calls):
    obj = _get_obj()
    inputs = [{"mediaItems": [{"id": "123", "filename": "IMG1.JPG"}]}]
    _new_data = Mock(side_effect=inputs)
    with patch.object(obj, "_load_new_data", _new_data):
        obj.get_photos(**kwargs)
        assert _new_data.call_args_list == calls


@pytest.mark.parametrize(
    "inputs,albums",
    [
        ([{}], []),
        ([{"nextPageToken": "bar"}, {}], []),
        ([{"albums": []}], []),
        (
            [{"albums": [{"id": "123", "title": "Album1", "productUrl": "aurl", "mediaItemsCount": "2"}]}],
            [
                {"name": "Album1", "id": "123", "count": 2, "user_url": "aurl"},
            ],
        ),
        (
            [
                {
                    "albums": [{"id": "123", "title": "Album1", "productUrl": "aurl", "mediaItemsCount": "2"}],
                    "nextPageToken": "bar",
                },
                {"albums": [{"id": "124", "title": "Album2", "productUrl": "aurl2", "mediaItemsCount": "3"}]},
            ],
            [
                {"name": "Album1", "id": "123", "count": 2, "user_url": "aurl"},
                {"name": "Album2", "id": "124", "count": 3, "user_url": "aurl2"},
            ],
        ),
    ],
)
def test_get_albums(inputs, albums):
    obj = _get_obj()
    _new_data = Mock(side_effect=inputs)
    with patch.object(obj, "_load_new_data", _new_data):
        assert obj.get_albums() == albums
