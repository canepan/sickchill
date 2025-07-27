import logging

from sickchill import settings
from sickchill.oldbeard import config

from .common import PageTemplate
from .index import WebRoot
from .routes import Route

logger = logging.getLogger("sickchill.music")


@Route("/music(/?.*)", name="music")
class MusicHandler(WebRoot):
    def _genericMessage(self, subject=None, message=None):
        t = PageTemplate(rh=self, filename="genericMessage.mako")
        return t.render(message=message, subject=subject, topmenu="music", title="")

    def index(self):
        t = PageTemplate(rh=self, filename="music/index.mako")
        return t.render(
            title=_("Music"),
            header=_("Artist List"),
            topmenu="music",
            music=settings.music_list,
            controller="music",
            action="index",
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
        if artist_id:
            artist = settings.music_list.add_from_musicbrainz(artist_id=artist_id)

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