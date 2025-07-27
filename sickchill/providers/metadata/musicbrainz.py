"""MusicBrainz metadata provider for SickChill."""

import logging
import os
from typing import Dict, List, Optional, Union
from xml.etree import ElementTree

import musicbrainzngs

from sickchill import logger, settings
from sickchill.oldbeard.databases import music
from sickchill.oldbeard.helpers import chmodAsParent

from .generic import GenericMetadata


class MusicBrainzMetadata(GenericMetadata):
    """
    Metadata provider for music using the MusicBrainz API.
    """

    def __init__(
        self,
        show_metadata=False,
        episode_metadata=False,
        fanart=False,
        poster=False,
        banner=False,
        episode_thumbnails=False,
        season_posters=False,
        season_banners=False,
        season_all_poster=False,
        season_all_banner=False,
    ):
        super().__init__(
            show_metadata,
            episode_metadata,
            fanart,
            poster,
            banner,
            episode_thumbnails,
            season_posters,
            season_banners,
            season_all_poster,
            season_all_banner,
        )
        self.name = "MusicBrainz"
        
        # Set up MusicBrainz API
        musicbrainzngs.set_useragent(
            "SickChill", 
            settings.BRANCH, 
            "https://sickchill.github.io/"
        )
        
        # Suppress warnings from the musicbrainzngs library
        logging.getLogger("musicbrainzngs").setLevel(logging.WARNING)
        
        # Define file names for artist and album metadata
        self._artist_metadata_filename = "artist.nfo"
        self._album_metadata_filename = "album.nfo"
        
        # Define image file names
        self.artist_poster_name = "artist-poster.jpg"
        self.album_cover_name = "cover.jpg"

    def get_artist_file_path(self, artist_obj):
        """
        Returns the path to the artist metadata file.
        
        artist_obj: An Artist object for which to create the metadata
        """
        return os.path.join(artist_obj.location, self._artist_metadata_filename)

    def get_album_file_path(self, album_obj):
        """
        Returns the path to the album metadata file.
        
        album_obj: An Album object for which to create the metadata
        """
        return os.path.join(album_obj.location, self._album_metadata_filename)

    def get_artist_poster_path(self, artist_obj):
        """
        Returns the path to the artist poster image.
        
        artist_obj: An Artist object for which to get the poster path
        """
        return os.path.join(artist_obj.location, self.artist_poster_name)

    def get_album_cover_path(self, album_obj):
        """
        Returns the path to the album cover image.
        
        album_obj: An Album object for which to get the cover path
        """
        return os.path.join(album_obj.location, self.album_cover_name)

    def _has_artist_metadata(self, artist_obj):
        """
        Check if artist metadata file exists.
        
        artist_obj: An Artist object to check
        """
        return self._check_exists(self.get_artist_file_path(artist_obj))

    def _has_album_metadata(self, album_obj):
        """
        Check if album metadata file exists.
        
        album_obj: An Album object to check
        """
        return self._check_exists(self.get_album_file_path(album_obj))

    def _has_artist_poster(self, artist_obj):
        """
        Check if artist poster exists.
        
        artist_obj: An Artist object to check
        """
        return self._check_exists(self.get_artist_poster_path(artist_obj))

    def _has_album_cover(self, album_obj):
        """
        Check if album cover exists.
        
        album_obj: An Album object to check
        """
        return self._check_exists(self.get_album_cover_path(album_obj))

    def _artist_data(self, artist_obj) -> Union[ElementTree.ElementTree, None]:
        """
        Generate XML data for an artist.
        
        artist_obj: An Artist object for which to create the metadata
        """
        if not artist_obj:
            return None

        try:
            # Create the XML structure for the artist
            artist_xml = ElementTree.Element("artist")
            
            ElementTree.SubElement(artist_xml, "name").text = artist_obj.name
            ElementTree.SubElement(artist_xml, "sortname").text = artist_obj.sort_name
            ElementTree.SubElement(artist_xml, "musicbrainzid").text = artist_obj.musicbrainz_id
            
            if artist_obj.country:
                ElementTree.SubElement(artist_xml, "country").text = artist_obj.country
            
            # Add genres
            genres_xml = ElementTree.SubElement(artist_xml, "genres")
            for genre in artist_obj.musicbrainz_genres:
                ElementTree.SubElement(genres_xml, "genre").text = genre.pk
            
            # Create the XML tree
            xml_data = ElementTree.ElementTree(artist_xml)
            
            return xml_data
        except Exception as e:
            logger.error(f"Error generating artist XML data: {e}")
            return None

    def _album_data(self, album_obj) -> Union[ElementTree.ElementTree, None]:
        """
        Generate XML data for an album.
        
        album_obj: An Album object for which to create the metadata
        """
        if not album_obj:
            return None

        try:
            # Create the XML structure for the album
            album_xml = ElementTree.Element("album")
            
            ElementTree.SubElement(album_xml, "title").text = album_obj.name
            ElementTree.SubElement(album_xml, "artist").text = album_obj.artist.name
            ElementTree.SubElement(album_xml, "year").text = str(album_obj.year)
            ElementTree.SubElement(album_xml, "musicbrainzid").text = album_obj.musicbrainz_id
            ElementTree.SubElement(album_xml, "type").text = album_obj.type
            ElementTree.SubElement(album_xml, "tracks").text = str(album_obj.tracks)
            
            if album_obj.date:
                ElementTree.SubElement(album_xml, "releasedate").text = str(album_obj.date)
            
            # Create the XML tree
            xml_data = ElementTree.ElementTree(album_xml)
            
            return xml_data
        except Exception as e:
            logger.error(f"Error generating album XML data: {e}")
            return None

    def create_artist_metadata(self, artist_obj):
        """
        Create metadata for an artist.
        
        artist_obj: An Artist object for which to create the metadata
        """
        if not artist_obj or self._has_artist_metadata(artist_obj):
            return False

        logger.debug(f"Creating artist metadata for {artist_obj.name}")
        return self.write_artist_file(artist_obj)

    def create_album_metadata(self, album_obj):
        """
        Create metadata for an album.
        
        album_obj: An Album object for which to create the metadata
        """
        if not album_obj or self._has_album_metadata(album_obj):
            return False

        logger.debug(f"Creating album metadata for {album_obj.name}")
        return self.write_album_file(album_obj)

    def create_artist_poster(self, artist_obj):
        """
        Create poster for an artist.
        
        artist_obj: An Artist object for which to create the poster
        """
        if not artist_obj or self._has_artist_poster(artist_obj):
            return False

        logger.debug(f"Creating artist poster for {artist_obj.name}")
        return self.save_artist_poster(artist_obj)

    def create_album_cover(self, album_obj):
        """
        Create cover for an album.
        
        album_obj: An Album object for which to create the cover
        """
        if not album_obj or self._has_album_cover(album_obj):
            return False

        logger.debug(f"Creating album cover for {album_obj.name}")
        return self.save_album_cover(album_obj)

    def write_artist_file(self, artist_obj):
        """
        Write artist metadata to file.
        
        artist_obj: An Artist object for which to write the metadata
        """
        data = self._artist_data(artist_obj)
        if not data:
            return False

        nfo_file_path = self.get_artist_file_path(artist_obj)
        nfo_file_dir = os.path.dirname(nfo_file_path)

        try:
            if not os.path.isdir(nfo_file_dir):
                logger.debug(f"Metadata dir didn't exist, creating it at {nfo_file_dir}")
                os.makedirs(nfo_file_dir)
                chmodAsParent(nfo_file_dir)

            logger.debug(f"Writing artist nfo file to {nfo_file_path}")

            nfo_file = open(nfo_file_path, "wb")
            data.write(nfo_file, encoding="UTF-8", xml_declaration=True)
            nfo_file.close()
            chmodAsParent(nfo_file_path)
        except IOError as error:
            logger.error(f"Unable to write file to {nfo_file_path} - are you sure the folder is writable? {error}")
            return False

        return True

    def write_album_file(self, album_obj):
        """
        Write album metadata to file.
        
        album_obj: An Album object for which to write the metadata
        """
        data = self._album_data(album_obj)
        if not data:
            return False

        nfo_file_path = self.get_album_file_path(album_obj)
        nfo_file_dir = os.path.dirname(nfo_file_path)

        try:
            if not os.path.isdir(nfo_file_dir):
                logger.debug(f"Metadata dir didn't exist, creating it at {nfo_file_dir}")
                os.makedirs(nfo_file_dir)
                chmodAsParent(nfo_file_dir)

            logger.debug(f"Writing album nfo file to {nfo_file_path}")

            nfo_file = open(nfo_file_path, "wb")
            data.write(nfo_file, encoding="UTF-8", xml_declaration=True)
            nfo_file.close()
            chmodAsParent(nfo_file_path)
        except IOError as error:
            logger.error(f"Unable to write file to {nfo_file_path} - are you sure the folder is writable? {error}")
            return False

        return True

    def save_artist_poster(self, artist_obj):
        """
        Save artist poster image.
        
        artist_obj: An Artist object for which to save the poster
        """
        # TODO: Implement fetching artist image from MusicBrainz/Cover Art Archive
        return False

    def save_album_cover(self, album_obj):
        """
        Save album cover image.
        
        album_obj: An Album object for which to save the cover
        """
        # TODO: Implement fetching album cover from MusicBrainz/Cover Art Archive
        return False

    def find_artist(self, name: str) -> Optional[Dict[str, str]]:
        """
        Find an artist by name and return their ID and name.
        
        Args:
            name: Name of the artist to search for.
            
        Returns:
            Optional[Dict[str, str]]: Dictionary with artist ID and name if found, None otherwise.
        """
        logger.info(f"Searching for artist: {name}")
        try:
            result = musicbrainzngs.search_artists(name, limit=10)
            artists = result.get("artist-list", [])
            
            if not artists:
                logger.warning(f"No artists found for query: {name}")
                return None
                
            # Find the best match
            for artist in artists:
                artist_name = artist.get("name", "")
                artist_id = artist.get("id", "")
                score = int(artist.get("ext:score", "0"))
                
                logger.debug(f"Found artist: {artist_name} (ID: {artist_id}, Score: {score})")
                
                # Consider it a match if the score is high enough
                if score > 90:
                    logger.info(f"Selected artist: {artist_name} (ID: {artist_id})")
                    return {"id": artist_id, "name": artist_name}
            
            # If no high-score match, return the first result
            artist = artists[0]
            artist_name = artist.get("name", "")
            artist_id = artist.get("id", "")
            logger.info(f"Selected artist (best match): {artist_name} (ID: {artist_id})")
            return {"id": artist_id, "name": artist_name}
            
        except musicbrainzngs.WebServiceError as e:
            logger.error(f"MusicBrainz API error while searching for artist: {e}")
            return None
        except Exception as e:
            logger.error(f"Error while searching for artist: {e}")
            return None

    def get_albums(self, artist_id: str, artist_name: str, max_albums: int = 50) -> List[Dict]:
        """
        Get albums for an artist.
        
        Args:
            artist_id: MusicBrainz ID of the artist.
            artist_name: Name of the artist (for reference).
            max_albums: Maximum number of albums to retrieve.
            
        Returns:
            List[Dict]: List of albums by the artist.
        """
        logger.info(f"Retrieving albums for artist: {artist_name} (ID: {artist_id})")
        albums = []
        offset = 0
        limit = 25
        total_albums = 0
        album_count = 0
        
        try:
            # Get the artist's release groups (albums)
            while True and album_count < max_albums:
                try:
                    result = musicbrainzngs.browse_release_groups(
                        artist=artist_id,
                        release_type=["album", "ep"],
                        limit=limit,
                        offset=offset,
                    )
                    release_groups = result.get("release-group-list", [])
                    total_albums = int(result.get("release-group-count", "0"))
                    
                    if not release_groups:
                        break
                except Exception as e:
                    logger.error(f"Error retrieving release groups: {e}")
                    break
                
                for release_group in release_groups:
                    album_id = release_group.get("id", "")
                    album_title = release_group.get("title", "")
                    album_type = release_group.get("type", "Album")
                    
                    # Get the first date if available
                    first_release_date = release_group.get("first-release-date", "")
                    year = None
                    if first_release_date and len(first_release_date) >= 4:
                        try:
                            year = int(first_release_date[:4])
                        except ValueError:
                            pass
                    
                    # Get track count if available
                    tracks = 0
                    
                    album = {
                        "id": album_id,
                        "title": album_title,
                        "artist": artist_name,
                        "artist_id": artist_id,
                        "year": year,
                        "tracks": tracks,
                        "type": album_type,
                    }
                    albums.append(album)
                    album_count += 1
                    logger.debug(f"Added album: {album_title} ({year})")
                    
                    if album_count >= max_albums:
                        logger.info(f"Reached maximum album limit ({max_albums})")
                        break
                
                offset += limit
                if offset >= total_albums or album_count >= max_albums:
                    break
            
            logger.info(f"Retrieved {len(albums)} albums for artist: {artist_name}")
            return albums
            
        except musicbrainzngs.WebServiceError as e:
            logger.error(f"MusicBrainz API error while retrieving albums: {e}")
            return albums
        except Exception as e:
            logger.error(f"Error while retrieving albums: {e}")
            return albums