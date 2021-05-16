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
            "raw": {"filename": "IMG1.JPG", "id": "123"},
        },
        {
            "description": "IMG2.JPG",
            "filename": "IMG2.JPG",
            "id": "124",
            "raw": {"filename": "IMG2.JPG", "id": "124"},
        },
    ]
    remote = GoogleRemote(".config")
    data = remote.get_albums()
    assert data == [{"id": "barfoo", "name": "Album1", "photos": ["123", "124"]}]
    mock_api_obj.get_albums.assert_called()
    mock_api_obj.get_photos.assert_called_with(album_id="barfoo")
