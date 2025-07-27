import datetime
import logging
from typing import List

from slugify import slugify
from sqlalchemy import ForeignKey, JSON
from sqlalchemy.event import listen
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, sessionmaker

logger = logging.getLogger("sickchill.music")


class Base(DeclarativeBase):
    """Declarative Base Class"""


Session = sessionmaker()


class Artist(Base):
    __tablename__ = "artist"
    pk: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str]
    sort_name: Mapped[str]
    country: Mapped[str]
    status: Mapped[int]
    paused: Mapped[bool] = mapped_column(default=False)
    location: Mapped[str]
    start: Mapped[datetime.timedelta] = mapped_column(default=datetime.timedelta(days=-7))
    interval: Mapped[datetime.timedelta] = mapped_column(default=datetime.timedelta(days=1))
    added: Mapped[datetime.datetime] = mapped_column(default=datetime.datetime.now)
    updated: Mapped[datetime.datetime] = mapped_column(onupdate=datetime.datetime.now)
    searched: Mapped[datetime.datetime]
    slug: Mapped[str]

    albums: Mapped[List["Album"]] = relationship(backref="artist")
    images: Mapped[List["Images"]] = relationship(backref="artist")
    indexer_data: Mapped[List["IndexerData"]] = relationship(backref="artist")

    def __init__(self, name: str, sort_name: str = None, country: str = None):
        self.name = name
        self.sort_name = sort_name or name
        self.country = country

    @property
    def poster(self):
        return ""

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
    date: Mapped[datetime.date]
    year: Mapped[int]
    status: Mapped[int]
    paused: Mapped[bool] = mapped_column(default=False)
    location: Mapped[str]
    tracks: Mapped[int]
    type: Mapped[str]  # Album, EP, Single, etc.
    added: Mapped[datetime.datetime] = mapped_column(default=datetime.datetime.now)
    updated: Mapped[datetime.datetime] = mapped_column(onupdate=datetime.datetime.now)
    completed: Mapped[datetime.datetime]
    searched: Mapped[datetime.datetime]
    slug: Mapped[str]

    artist_pk: Mapped[int] = mapped_column(ForeignKey("artist.pk"))
    result_pk: Mapped[int] = mapped_column(ForeignKey("music_result.pk"))
    results: Mapped[List["MusicResult"]] = relationship(backref="album")

    images: Mapped[List["Images"]] = relationship(backref="album")
    indexer_data: Mapped[List["IndexerData"]] = relationship(backref="album")

    def __init__(self, name: str, year: int, artist_pk: int, tracks: int = 0, album_type: str = "Album"):
        self.name = name
        self.year = year
        self.artist_pk = artist_pk
        self.tracks = tracks
        self.type = album_type

    @property
    def poster(self):
        return ""

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