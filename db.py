import datetime
from pathlib import Path
from typing import Any, List, Optional, Generator

from pydantic import BaseModel
from sqlalchemy import create_engine, Column, Integer, Text, Table, ForeignKey, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, Session

import settings
from metadata import SongMetadata

Base = declarative_base()


class Song(Base):
    __tablename__ = 'song'

    # Columns from backrefs
    # necessary for typing
    album: Column
    tagger: Column

    artist_association = Table(
        'song_artist_table',
        Base.metadata,
        Column('song_id', Integer, ForeignKey('song.id')),
        Column('artist_id', Integer, ForeignKey('artist.id')),
    )

    original_artist_association = Table(
        'song_origina_artist_table',
        Base.metadata,
        Column('song_id', Integer, ForeignKey('song.id')),
        Column('artist_id', Integer, ForeignKey('artist.id')),
    )

    id = Column(Integer, primary_key=True)
    title = Column(Text)
    filepath = Column(Text)
    created_date = Column(DateTime, default=datetime.datetime.utcnow)

    # Necessary for tagger field
    _tagger_id = Column(Integer, ForeignKey('tagger.id'), nullable=True)

    # Necessary for album field
    _album_id = Column(Integer, ForeignKey('album.id'), nullable=True)

    # Abstract relationship fields
    artists = relationship(
        'Artist', secondary=artist_association, backref='songs')
    original_artists = relationship(
        'Artist', secondary=original_artist_association, backref='original_songs')

    class Model(BaseModel):
        id: int
        title: str
        tagger: Optional[str]
        album: Optional[str]
        artists: List[str]
        original_artists: List[str]
        created_date: datetime.datetime

    def to_model(self) -> Model:
        model = Song.Model(
            id=self.id,
            title=self.title,
            artists=[a.name for a in self.artists],
            original_artists=[a.name for a in self.original_artists],
            created_date=self.created_date,
        )

        if self.tagger is not None:
            model.tagger = self.tagger.name

        if self.album is not None:
            model.album = self.album.name

        return model


class Artist(Base):
    __tablename__ = 'artist'

    id = Column(Integer, primary_key=True)
    name = Column(Text)
    yt_id = Column(Text, nullable=True)


class Album(Base):
    __tablename__ = 'album'

    id = Column(Integer, primary_key=True)
    name = Column(Text)
    songs = relationship('Song', backref='album')


class Tagger(Base):
    __tablename__ = 'tagger'

    id = Column(Integer, primary_key=True)
    name = Column(Text)
    songs = relationship('Song', backref='tagger')


def init(db_name: str) -> Any:
    """
    Initializes sqlite database.

    :param db_name: relative path to db file
    :return: db engine
    """
    engine = create_engine(f'sqlite:///{db_name}')
    Base.metadata.create_all(engine)

    return engine


def add_song(s: Session, meta: SongMetadata, path: Path):
    """
    Adds a song object to the database.

    :param s: current db session
    :param meta: the song metadata to create a Song from
    :param path: the host path to the song file
    """
    song = Song(
        title=meta.title,
        artists=get_or_create_artists(s, meta.artists),
        original_artists=get_or_create_artists(s, meta.original_artists),
        filepath=str(path.resolve()),
    )

    album = s.query(Album).filter(Album.name == meta.album).scalar()
    if album is None:
        song.album = Album(name=meta.album)
    else:
        song.album = album

    # Create tagger if not exists
    if meta.tagger is not None and meta.tagger != '':
        tagger = s.query(Tagger).filter(Tagger.name == meta.tagger).scalar()
        if tagger is None:
            song.tagger = Tagger(name=meta.tagger)
        else:
            song.tagger = tagger

    s.add(song)
    s.commit()


def get_or_create_artists(session: Session, artist_names: List[str]) -> List[Artist]:
    """
    Create Artist objects for each element in ``artist_names`` if no artist exists
    with the name already.
    """
    artists = []
    for name in artist_names:
        row = session.query(Artist).filter(Artist.name == name).scalar()
        if row is None:
            artists.append(Artist(name=name))
        else:
            artists.append(row)

    return artists


def get_songs(session: Session, limit: Optional[int] = None) -> Generator[Song, None, None]:
    """
    Query Song objects from the database, ordered by created date.

    :param session: current db session
    :param limit: the max number of songs to retrieve
    :return: a generator yielding the Song objects
    """
    q = session.query(Song).order_by(Song.created_date.desc())

    if limit is not None:
        q = q.limit(limit)

    return q.all()


db = init(settings.DB)
