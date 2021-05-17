"""Basic Google Remote testing"""

from unittest.mock import patch, Mock

from photoriver2.remote_google import GoogleRemote


@patch("photoriver2.remote_google.GPhoto")
def test_get_albums(mock_api):
    mock_api_obj = Mock()
    mock_api.return_value = mock_api_obj
    mock_api_obj.get_albums.return_value = [{"name": "Album1", "id": "barfoo"}]
    mock_api_obj.get_photos.return_value = [
        {
            "description": "IMG1.JPG",
            "filename": "IMG1.JPG",
            "id": "123",
            "raw": {
                "filename": "IMG1.JPG",
                "id": "123",
                "mediaMetadata": {"creationTime": "2021-02-15T15:32:12.045123456Z"},
            },
        },
        {
            "description": "IMG2.JPG",
            "filename": "IMG2.JPG",
            "id": "124",
            "raw": {
                "filename": "IMG2.JPG",
                "id": "124",
                "mediaMetadata": {"creationTime": "2021-02-16T15:32:14.045123456Z"},
            },
        },
    ]
    remote = GoogleRemote(".config")
    data = remote.get_albums()
    assert data == [{"id": "barfoo", "name": "Album1", "photos": ["2021/02/15/IMG1.JPG", "2021/02/16/IMG2.JPG"]}]
    mock_api_obj.get_albums.assert_called()
    mock_api_obj.get_photos.assert_called_with(album_id="barfoo")


@patch("photoriver2.remote_google.GPhoto")
def test_get_photos(mock_api):
    mock_api_obj = Mock()
    mock_api.return_value = mock_api_obj
    mock_api_obj.get_photos.return_value = [
        {
            "description": "IMG1.JPG",
            "filename": "IMG1.JPG",
            "id": "123",
            "raw": {
                "filename": "IMG1.JPG",
                "id": "123",
                "mediaMetadata": {"creationTime": "2021-02-15T15:32:12Z"},
            },
        },
        {
            "description": "IMG2.JPG",
            "filename": "IMG2.JPG",
            "id": "124",
            "raw": {
                "filename": "IMG2.JPG",
                "id": "124",
                "mediaMetadata": {"creationTime": "2021-02-16T15:32:14Z"},
            },
        },
    ]
    remote = GoogleRemote(".config")
    data = remote.get_photos()
    for entry in data:
        del entry["modified"]
    assert data == [
        {
            "description": "IMG1.JPG",
            "filename": "IMG1.JPG",
            "id": "123",
            "name": "2021/02/15/IMG1.JPG",
            "raw": {
                "filename": "IMG1.JPG",
                "id": "123",
                "mediaMetadata": {"creationTime": "2021-02-15T15:32:12Z"},
            },
        },
        {
            "description": "IMG2.JPG",
            "filename": "IMG2.JPG",
            "id": "124",
            "name": "2021/02/16/IMG2.JPG",
            "raw": {
                "filename": "IMG2.JPG",
                "id": "124",
                "mediaMetadata": {"creationTime": "2021-02-16T15:32:14Z"},
            },
        },
    ]
    mock_api_obj.get_photos.assert_called_with()
