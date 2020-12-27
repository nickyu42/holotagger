from pathlib import Path
from typing import Any, List

from sqlalchemy import create_engine, Column, Integer, Text, Table, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, Session

from metadata import SongMetadata

Base = declarative_base()


class Song(Base):
    __tablename__ = 'song'

    artist_association = Table(
        'song_artist_table',
        Base.metadata,
        Column('song_id', Integer, ForeignKey('song.id')),
        Column('artist_id', Integer, ForeignKey('artist.id')),
    )

    id = Column(Integer, primary_key=True)
    title = Column(Text)
    filepath = Column(Text)

    # Necessary for tagger field
    _tagger_id = Column(Integer, ForeignKey('tagger.id'), nullable=True)

    # Necessary for album field
    _album_id = Column(Integer, ForeignKey('album.id'), nullable=True)

    # Abstract relationship fields
    artists = relationship('Artist', secondary=artist_association, backref='songs')
    original_artists = relationship('Artist', secondary=artist_association, backref='original_songs')


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
    if meta.tagger is not None:
        tagger = s.query(Tagger).filter(Tagger.name == meta.tagger).scalar()
        if tagger is None:
            song.tagger = Tagger(name=meta.tagger)
        else:
            song.tagger = tagger

    s.add(song)
    s.commit()


def get_or_create_artists(session: Session, artist_names: List[str]) -> List[Artist]:
    artists = []
    for name in artist_names:
        row = session.query(Artist).filter(Artist.name == name).scalar()
        if row is None:
            artists.append(Artist(name=name))
        else:
            artists.append(row)

    return artists
