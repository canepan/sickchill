import datetime
import logging
import os
from typing import List

from slugify import slugify
from sqlalchemy import ForeignKey, JSON
from sqlalchemy.event import listen
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, sessionmaker

from sickchill import settings

logger = logging.getLogger("sickchill.music")


class AlbumStatus:
    """Album status constants"""
    WANTED = 1
    SNATCHED = 2
    DOWNLOADED = 3
    SKIPPED = 4
    IGNORED = 5


class Base(DeclarativeBase):
    """Declarative Base Class"""


Session = sessionmaker()


class Artist(Base):
    __tablename__ = "artist"
    pk: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str]
    sort_name: Mapped[str]
    country: Mapped[str] = mapped_column(nullable=True)
    status: Mapped[int] = mapped_column(nullable=True)
    paused: Mapped[bool] = mapped_column(default=False)
    location: Mapped[str] = mapped_column(nullable=True)
    start: Mapped[datetime.timedelta] = mapped_column(default=datetime.timedelta(days=-7))
    interval: Mapped[datetime.timedelta] = mapped_column(default=datetime.timedelta(days=1))
    added: Mapped[datetime.datetime] = mapped_column(default=datetime.datetime.now)
    updated: Mapped[datetime.datetime] = mapped_column(onupdate=datetime.datetime.now)
    searched: Mapped[datetime.datetime] = mapped_column(nullable=True)
    slug: Mapped[str] = mapped_column(nullable=True)

    albums: Mapped[List["Album"]] = relationship(backref="artist")
    images: Mapped[List["Images"]] = relationship(backref="artist")
    indexer_data: Mapped[List["IndexerData"]] = relationship(backref="artist")

    def __init__(self, name: str, sort_name: str = None, country: str = None):
        self.name = name
        self.sort_name = sort_name or name
        self.country = country
        self.updated = datetime.datetime.now()  # Set updated field to current datetime

    @property
    def poster(self):
        """
        Returns the local file path to the artist poster image.
        If the image doesn't exist locally, returns an empty string.
        """
        # Check if we have any images in the database
        if self.images:
            for image in self.images:
                if image.style == 1:  # Assuming style 1 is for posters
                    return image.path

        # If no image in database, check if there's a file in the expected location
        if self.location:
            poster_path = os.path.join(self.location, "artist-poster.jpg")
            if os.path.isfile(poster_path):
                return poster_path

        return ""

    def image_url(self, which):
        """
        Returns a web-accessible URL for the artist image.
        
        :param which: Type of image ('poster', 'banner', 'fanart')
        :return: URL to the image
        """
        from sickchill import settings

        if which != 'poster':
            return "images/poster.png"

        if not self.poster:
            return "images/poster.png"

        # Use the image cache to get a web-accessible URL
        cache_dir = os.path.abspath(os.path.join(settings.CACHE_DIR, "images"))
        cache_file = os.path.join(cache_dir, f"artist-{self.pk}.jpg")

        # If the cache file doesn't exist, copy the poster to the cache
        if not os.path.isfile(cache_file) and os.path.isfile(self.poster):
            if not os.path.isdir(cache_dir):
                os.makedirs(cache_dir)
            try:
                import shutil
                shutil.copy(self.poster, cache_file)
            except Exception as e:
                logger.error(f"Error copying artist poster to cache: {e}")
                return "images/poster.png"

        # Return the URL to the cached image
        if os.path.isfile(cache_file):
            return f"cache/images/artist-{self.pk}.jpg"

        return "images/poster.png"

    def __get_named_indexer_data(self, name):
        if self.indexer_data:
            for data in self.indexer_data:
                if data.site == name:
                    return data

    @property
    def musicbrainz_data(self):
        data = self.__get_named_indexer_data("musicbrainz")
        if data:
            return data.data
        return dict()

    @property
    def musicbrainz_id(self):
        data = self.__get_named_indexer_data("musicbrainz")
        if data:
            return data.pk
        return ""

    @property
    def musicbrainz_genres(self):
        data = self.__get_named_indexer_data("musicbrainz")
        if data:
            return data.genres
        return []

    def __get_indexer_values(self, name, keys: list):
        try:
            data = getattr(self, f"{name}_data")
            for key in keys:
                data = data[key]
            return data
        except AttributeError:
            logger.debug(f"We do not have data for {name}")
        except (IndexError, KeyError):
            logger.debug(f"KeyError: {name}{''.join([f'[{k}]' for k in keys])}")

    @staticmethod
    def slugify(target, value, old_value, initiator):
        if value and (not target.slug or value != old_value):
            target.slug = slugify(value)

    def search_strings(self):
        return {"Artist": [self.name]}

    def __repr__(self):
        return f"{self.name}"


listen(Artist.name, "set", Artist.slugify, retval=False)


class Album(Base):
    __tablename__ = "album"
    pk: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str]
    date: Mapped[datetime.date] = mapped_column(nullable=True)
    year: Mapped[int]
    status: Mapped[int] = mapped_column(nullable=True)
    paused: Mapped[bool] = mapped_column(default=False)
    location: Mapped[str] = mapped_column(nullable=True)
    tracks: Mapped[int]
    type: Mapped[str]  # Album, EP, Single, etc.
    added: Mapped[datetime.datetime] = mapped_column(default=datetime.datetime.now)
    updated: Mapped[datetime.datetime] = mapped_column(onupdate=datetime.datetime.now)
    completed: Mapped[datetime.datetime] = mapped_column(nullable=True)
    searched: Mapped[datetime.datetime] = mapped_column(nullable=True)
    slug: Mapped[str] = mapped_column(nullable=True)

    artist_pk: Mapped[int] = mapped_column(ForeignKey("artist.pk"))
    results: Mapped[List["MusicResult"]] = relationship(backref="album")

    images: Mapped[List["Images"]] = relationship(backref="album")
    indexer_data: Mapped[List["IndexerData"]] = relationship(backref="album")

    def __init__(self, name: str, year: int, artist_pk: int, tracks: int = 0, album_type: str = "Album"):
        self.name = name
        self.year = year
        self.artist_pk = artist_pk
        self.tracks = tracks
        self.type = album_type
        self.status = AlbumStatus.IGNORED
        self.updated = datetime.datetime.now()  # Set updated field to current datetime

    @property
    def poster(self):
        """
        Returns the local file path to the album cover image.
        If the image doesn't exist locally, returns an empty string.
        """
        # Check if we have any images in the database
        if self.images:
            for image in self.images:
                if image.style == 1:  # Assuming style 1 is for covers
                    return image.path

        # If no image in database, check if there's a file in the expected location
        if self.location:
            cover_path = os.path.join(self.location, "cover.jpg")
            if os.path.isfile(cover_path):
                return cover_path

        return ""

    def image_url(self, which):
        """
        Returns a web-accessible URL for the album image.

        :param which: Type of image ('poster', 'banner', 'fanart')
        :return: URL to the image
        """


        if which != 'poster':
            return "images/poster.png"

        if not self.poster:
            return "images/poster.png"

        # Use the image cache to get a web-accessible URL
        cache_dir = os.path.abspath(os.path.join(settings.CACHE_DIR, "images"))
        cache_file = os.path.join(cache_dir, f"album-{self.pk}.jpg")

        # If the cache file doesn't exist, copy the poster to the cache
        if not os.path.isfile(cache_file) and os.path.isfile(self.poster):
            if not os.path.isdir(cache_dir):
                os.makedirs(cache_dir)
            try:
                import shutil
                shutil.copy(self.poster, cache_file)
            except Exception as e:
                logger.error(f"Error copying album poster to cache: {e}")
                return "images/poster.png"

        # Return the URL to the cached image
        if os.path.isfile(cache_file):
            return f"cache/images/album-{self.pk}.jpg"

        return "images/poster.png"

    def __get_named_indexer_data(self, name):
        if self.indexer_data:
            for data in self.indexer_data:
                if data.site == name:
                    return data

    @property
    def musicbrainz_data(self):
        data = self.__get_named_indexer_data("musicbrainz")
        if data:
            return data.data
        return dict()

    @property
    def musicbrainz_id(self):
        data = self.__get_named_indexer_data("musicbrainz")
        if data:
            return data.pk
        return ""

    @staticmethod
    def slugify(target, value, old_value, initiator):
        if value and (not target.slug or value != old_value):
            target.slug = slugify(value)

    def search_strings(self):
        return {"Album": [f"{self.artist.name} {self.name}"]}

    def __repr__(self):
        return f"{self.name}"


listen(Album.name, "set", Album.slugify, retval=False)


class MusicResult(Base):
    __tablename__ = "music_result"
    pk: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str]
    title: Mapped[str]
    url: Mapped[str]
    size: Mapped[int]
    year: Mapped[int]
    provider: Mapped[str]
    seeders: Mapped[int]
    leechers: Mapped[int]
    info_hash: Mapped[str]
    group: Mapped[str]
    kind: Mapped[str]
    guess = mapped_column(JSON)
    found: Mapped[datetime.datetime] = mapped_column(default=datetime.datetime.now)
    updated: Mapped[datetime.datetime] = mapped_column(onupdate=datetime.datetime.now)

    album_pk: Mapped[int] = mapped_column(ForeignKey("album.pk"))

    session = Session()

    def __init__(self, result: dict, album, provider):
        self.info_hash = result.get("hash", "")
        self.url = result.get("link", "")
        self.name = result.get("title", "")
        self.title = album.name
        self.group = result.get("release_group", "")
        self.seeders = result.get("seeders", 0)
        self.leechers = result.get("leechers", 0)
        self.size = result.get("size", 0)
        self.year = album.year
        self.kind = provider.provider_type
        self.provider = provider.get_id()
        self.album = album
        self.album_pk = album.pk
        self.guess = result.get("guess", {})
        self.updated = datetime.datetime.now()

    def __repr__(self):
        return f"{self.name}"


class Images(Base):
    __tablename__ = "music_images"

    url: Mapped[str] = mapped_column(primary_key=True)
    path: Mapped[str]
    site: Mapped[str]
    style: Mapped[int]

    artist_pk: Mapped[int] = mapped_column(ForeignKey("artist.pk"), nullable=True)
    album_pk: Mapped[int] = mapped_column(ForeignKey("album.pk"), nullable=True)

    def __init__(self, site: str, url: str, path: str, style: int, artist_pk: int = None, album_pk: int = None):
        self.url = url
        self.path = path
        self.site = site
        self.style = style
        self.artist_pk = artist_pk
        self.album_pk = album_pk


class IndexerData(Base):
    __tablename__ = "music_indexer_data"
    pk: Mapped[str] = mapped_column(primary_key=True)
    site: Mapped[str]
    data = mapped_column(JSON)

    artist_pk: Mapped[int] = mapped_column(ForeignKey("artist.pk"), nullable=True)
    album_pk: Mapped[int] = mapped_column(ForeignKey("album.pk"), nullable=True)

    genres: Mapped[List["Genres"]] = relationship(backref="indexer_data")

    def __repr__(self):
        if self.artist:
            return f"[{self.__tablename__.replace('_', ' ').title()}] {self.site}: {self.pk} - {self.artist.name}"
        elif self.album:
            return f"[{self.__tablename__.replace('_', ' ').title()}] {self.site}: {self.pk} - {self.album.name}"
        return f"[{self.__tablename__.replace('_', ' ').title()}] {self.site}: {self.pk}"


class Genres(Base):
    __tablename__ = "music_genres"
    pk: Mapped[str] = mapped_column(primary_key=True)
    indexer_data_pk: Mapped[int] = mapped_column(ForeignKey("music_indexer_data.pk"))


class MusicHistory(Base):
    __tablename__ = "music_history"
    pk: Mapped[int] = mapped_column(primary_key=True)
    album_pk: Mapped[int] = mapped_column(ForeignKey("album.pk"))
    provider: Mapped[str]
    quality: Mapped[str] = mapped_column(nullable=True)
    date: Mapped[datetime.datetime] = mapped_column(default=datetime.datetime.now)

    album: Mapped["Album"] = relationship(backref="history")

    def __init__(self, album, provider, quality=None, date=None):
        self.album = album
        self.album_pk = album.pk
        self.provider = provider
        self.quality = quality
        if date:
            self.date = date