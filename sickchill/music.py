import datetime
import json
import logging
import os
import threading
import traceback

import musicbrainzngs
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from . import settings
from .oldbeard import clients, generic_queue
from .oldbeard.databases import music
from .oldbeard.db import db_cons, db_full_path, db_locks
from .providers.metadata.musicbrainz import MusicBrainzMetadata

logger = logging.getLogger("sickchill.music")

class MusicQueue(generic_queue.GenericQueue):
    """
    Queue for background music operations
    """
    def __init__(self):
        super().__init__()
        self.queue_name = "MUSICQUEUE"

    def is_in_add_queue(self, artist_id):
        """
        Check if an artist is already in the add queue
        """
        for cur_item in self.queue + [self.currentItem]:
            if isinstance(cur_item, MusicQueueItemAdd) and cur_item.artist_id == artist_id:
                return True
        return False

class MusicQueueItemAdd(generic_queue.QueueItem):
    """
    Queue item for adding an artist
    """
    def __init__(self, artist_id, root_dir=None):
        super().__init__("Add Artist", 1)  # 1 = ADD action
        self.artist_id = artist_id
        self.root_dir = root_dir
        self.priority = generic_queue.QueuePriorities.HIGH
        self.name = f"ADD-{artist_id}"
        self.success = None
        self.added_artist = None

    def run(self):
        """
        Run the add artist task
        """
        try:
            logger.info(f"Starting to add artist {self.artist_id}")
            
            # Check if we have a root directory set
            root_dir = self.root_dir
            if not root_dir and settings.MUSIC_ROOT_DIRS:
                # Use the first root directory if available
                root_dirs = settings.MUSIC_ROOT_DIRS.split('|')
                if len(root_dirs) > 1 and root_dirs[1]:
                    root_dir = root_dirs[1]
            
            # If we still don't have a root directory, use MUSIC_DOWNLOAD_DIR
            if not root_dir and settings.MUSIC_DOWNLOAD_DIR:
                root_dir = settings.MUSIC_DOWNLOAD_DIR
                
            if not root_dir:
                logger.warning("No music root directory or download directory set. Artist will be added without a location.")
                
            self.added_artist = settings.music_list._add_artist_from_musicbrainz(self.artist_id, root_dir)
            if self.added_artist:
                self.success = True
                logger.info(f"Successfully added artist {self.added_artist.name}")
                # Check if the artist has albums
                album_count = len(self.added_artist.albums)
                logger.info(f"Artist {self.added_artist.name} has {album_count} albums in database")
            else:
                self.success = False
                logger.error(f"Failed to add artist {self.artist_id}")
        except Exception as e:
            self.success = False
            logger.error(f"Error adding artist {self.artist_id}: {e}")
            logger.error(f"Exception traceback: {traceback.format_exc()}")


class MusicList:
    def __init__(self):
        # Set up MusicBrainz API
        musicbrainzngs.set_useragent(
            settings.MUSICBRAINZ_USER_AGENT,
            settings.BRANCH,
            settings.MUSICBRAINZ_CONTACT,
        )

        # Suppress lower level logs from the musicbrainzngs library
        logging.getLogger("musicbrainzngs").setLevel(logging.WARNING)

        self.filename = "music.db"
        self.full_path = db_full_path(self.filename)

        if self.filename not in db_cons or not db_cons[self.filename]:
            music.Session.configure(
                bind=create_engine(
                    f"sqlite:///{self.full_path}",
                    connect_args={"check_same_thread": False},
                    json_serializer=lambda obj: json.dumps(obj, ensure_ascii=False),
                )
            )
            self.session: Session = music.Session()
            music.Base.metadata.create_all(self.session.bind, checkfirst=True)

            db_locks[self.filename] = threading.Lock()
            db_cons[self.filename] = self.session
        else:
            self.session: Session = db_cons[self.filename]

    def __iter__(self):
        for item in self.artist_query.all():
            yield item

    def __getitem__(self, pk):
        return self.artist_query.get(pk)

    def __contains__(self, pk):
        try:
            self.__getitem__(pk)
            return True
        except KeyError:
            return False

    def search_musicbrainz(self, query=None, artist_id=None):
        """
        Search for artists on MusicBrainz.

        Args:
            query: Artist name to search for
            artist_id: MusicBrainz artist ID

        Returns:
            List of artist results
        """
        if artist_id:
            try:
                result = musicbrainzngs.get_artist_by_id(artist_id)
                return [result["artist"]]
            except musicbrainzngs.WebServiceError as e:
                logger.error(f"MusicBrainz API error while getting artist by ID: {e}")
                return []
        elif query:
            try:
                result = musicbrainzngs.search_artists(query, limit=10)
                return result.get("artist-list", [])
            except musicbrainzngs.WebServiceError as e:
                logger.error(f"MusicBrainz API error while searching for artist: {e}")
                return []
        else:
            raise Exception("Query or artist ID is required!")

    def add_from_musicbrainz(self, artist_id: str, root_dir=None):
        """
        Add an artist from MusicBrainz by adding it to the queue.

        Args:
            artist_id: MusicBrainz artist ID
            root_dir: Root directory for the artist (optional)

        Returns:
            True if the artist was added to the queue, False otherwise
        """
        if not artist_id:
            logger.error("No artist ID provided")
            return False

        # Check if the artist already exists
        existing_artist = self._check_existing_indexer_data(artist_id, "artist")
        if existing_artist:
            # If the artist exists but doesn't have a location and we have a root_dir,
            # update the artist's location
            if not existing_artist.location and root_dir:
                existing_artist.location = os.path.join(root_dir, existing_artist.name)
                logger.info(f"Setting location for existing artist {existing_artist.name} to {existing_artist.location}")
                
                # Create the directory if it doesn't exist
                if not os.path.isdir(existing_artist.location):
                    try:
                        os.makedirs(existing_artist.location)
                    except OSError as e:
                        logger.error(f"Failed to create artist directory: {e}")
                
                # Update album locations
                for album in existing_artist.albums:
                    if not album.location:
                        album.location = os.path.join(existing_artist.location, album.name)
                        logger.info(f"Setting location for album {album.name} to {album.location}")
                
                # Commit changes
                self.commit()
            
            return existing_artist

        # Check if the artist is already in the queue
        if settings.musicQueueScheduler.action.is_in_add_queue(artist_id):
            logger.debug(f"Artist {artist_id} is already in the queue")
            return True

        # Add the artist to the queue
        queue_item = MusicQueueItemAdd(artist_id, root_dir)
        settings.musicQueueScheduler.action.add_item(queue_item)

        logger.debug(f"Added artist {artist_id} to the queue")
        return True

    def _add_artist_from_musicbrainz(self, artist_id: str, root_dir=None):
        """
        Internal method to add an artist from MusicBrainz.
        This is called by the queue item.

        Args:
            artist_id: MusicBrainz artist ID
            root_dir: Root directory for the artist (optional)

        Returns:
            Artist object
        """
        logger.debug(f"Adding artist from MusicBrainz with id: {artist_id}")

        try:
            # Check if the indexer data already exists
            existing_artist = self._check_existing_indexer_data(artist_id, "artist")
            if existing_artist:
                logger.info(f"Artist {existing_artist.name} already exists, retrieving albums")
                
                # Set artist location if it's not set and root_dir is provided
                if not existing_artist.location and root_dir:
                    existing_artist.location = os.path.join(root_dir, existing_artist.name)
                    logger.info(f"Setting location for existing artist {existing_artist.name} to {existing_artist.location}")
                    
                    # Create the directory if it doesn't exist
                    if not os.path.isdir(existing_artist.location):
                        try:
                            os.makedirs(existing_artist.location)
                        except OSError as e:
                            logger.error(f"Failed to create artist directory: {e}")
                
                # Get albums for this artist even if it already exists
                albums = self.get_albums_for_artist(existing_artist)
                
                # Set album locations if they're not set
                if existing_artist.location:
                    for album in albums:
                        if not album.location:
                            album.location = os.path.join(existing_artist.location, album.name)
                            logger.info(f"Setting location for album {album.name} to {album.location}")
                            
                            # Create the directory if it doesn't exist
                            if not os.path.isdir(album.location):
                                try:
                                    os.makedirs(album.location)
                                except OSError as e:
                                    logger.error(f"Failed to create album directory: {e}")

                # Try to fetch artist image if it doesn't exist
                if not existing_artist.poster:
                    metadata_provider = MusicBrainzMetadata()
                    metadata_provider.save_artist_poster(existing_artist)

                # Commit changes to the database
                self.commit()
                
                return existing_artist

            # Get artist info from MusicBrainz
            mb_artist = musicbrainzngs.get_artist_by_id(artist_id, includes=["aliases", "tags"])["artist"]

            # Create artist instance
            name = mb_artist.get("name", "")
            sort_name = mb_artist.get("sort-name", name)
            country = mb_artist.get("country", "")

            instance = music.Artist(name=name, sort_name=sort_name, country=country)
            
            # Set artist location if root_dir is provided
            if root_dir:
                instance.location = os.path.join(root_dir, name)
                logger.info(f"Setting location for new artist {name} to {instance.location}")
                
                # Create the directory if it doesn't exist
                if not os.path.isdir(instance.location):
                    try:
                        os.makedirs(instance.location)
                    except OSError as e:
                        logger.error(f"Failed to create artist directory: {e}")

            # Create indexer data
            mb_data = music.IndexerData(site="musicbrainz", data=mb_artist, pk=artist_id)

            # Add the indexer_data to the session first
            self.session.add(mb_data)
            self.session.flush()

            # Add genres from tags
            if "tag-list" in mb_artist:
                with self.session.no_autoflush:
                    for tag in mb_artist["tag-list"]:
                        if "name" in tag and int(tag.get("count", 0)) > 0:
                            genre_name = tag["name"]
                            logger.debug(f"Adding genre {genre_name}")
                            genre = self.get_genre(genre_name)
                            if not genre:
                                genre = music.Genres(pk=genre_name)
                                self.session.add(genre)
                            else:
                                # Merge the genre into the current session
                                genre = self.session.merge(genre)
                            mb_data.genres.append(genre)

            instance.indexer_data.append(mb_data)

            # Add the artist to the session
            self.session.add(instance)

            # Commit the artist first to ensure it has a valid pk
            self.commit()

            # Get albums for this artist
            albums = self.get_albums_for_artist(instance)
            logger.info(f"Added artist {instance.name} with {len(albums)} albums")

            # Try to fetch artist image
            metadata_provider = MusicBrainzMetadata()
            metadata_provider.save_artist_poster(instance)

            return instance

        except musicbrainzngs.WebServiceError as e:
            logger.error(f"MusicBrainz API error while adding artist: {e}")
            self.session.rollback()
            return None
        except Exception as e:
            logger.error(f"Error while adding artist: {e}")
            self.session.rollback()
            return None

    def get_genre(self, name):
        """
        Get a genre by name.

        Args:
            name: Genre name

        Returns:
            Genre object or None if not found
        """
        with self.session.no_autoflush:
            return self.session.query(music.Genres).filter_by(pk=name).first()

    def get_albums_for_artist(self, artist_obj):
        """
        Get albums for an artist and add them to the database.

        Args:
            artist_obj: Artist object

        Returns:
            List of Album objects
        """
        artist_id = artist_obj.musicbrainz_id
        if not artist_id:
            logger.error(f"No MusicBrainz ID for artist {artist_obj.name}")
            return []

        albums = []
        offset = 0
        limit = 25
        chunk_size = 10  # Process albums in chunks of 10
        current_chunk = []

        # Initialize metadata provider for album covers
        metadata_provider = MusicBrainzMetadata()

        try:
            while True:
                logger.debug(f"Retrieving albums for {artist_obj.name} (offset: {offset}, limit: {limit})")
                result = musicbrainzngs.browse_release_groups(
                    artist=artist_id,
                    release_type=["album", "ep", "single"],
                    limit=limit,
                    offset=offset
                )

                release_groups = result.get("release-group-list", [])
                if not release_groups:
                    break

                logger.debug(f"Retrieved {len(release_groups)} release groups")

                for release_group in release_groups:
                    album_id = release_group.get("id", "")
                    album_title = release_group.get("title", "")
                    album_type = release_group.get("type", "Album")

                    # Get the first date if available
                    first_release_date = release_group.get("first-release-date", "")
                    year = None
                    date = None

                    if first_release_date:
                        try:
                            if len(first_release_date) >= 4:
                                year = int(first_release_date[:4])
                            if len(first_release_date) >= 10:
                                date = datetime.datetime.strptime(first_release_date[:10], "%Y-%m-%d").date()
                        except ValueError:
                            pass

                    # Check if album already exists
                    existing_album = self._check_existing_indexer_data(album_id, "album")
                    if existing_album:
                        albums.append(existing_album)

                        # Try to fetch album cover if it doesn't exist
                        if not existing_album.poster:
                            metadata_provider.save_album_cover(existing_album)

                        # Check if track information is available
                        mb_data = existing_album.musicbrainz_data
                        if not mb_data or "tracks" not in mb_data:
                            try:
                                logger.debug(f"Fetching track information for existing album {existing_album.name}")
                                self._update_album_tracks(existing_album, album_id)
                            except Exception as e:
                                logger.error(f"Error updating track information for album {existing_album.name}: {e}")

                        continue

                    # Get more detailed info about the release group
                    try:
                        logger.debug(f"Getting details for album {album_title} ({album_id})")
                        release_group_info = musicbrainzngs.get_release_group_by_id(
                            album_id,
                            includes=["releases", "tags"]
                        )["release-group"]

                        # Get track information
                        tracks, track_list = self._get_album_tracks(release_group_info)

                        # Add track list to release group info
                        release_group_info["tracks"] = track_list
                    except Exception as e:
                        logger.error(f"Error getting detailed album info: {e}")
                        release_group_info = {}

                    # Create album instance
                    album = music.Album(
                        name=album_title,
                        year=year or 0,
                        artist_pk=artist_obj.pk,
                        tracks=tracks,
                        album_type=album_type
                    )

                    if date:
                        album.date = date

                    # Create indexer data
                    mb_data = music.IndexerData(site="musicbrainz", data=release_group_info, pk=album_id)

                    # Add the indexer_data to the session first
                    self.session.add(mb_data)
                    self.session.flush()

                    # Add genres from tags
                    if "tag-list" in release_group_info:
                        with self.session.no_autoflush:
                            for tag in release_group_info["tag-list"]:
                                if "name" in tag and int(tag.get("count", 0)) > 0:
                                    genre_name = tag["name"]
                                    logger.debug(f"Adding genre {genre_name}")
                                    genre = self.get_genre(genre_name)
                                    if not genre:
                                        genre = music.Genres(pk=genre_name)
                                        self.session.add(genre)
                                    else:
                                        # Merge the genre into the current session
                                        genre = self.session.merge(genre)
                                    mb_data.genres.append(genre)

                    album.indexer_data.append(mb_data)
                    
                    # Set album location if artist has a location
                    if artist_obj.location and not album.location:
                        album.location = os.path.join(artist_obj.location, album.name)
                        logger.info(f"Setting location for album {album.name} to {album.location}")
                        
                        # Create the directory if it doesn't exist
                        if not os.path.isdir(album.location):
                            try:
                                os.makedirs(album.location)
                            except OSError as e:
                                logger.error(f"Failed to create album directory: {e}")
                    
                    albums.append(album)
                    current_chunk.append(album)

                    # Add album to session
                    self.session.add(album)

                    # Commit albums in chunks
                    if len(current_chunk) >= chunk_size:
                        logger.debug(f"Committing chunk of {len(current_chunk)} albums")
                        self.commit()
                        logger.info(f"Added chunk of {len(current_chunk)} albums for artist {artist_obj.name}")

                        # Try to fetch album covers for the committed albums
                        for album_obj in current_chunk:
                            metadata_provider.save_album_cover(album_obj)

                        current_chunk = []

                offset += limit
                if len(release_groups) < limit:
                    break

            # Commit any remaining albums
            if current_chunk:
                logger.debug(f"Committing final chunk of {len(current_chunk)} albums")
                self.commit()
                logger.info(f"Added final chunk of {len(current_chunk)} albums for artist {artist_obj.name}")

                # Try to fetch album covers for the remaining albums
                for album_obj in current_chunk:
                    metadata_provider.save_album_cover(album_obj)

            logger.info(f"Total: Added {len(albums)} albums for artist {artist_obj.name}")
            return albums

        except musicbrainzngs.WebServiceError as e:
            logger.error(f"MusicBrainz API error while getting albums: {e}")
            # Try to commit any albums we've processed so far
            if current_chunk:
                try:
                    self.commit()
                    logger.info(f"Saved {len(current_chunk)} albums before error")
                except Exception:
                    logger.error("Failed to save albums after API error")
            return albums
        except Exception as e:
            logger.error(f"Error while getting albums: {e}")
            logger.error(f"Exception traceback: {traceback.format_exc()}")
            # Try to commit any albums we've processed so far
            if current_chunk:
                try:
                    self.commit()
                    logger.info(f"Saved {len(current_chunk)} albums before error")
                except Exception:
                    logger.error("Failed to save albums after error")
            return albums

    def _get_album_tracks(self, release_group_info):
        """
        Extract track information from a release group.

        Args:
            release_group_info: Release group information from MusicBrainz

        Returns:
            Tuple of (track_count, track_list)
        """
        tracks = 0
        track_list = []

        if "release-list" in release_group_info and release_group_info["release-list"]:
            first_release = release_group_info["release-list"][0]
            release_id = first_release.get("id")

            if release_id:
                try:
                    release_info = musicbrainzngs.get_release_by_id(
                        release_id,
                        includes=["recordings", "media"]
                    )["release"]

                    if "medium-list" in release_info:
                        for medium in release_info["medium-list"]:
                            medium_tracks = int(medium.get("track-count", 0))
                            tracks += medium_tracks

                            # Extract track information
                            if "track-list" in medium:
                                for track in medium["track-list"]:
                                    track_info = {
                                        "position": track.get("position", ""),
                                        "title": track.get("title", ""),
                                        "duration": track.get("length", ""),
                                    }

                                    # Format duration from milliseconds to MM:SS
                                    if track_info["duration"]:
                                        try:
                                            ms = int(track_info["duration"])
                                            seconds = ms // 1000
                                            minutes = seconds // 60
                                            seconds = seconds % 60
                                            track_info["duration"] = f"{minutes}:{seconds:02d}"
                                        except (ValueError, TypeError):
                                            pass

                                    track_list.append(track_info)
                except Exception as e:
                    logger.error(f"Error getting release information: {e}")

        return tracks, track_list

    def _update_album_tracks(self, album_obj, album_id):
        """
        Update an album with track information.

        Args:
            album_obj: Album object to update
            album_id: MusicBrainz ID of the album

        Returns:
            True if successful, False otherwise
        """
        try:
            # Get more detailed info about the release group
            release_group_info = musicbrainzngs.get_release_group_by_id(
                album_id,
                includes=["releases", "tags"]
            )["release-group"]

            # Get track information
            _, track_list = self._get_album_tracks(release_group_info)

            # Update the album's MusicBrainz data with track information
            for indexer_data in album_obj.indexer_data:
                if indexer_data.site == "musicbrainz":
                    data = indexer_data.data
                    data["tracks"] = track_list
                    indexer_data.data = data
                    self.session.add(indexer_data)
                    self.session.flush()
                    logger.debug(f"Updated track information for album {album_obj.name}")
                    return True

            return False
        except Exception as e:
            logger.error(f"Error updating track information: {e}")
            return False

    def _check_existing_indexer_data(self, pk, data_type="artist"):
        """
        Check if an IndexerData record exists and handle orphaned records.

        Args:
            pk: Primary key (ID) to check for
            data_type: Type of data ("artist" or "album")

        Returns:
            The associated artist/album object if it exists, None otherwise
        """
        existing = self.session.query(music.IndexerData).filter_by(pk=pk).first()
        if not existing:
            return None

        # Check if this is an orphaned record
        if data_type == "artist" and existing.artist:
            logger.debug(f"Artist already existed as {existing.artist.name}")
            return existing.artist
        elif data_type == "album" and existing.album:
            logger.debug(f"Album already existed as {existing.album.name}")
            return existing.album
        else:
            # This is an orphaned record, clean it up
            logger.debug(f"Found orphaned IndexerData record for {data_type} {pk}, removing it")

            try:
                # First, delete any associated genres to avoid NOT NULL constraint violations
                if existing.genres:
                    for genre in existing.genres:
                        self.session.delete(genre)
                    self.session.flush()

                # Now delete the indexer data record
                self.session.delete(existing)
                self.session.commit()
            except Exception as e:
                logger.error(f"Error cleaning up orphaned record: {e}")
                self.session.rollback()

            return None

    def commit(self, instance=None):
        logger.debug("Committing")
        try:
            if instance:
                self.session.add(instance)
            self.session.flush()
            self.session.commit()
        except Exception as e:
            logger.error(f"Error committing to database: {e}")
            self.session.rollback()
            raise

    def delete_artist(self, pk):
        instance = self.artist_query.get(pk)
        if instance:
            # Delete all albums for this artist
            for album in instance.albums:
                self.delete_album(album.pk)

            # Delete the artist
            self.session.delete(instance)
            self.commit()

    def delete_album(self, pk):
        instance = self.album_query.get(pk)
        if instance:
            self.session.delete(instance)
            self.commit()

    @property
    def artist_query(self):
        return self.session.query(music.Artist)

    @property
    def album_query(self):
        return self.session.query(music.Album)

    def artist_by_slug(self, slug):
        return self.artist_query.filter_by(slug=slug).first()

    def album_by_slug(self, slug):
        return self.album_query.filter_by(slug=slug).first()

    def search_providers(self, album_obj: music.Album):
        """
        Search providers for an album.

        Args:
            album_obj: Album object to search for

        Returns:
            List of search results
        """
        strings = album_obj.search_strings()
        for provider in settings.providerList:
            if provider.can_backlog and provider.backlog_enabled and provider.supports_movies:  # Reuse movie support for now
                results = provider.search(strings)
                for result in results:
                    music_result = music.MusicResult(result=result, album=album_obj, provider=provider)
                    self.session.add(music_result)

                self.commit(album_obj)
                # TODO: Check if we need to break out here and stop hitting providers if we found a good result

    def snatch_album(self, result: music.MusicResult):
        """
        Snatch an album result.

        Args:
            result: MusicResult object to snatch

        Returns:
            bool: True if successful, False otherwise
        """
        if not result or not result.album:
            logger.error("Invalid result or album")
            return False

        album = result.album
        artist = self.artist_query.get(album.artist_pk)

        if not artist:
            logger.error(f"Could not find artist for album {album.name}")
            return False

        logger.info(f"Snatching {album.name} by {artist.name} from {result.provider.name}")

        try:
            # Extract necessary information from the result
            download_url = result.url
            download_name = result.name
            download_size = result.size
            download_provider = result.provider

            # Check if MUSIC_DOWNLOAD_DIR is set
            if not settings.MUSIC_DOWNLOAD_DIR:
                logger.error("No music download directory set. Please set MUSIC_DOWNLOAD_DIR in Settings -> General.")
                return False
                
            # Check if artist has a location set
            if not artist.location:
                # If artist doesn't have a location, use MUSIC_DOWNLOAD_DIR/artist.name
                artist.location = os.path.join(settings.MUSIC_DOWNLOAD_DIR, artist.name)
                logger.info(f"Setting artist location to {artist.location}")
                
                # Create the directory if it doesn't exist
                if not os.path.isdir(artist.location):
                    try:
                        os.makedirs(artist.location)
                    except OSError as e:
                        logger.error(f"Failed to create artist directory: {e}")
                        return False
            
            # Check if album has a location set
            if not album.location:
                # If album doesn't have a location, use artist.location/album.name
                album.location = os.path.join(artist.location, album.name)
                logger.info(f"Setting album location to {album.location}")
            
            # Use album location as download directory
            download_dir = album.location
            
            # Ensure download directory exists
            if not os.path.isdir(download_dir):
                try:
                    os.makedirs(download_dir)
                except OSError as e:
                    logger.error(f"Failed to create album directory: {e}")
                    return False

            # Get the appropriate download client
            download_client = clients.getClientInstance(settings.TORRENT_METHOD)()

            if not download_client:
                logger.error(f"Could not get download client {settings.TORRENT_METHOD}")
                return False

            # Send the download to the client
            download_result = download_client.sendTORRENT(
                download_url,
                download_name,
                download_dir
            )

            if not download_result:
                logger.error(f"Failed to send download to client: {download_name}")
                return False

            # Update album status
            album.status = music.AlbumStatus.SNATCHED
            album.provider = download_provider
            album.size = download_size

            # Add to download history
            history = music.MusicHistory(
                album=album,
                provider=download_provider,
                quality=None,  # Quality not available in MusicResult
                date=datetime.datetime.now()
            )

            self.session.add(history)
            self.commit()

            logger.info(f"Successfully snatched {album.name} by {artist.name}")
            return True

        except Exception as e:
            logger.error(f"Error snatching album {album.name}: {e}")
            return False

    def search_thread(self):
        """
        Thread for searching for new albums.

        This method checks for new albums for all artists in the database
        and adds them to the database. It also triggers searches for these
        new albums on providers if auto_search is enabled.
        """
        logger.info("Starting music search thread")

        try:
            # Get all artists from the database
            artists = self.artist_query.all()

            if not artists:
                logger.debug("No artists found in database")
                return

            logger.info(f"Checking for new albums for {len(artists)} artists")

            for artist in artists:
                logger.debug(f"Checking for new albums for {artist.name}")

                # Get current albums for this artist
                current_albums = {album.musicbrainz_id for album in artist.albums if album.musicbrainz_id}

                # Get albums from MusicBrainz
                new_albums = []
                try:
                    albums = self.get_albums_for_artist(artist)

                    # Filter out albums that are already in the database
                    new_albums = [album for album in albums if album.musicbrainz_id not in current_albums]

                    if new_albums:
                        logger.info(f"Found {len(new_albums)} new albums for {artist.name}")

                        # Commit changes to database
                        self.commit()

                        # Search for new albums if auto_search is enabled
                        if settings.MUSIC_AUTO_SEARCH:
                            for album in new_albums:
                                logger.debug(f"Searching for {album.name}")
                                self.search_providers(album)
                    else:
                        logger.debug(f"No new albums found for {artist.name}")

                except Exception as e:
                    logger.error(f"Error checking for new albums for {artist.name}: {e}")
                    continue

            logger.info("Finished music search thread")

        except Exception as e:
            logger.error(f"Error in music search thread: {e}")
