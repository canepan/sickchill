import logging
import os

from sickchill import settings
from sickchill.oldbeard import config
from sickchill.oldbeard.databases import music
from sickchill.oldbeard.databases.music import AlbumStatus

from .common import PageTemplate
from .index import WebRoot
from .routes import Route

logger = logging.getLogger("sickchill.music")


@Route("/music(/?.*)", name="music")
class MusicHandler(WebRoot):
    """
    Handler for music-related pages
    """
    def _genericMessage(self, subject=None, message=None):
        t = PageTemplate(rh=self, filename="genericMessage.mako")
        return t.render(message=message, subject=subject, topmenu="music", title="")

    def index(self):
        t = PageTemplate(rh=self, filename="music/index.mako")
        selected_root = self.get_body_argument("root", "")

        if selected_root and settings.MUSIC_ROOT_DIRS:
            backend_dirs = settings.MUSIC_ROOT_DIRS.split("|")[1:]
            try:
                assert selected_root != "-1"
                selected_root_dir = backend_dirs[int(selected_root)]
            except (IndexError, ValueError, TypeError, AssertionError):
                selected_root_dir = ""
        else:
            selected_root_dir = ""

        artists = []
        for artist in settings.music_list:
            if not selected_root_dir or (artist.location and artist.location.startswith(selected_root_dir)):
                artists.append(artist)

        return t.render(
            title=_("Music"),
            header=_("Artist List"),
            topmenu="music",
            music=artists,
            controller="music",
            action="index",
            selected_root=selected_root or "-1",
        )

    def search(self):
        query = self.get_body_argument("query", "")
        search_results = []
        if query:
            search_results = settings.music_list.search_musicbrainz(query=query)
        t = PageTemplate(rh=self, filename="music/search.mako")
        return t.render(
            title=_("Music"),
            header=_("Artist Search"),
            topmenu="music",
            controller="music",
            action="search",
            search_results=search_results,
            music=settings.music_list,
            query=query,
        )

    def add(self):
        artist = None
        artist_id = self.get_body_argument("musicbrainz", None)
        
        # Get the selected root directory
        selected_dir = None
        if settings.MUSIC_ROOT_DIRS:
            music_root_dir = self.get_body_argument("musicRootDir", None)
            if music_root_dir:
                selected_dir = music_root_dir
        
        if artist_id:
            result = settings.music_list.add_from_musicbrainz(artist_id=artist_id)

            # If result is an Artist object, use it
            if hasattr(result, 'slug'):
                artist = result
                
                # Set the artist location if a root directory was selected
                if selected_dir:
                    # Create the artist directory path
                    artist_dir = os.path.join(selected_dir, artist.name)
                    
                    # Check if the directory exists or if we should create it
                    if not (os.path.isdir(artist_dir) or settings.CREATE_MISSING_SHOW_DIRS):
                        return self._genericMessage(_("Error"), _("Location does not exist and CREATE_MISSING_SHOW_DIRS is disabled"))
                    
                    # Create the directory if it doesn't exist
                    if not os.path.isdir(artist_dir):
                        try:
                            os.makedirs(artist_dir)
                        except OSError as e:
                            return self._genericMessage(_("Error"), _("Failed to create directory: {error}").format(error=str(e)))
                    
                    # Set the artist location
                    artist.location = artist_dir
                    
                    # Set album locations
                    for album in artist.albums:
                        album.location = os.path.join(artist_dir, album.name)
                    
                    # Save changes to the database
                    settings.music_list.commit()
                
            # If result is True, the artist was added to the queue
            elif result is True:
                # Redirect to the index page with a message
                return self.redirect(self.reverse_url("music", ""))

        if not artist:
            return self.redirect(self.reverse_url("music-search", "search"))

        return self.redirect(self.reverse_url("music-details", "details", artist.slug))

    def remove(self):
        pk = self.path_kwargs.get("pk")
        if pk is not None:
            if not settings.music_list.artist_query.get(pk):
                return self._genericMessage(_("Error"), _("Artist not found"))

            settings.music_list.delete_artist(pk)

        t = PageTemplate(rh=self, filename="music/remove.mako")
        return t.render(
            title=_("Music"),
            header=_("Artist Remove"),
            topmenu="music",
            music=settings.music_list,
            controller="music",
            action="remove",
        )

    def details(self):
        artist = settings.music_list.artist_by_slug(self.path_kwargs.get("slug"))
        if not artist:
            return self._genericMessage(_("Error"), _("Artist not found"))

        t = PageTemplate(rh=self, filename="music/details.mako")
        return t.render(
            title=_("Music"),
            header=_("Artist Details"),
            topmenu="music",
            controller="music",
            action="details",
            artist=artist,
            artist_message=None,
        )

    def album_details(self):
        album = settings.music_list.album_by_slug(self.path_kwargs.get("slug"))
        if not album:
            return self._genericMessage(_("Error"), _("Album not found"))

        t = PageTemplate(rh=self, filename="music/album_details.mako")
        return t.render(
            title=_("Music"),
            header=_("Album Details"),
            topmenu="music",
            controller="music",
            action="album_details",
            album=album,
            album_message=None,
        )

    def set_album_status(self):
        """
        Set the status of a single album
        """
        album_id = self.path_kwargs.get("pk")
        status = self.get_query_argument("status", None)

        if not album_id or not status:
            return self._genericMessage(_("Error"), _("Missing album ID or status"))

        try:
            status = int(status)
            if status not in [AlbumStatus.WANTED, AlbumStatus.SKIPPED, AlbumStatus.IGNORED]:
                return self._genericMessage(_("Error"), _("Invalid status"))
        except ValueError:
            return self._genericMessage(_("Error"), _("Invalid status value"))

        album = settings.music_list.album_query.get(album_id)
        if not album:
            return self._genericMessage(_("Error"), _("Album not found"))

        # Update album status
        album.status = status
        settings.music_list.commit()

        # Redirect back to the artist details page
        return self.redirect(self.reverse_url("music-details", "details", album.artist.slug))

    def set_albums_status(self):
        """
        Set the status of multiple albums via AJAX
        """
        # Log all request arguments for debugging
        logger.debug(f"set_albums_status request arguments: {self.request.arguments}")

        albums = self.get_body_argument("albums", "")
        status = self.get_body_argument("status", None)
        artist_id = self.get_body_argument("artist", None)

        logger.debug(f"set_albums_status parameters: albums={albums}, status={status}, artist_id={artist_id}")

        if not albums or not status:
            logger.error("Missing albums or status in request")
            return self.write({"success": False, "message": _("Missing albums or status")})

        try:
            status = int(status)
            if status not in [AlbumStatus.WANTED, AlbumStatus.SKIPPED, AlbumStatus.IGNORED]:
                logger.error(f"Invalid status value: {status}")
                return self.write({"success": False, "message": _("Invalid status")})
        except ValueError:
            logger.error(f"Invalid status value (not an integer): {status}")
            return self.write({"success": False, "message": _("Invalid status value")})

        album_ids = albums.split(",")
        logger.debug(f"Processing album IDs: {album_ids}")
        updated = 0

        for album_id in album_ids:
            try:
                album = settings.music_list.album_query.get(int(album_id))
                if album:
                    album.status = status
                    updated += 1
                    logger.debug(f"Updated album {album_id} status to {status}")
                else:
                    logger.error(f"Album not found: {album_id}")
            except (ValueError, TypeError):
                logger.error(f"Invalid album ID: {album_id}")

        if updated > 0:
            settings.music_list.commit()
            logger.debug(f"Committed {updated} album status changes")

        return self.write({"success": True, "message": f"{updated} albums updated"})

    def search_album(self):
        """
        Search for an album on providers
        """
        album_id = self.path_kwargs.get("pk")

        if not album_id:
            return self._genericMessage(_("Error"), _("Missing album ID"))

        album = settings.music_list.album_query.get(album_id)
        if not album:
            return self._genericMessage(_("Error"), _("Album not found"))

        # Search for the album on providers
        settings.music_list.search_providers(album)

        # Redirect to album details page
        return self.redirect(self.reverse_url("music-album_details", "album_details", album.slug))

    def snatch_album(self):
        """
        Snatch a specific album result
        """
        result_id = self.path_kwargs.get("pk")

        if not result_id:
            return self._genericMessage(_("Error"), _("Missing result ID"))

        result = settings.music_list.session.query(music.MusicResult).get(result_id)
        if not result:
            return self._genericMessage(_("Error"), _("Result not found"))

        # Snatch the album
        success = settings.music_list.snatch_album(result)

        if success:
            # Redirect to album details page
            return self.redirect(self.reverse_url("music-album_details", "album_details", result.album.slug))
        else:
            return self._genericMessage(_("Error"), _("Failed to snatch album"))
            
    def set_artist_location(self):
        """
        Set the location for an artist and all its albums
        """
        artist_id = self.path_kwargs.get("pk")
        location = self.get_body_argument("location", None)

        if not artist_id or not location:
            return self._genericMessage(_("Error"), _("Missing artist ID or location"))

        artist = settings.music_list.artist_query.get(artist_id)
        if not artist:
            return self._genericMessage(_("Error"), _("Artist not found"))

        # Normalize the location path
        location = os.path.normpath(location)
        
        # Check if the location exists or if we should create it
        if not (os.path.isdir(location) or settings.CREATE_MISSING_SHOW_DIRS):
            return self._genericMessage(_("Error"), _("Location does not exist and CREATE_MISSING_SHOW_DIRS is disabled"))
        
        # Create the directory if it doesn't exist
        if not os.path.isdir(location):
            try:
                os.makedirs(location)
            except OSError as e:
                return self._genericMessage(_("Error"), _("Failed to create directory: {error}").format(error=str(e)))
        
        # Update the artist location
        old_location = artist.location
        artist.location = location
        
        # Update all album locations
        for album in artist.albums:
            if old_location and album.location and album.location.startswith(old_location):
                # If the album had a location under the old artist location, update it
                album_relative_path = os.path.relpath(album.location, old_location)
                album.location = os.path.join(location, album_relative_path)
            else:
                # Otherwise, set it to a new location under the artist directory
                album.location = os.path.join(location, album.name)
        
        # Save changes to the database
        settings.music_list.commit()
        
        # Redirect back to the artist details page
        return self.redirect(self.reverse_url("music-details", "details", artist.slug))
