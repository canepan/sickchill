import datetime
import json
import logging
import os
import threading

import musicbrainzngs
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from . import settings
from .oldbeard.databases import music
from .oldbeard.db import db_cons, db_full_path, db_locks

logger = logging.getLogger("sickchill.music")


class MusicList:
    def __init__(self):
        # Set up MusicBrainz API
        musicbrainzngs.set_useragent(
            "SickChill", 
            settings.BRANCH, 
            "https://sickchill.github.io/"
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

    def add_from_musicbrainz(self, artist_id: str):
        """
        Add an artist from MusicBrainz.
        
        Args:
            artist_id: MusicBrainz artist ID
            
        Returns:
            Artist object
        """
        logger.debug(f"Adding artist from MusicBrainz with id: {artist_id}")
        existing = self.session.query(music.IndexerData).filter_by(pk=artist_id).first()
        if existing:
            logger.debug(f"Artist already existed as {existing.artist.name}")
            return existing.artist

        try:
            # Get artist info from MusicBrainz
            mb_artist = musicbrainzngs.get_artist_by_id(artist_id, includes=["aliases", "tags"])["artist"]
            
            # Create artist instance
            name = mb_artist.get("name", "")
            sort_name = mb_artist.get("sort-name", name)
            country = mb_artist.get("country", "")
            
            instance = music.Artist(name=name, sort_name=sort_name, country=country)
            
            # Create indexer data
            mb_data = music.IndexerData(site="musicbrainz", data=mb_artist, pk=artist_id)
            
            # Add genres from tags
            if "tag-list" in mb_artist:
                for tag in mb_artist["tag-list"]:
                    if "name" in tag and int(tag.get("count", 0)) > 0:
                        logger.debug(f"Adding genre {tag['name']}")
                        mb_data.genres.append(music.Genres(pk=tag["name"]))
            
            instance.indexer_data.append(mb_data)
            
            # Get albums for this artist
            self.get_albums_for_artist(instance)
            
            self.commit(instance)
            
            logger.debug(f"Returning instance for {instance.name}")
            return instance
            
        except musicbrainzngs.WebServiceError as e:
            logger.error(f"MusicBrainz API error while adding artist: {e}")
            return None
        except Exception as e:
            logger.error(f"Error while adding artist: {e}")
            return None

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
        
        try:
            while True:
                result = musicbrainzngs.browse_release_groups(
                    artist=artist_id,
                    release_type=["album", "ep", "single"],
                    limit=limit,
                    offset=offset
                )
                
                release_groups = result.get("release-group-list", [])
                if not release_groups:
                    break
                    
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
                    existing = self.session.query(music.IndexerData).filter_by(pk=album_id).first()
                    if existing:
                        logger.debug(f"Album already existed as {existing.album.name}")
                        albums.append(existing.album)
                        continue
                    
                    # Get more detailed info about the release group
                    try:
                        release_group_info = musicbrainzngs.get_release_group_by_id(
                            album_id, 
                            includes=["releases", "tags"]
                        )["release-group"]
                        
                        # Get track count from the first release
                        tracks = 0
                        if "release-list" in release_group_info and release_group_info["release-list"]:
                            first_release = release_group_info["release-list"][0]
                            release_id = first_release.get("id")
                            
                            if release_id:
                                release_info = musicbrainzngs.get_release_by_id(
                                    release_id, 
                                    includes=["recordings"]
                                )["release"]
                                
                                if "medium-list" in release_info:
                                    for medium in release_info["medium-list"]:
                                        tracks += int(medium.get("track-count", 0))
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
                    
                    # Add genres from tags
                    if "tag-list" in release_group_info:
                        for tag in release_group_info["tag-list"]:
                            if "name" in tag and int(tag.get("count", 0)) > 0:
                                logger.debug(f"Adding genre {tag['name']}")
                                mb_data.genres.append(music.Genres(pk=tag["name"]))
                    
                    album.indexer_data.append(mb_data)
                    albums.append(album)
                    
                    # Add album to session
                    self.session.add(album)
                
                offset += limit
                if len(release_groups) < limit:
                    break
            
            return albums
            
        except musicbrainzngs.WebServiceError as e:
            logger.error(f"MusicBrainz API error while getting albums: {e}")
            return albums
        except Exception as e:
            logger.error(f"Error while getting albums: {e}")
            return albums

    def commit(self, instance=None):
        logger.debug("Committing")
        if instance:
            self.session.add(instance)
        self.session.flush()
        self.session.commit()

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
                    music.MusicResult(result=result, album=album_obj, provider=provider)

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
            download_url = result.result.url
            download_name = result.result.name
            download_size = result.result.size
            download_provider = result.provider.name
            
            # Create download directory path
            download_dir = os.path.join(settings.MUSIC_DOWNLOAD_DIR, artist.name, album.name)
            
            # Ensure download directory exists
            if not os.path.isdir(download_dir):
                os.makedirs(download_dir)
                
            # Use SickChill's download client to download the album
            from sickchill.oldbeard import clients
            
            # Get the appropriate download client
            download_client = clients.getClientInstance(settings.TORRENT_METHOD)()
            
            if not download_client:
                logger.error(f"Could not get download client {settings.TORRENT_METHOD}")
                return False
                
            # Send the download to the client
            result = download_client.sendTORRENT(
                download_url,
                download_name,
                download_dir
            )
            
            if not result:
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
                quality=result.result.quality,
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