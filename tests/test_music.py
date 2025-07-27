"""
Test music module
"""

import unittest
from unittest import mock

import musicbrainzngs

from sickchill import settings
from sickchill.music import MusicList
from sickchill.oldbeard.databases import music
from tests import conftest


class MusicListTests(conftest.SickChillTestDBCase):
    """
    Test music list
    """

    def setUp(self):
        """
        Set up tests
        """
        super().setUp()
        settings.MUSIC_DOWNLOAD_DIR = conftest.TEST_DIR
        settings.MUSIC_AUTO_SEARCH = False
        self.music_list = MusicList()

    def tearDown(self):
        """
        Tear down tests
        """
        super().tearDown()

    @mock.patch('musicbrainzngs.search_artists')
    def test_search_musicbrainz(self, mock_search_artists):
        """
        Test searching for artists on MusicBrainz
        """
        # Mock the MusicBrainz API response
        mock_search_artists.return_value = {
            "artist-list": [
                {
                    "id": "test-artist-id",
                    "name": "Test Artist",
                    "sort-name": "Artist, Test",
                    "country": "US"
                }
            ]
        }

        # Test searching by query
        results = self.music_list.search_musicbrainz(query="Test Artist")
        assert len(results) == 1
        assert results[0]["id"] == "test-artist-id"
        assert results[0]["name"] == "Test Artist"
        mock_search_artists.assert_called_once_with("Test Artist", limit=10)

    @mock.patch('musicbrainzngs.get_artist_by_id')
    def test_search_musicbrainz_by_id(self, mock_get_artist_by_id):
        """
        Test searching for artists on MusicBrainz by ID
        """
        # Mock the MusicBrainz API response
        mock_get_artist_by_id.return_value = {
            "artist": {
                "id": "test-artist-id",
                "name": "Test Artist",
                "sort-name": "Artist, Test",
                "country": "US"
            }
        }

        # Test searching by ID
        results = self.music_list.search_musicbrainz(artist_id="test-artist-id")
        assert len(results) == 1
        assert results[0]["id"] == "test-artist-id"
        assert results[0]["name"] == "Test Artist"
        mock_get_artist_by_id.assert_called_once_with("test-artist-id")

    @mock.patch('musicbrainzngs.get_artist_by_id')
    def test_add_from_musicbrainz(self, mock_get_artist_by_id):
        """
        Test adding an artist from MusicBrainz
        """
        # Mock the MusicBrainz API response
        mock_get_artist_by_id.return_value = {
            "artist": {
                "id": "test-artist-id",
                "name": "Test Artist",
                "sort-name": "Artist, Test",
                "country": "US",
                "tag-list": [
                    {"name": "rock", "count": "10"},
                    {"name": "pop", "count": "5"}
                ]
            }
        }

        # Mock the get_albums_for_artist method
        with mock.patch.object(self.music_list, 'get_albums_for_artist') as mock_get_albums:
            mock_get_albums.return_value = []
            
            # Add artist from MusicBrainz
            artist = self.music_list.add_from_musicbrainz("test-artist-id")
            
            # Verify artist was added correctly
            assert artist is not None
            assert artist.name == "Test Artist"
            assert artist.sort_name == "Artist, Test"
            assert artist.country == "US"
            
            # Verify indexer data was added
            assert len(artist.indexer_data) == 1
            indexer_data = artist.indexer_data[0]
            assert indexer_data.site == "musicbrainz"
            assert indexer_data.pk == "test-artist-id"
            
            # Verify genres were added
            assert len(indexer_data.genres) == 2
            genre_names = [genre.pk for genre in indexer_data.genres]
            assert "rock" in genre_names
            assert "pop" in genre_names
            
            # Verify get_albums_for_artist was called
            mock_get_albums.assert_called_once_with(artist)

    @mock.patch('musicbrainzngs.browse_release_groups')
    @mock.patch('musicbrainzngs.get_release_group_by_id')
    @mock.patch('musicbrainzngs.get_release_by_id')
    def test_get_albums_for_artist(self, mock_get_release, mock_get_release_group, mock_browse_release_groups):
        """
        Test getting albums for an artist
        """
        # Create a test artist
        artist = music.Artist(name="Test Artist", sort_name="Artist, Test", country="US")
        indexer_data = music.IndexerData(site="musicbrainz", pk="test-artist-id")
        artist.indexer_data.append(indexer_data)
        self.music_list.commit(artist)
        
        # Mock the MusicBrainz API responses
        mock_browse_release_groups.return_value = {
            "release-group-list": [
                {
                    "id": "test-album-id",
                    "title": "Test Album",
                    "type": "Album",
                    "first-release-date": "2020-01-01"
                }
            ]
        }
        
        mock_get_release_group.return_value = {
            "release-group": {
                "id": "test-album-id",
                "title": "Test Album",
                "type": "Album",
                "first-release-date": "2020-01-01",
                "release-list": [
                    {
                        "id": "test-release-id",
                        "title": "Test Album"
                    }
                ],
                "tag-list": [
                    {"name": "rock", "count": "10"},
                    {"name": "pop", "count": "5"}
                ]
            }
        }
        
        mock_get_release.return_value = {
            "release": {
                "id": "test-release-id",
                "title": "Test Album",
                "medium-list": [
                    {
                        "track-count": 10
                    }
                ]
            }
        }
        
        # Get albums for artist
        albums = self.music_list.get_albums_for_artist(artist)
        
        # Verify album was added correctly
        assert len(albums) == 1
        album = albums[0]
        assert album.name == "Test Album"
        assert album.year == 2020
        assert album.tracks == 10
        assert album.album_type == "Album"
        
        # Verify indexer data was added
        assert len(album.indexer_data) == 1
        indexer_data = album.indexer_data[0]
        assert indexer_data.site == "musicbrainz"
        assert indexer_data.pk == "test-album-id"
        
        # Verify genres were added
        assert len(indexer_data.genres) == 2
        genre_names = [genre.pk for genre in indexer_data.genres]
        assert "rock" in genre_names
        assert "pop" in genre_names

    @mock.patch('sickchill.music.MusicList.search_providers')
    def test_search_thread(self, mock_search_providers):
        """
        Test the search thread functionality
        """
        # Create a test artist with albums
        artist = music.Artist(name="Test Artist", sort_name="Artist, Test", country="US")
        indexer_data = music.IndexerData(site="musicbrainz", pk="test-artist-id")
        artist.indexer_data.append(indexer_data)
        self.music_list.commit(artist)
        
        # Mock get_albums_for_artist to return a new album
        with mock.patch.object(self.music_list, 'get_albums_for_artist') as mock_get_albums:
            album = music.Album(
                name="New Album",
                year=2025,
                artist_pk=artist.pk,
                tracks=10,
                album_type="Album"
            )
            album_indexer = music.IndexerData(site="musicbrainz", pk="new-album-id")
            album.indexer_data.append(album_indexer)
            mock_get_albums.return_value = [album]
            
            # Enable auto search
            settings.MUSIC_AUTO_SEARCH = True
            
            # Run search thread
            self.music_list.search_thread()
            
            # Verify search_providers was called for the new album
            mock_search_providers.assert_called_once_with(album)

    @mock.patch('sickchill.oldbeard.clients.getClientInstance')
    def test_snatch_album(self, mock_get_client):
        """
        Test snatching an album
        """
        # Create a test artist with an album
        artist = music.Artist(name="Test Artist", sort_name="Artist, Test", country="US")
        self.music_list.commit(artist)
        
        album = music.Album(
            name="Test Album",
            year=2020,
            artist_pk=artist.pk,
            tracks=10,
            album_type="Album"
        )
        self.music_list.commit(album)
        
        # Create a mock result
        mock_result = mock.MagicMock()
        mock_result.album = album
        mock_result.result.url = "http://example.com/test.torrent"
        mock_result.result.name = "Test Album 2020"
        mock_result.result.size = 100000
        mock_result.provider.name = "Test Provider"
        
        # Mock the download client
        mock_client = mock.MagicMock()
        mock_client.sendTORRENT.return_value = True
        mock_get_client.return_value.return_value = mock_client
        
        # Snatch the album
        result = self.music_list.snatch_album(mock_result)
        
        # Verify the result
        assert result is True
        
        # Verify the album status was updated
        album = self.music_list.album_query.get(album.pk)
        assert album.status == music.AlbumStatus.SNATCHED
        assert album.provider == "Test Provider"
        assert album.size == 100000
        
        # Verify a history entry was created
        history = self.music_list.session.query(music.MusicHistory).filter_by(album_pk=album.pk).first()
        assert history is not None
        assert history.provider == "Test Provider"


if __name__ == "__main__":
    print("==================")
    print("STARTING - MUSIC TESTS")
    print("==================")
    print("######################################################################")
    SUITE = unittest.TestLoader().loadTestsFromTestCase(MusicListTests)
    unittest.TextTestRunner(verbosity=2).run(SUITE)