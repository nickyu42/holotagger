import json
import logging
import os
import pathlib
from typing import List, Optional, Dict, Set

import googleapiclient.discovery
import googleapiclient.errors
import yaml
from fuzzywuzzy import process
from mutagen.easyid3 import EasyID3
from mutagen.id3 import APIC, ID3
from mutagen.mp3 import MP3
from pydantic.dataclasses import dataclass
from pydantic.json import pydantic_encoder

logger = logging.getLogger('dl')


@dataclass
class SongMetadata:
    title: str
    artists: List[str]
    album: str
    original_artists = List[str]

    def serialize(self):
        return json.dumps(self, default=pydantic_encoder)


@dataclass
class Artist:
    name: str
    fuzzy_names: List[str]
    yt_id: str

    def serialize(self):
        return json.dumps(self, default=pydantic_encoder)


class YoutubeAPI:
    _API_SERVICE_NAME = 'youtube'
    _API_VERSION = 'v3'

    _youtube = None

    @classmethod
    def init(cls):
        if cls._youtube is None:
            key = os.environ.get('YOUTUBE_DEVELOPER_KEY')

            if key is None:
                raise RuntimeError('YOUTUBE_DEVELOPER_KEY is not set')

            if os.environ.get('DEBUG', 'false').lower() == 'true':
                os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

            # Get credentials and create an API client
            cls._youtube = googleapiclient.discovery.build(cls._API_SERVICE_NAME, cls._API_VERSION, developerKey=key)
            logging.info('Created Youtube API Resource')

        return cls._youtube

    @classmethod
    def video_info(cls, video_ids: List[str]) -> list:
        if cls._youtube is None:
            cls.init()

        request = cls._youtube.videos().list(
            part='snippet',
            id=','.join(video_ids)
        )
        response = request.execute()
        return [i['snippet'] for i in response['items']]


def guess_artist(song_title: str, choices: Dict[str, Artist], guess_threshold=80) -> Set[str]:
    bests = process.extractBests(song_title, tuple(choices.keys()), score_cutoff=guess_threshold)
    print(bests)
    return set(choices[t[0]].name for t in bests)


def get_metadata(video_id: str, choices: dict, artists: List[Artist]) -> SongMetadata:
    response = YoutubeAPI.video_info([video_id])[0]

    title = response['title']

    guessed_artists = set()

    for a in (a for a in artists if a.yt_id == response['channelId']):
        guessed_artists.add(a.name)

    guessed_artists |= guess_artist(title, choices)

    return SongMetadata(title=title, artists=list(guessed_artists), album='Vtuber Covers')


def add_metadata(
        song_file: pathlib.Path,
        meta: SongMetadata,
        thumbnail: pathlib.Path,
):
    audio = MP3(song_file.resolve(), ID3=EasyID3)

    audio['title'] = meta.title
    audio['artist'] = ','.join(meta.artists)
    audio['album'] = meta.album
    audio.save()

    audio = MP3(song_file.resolve(), ID3=ID3)
    with open(str(thumbnail), 'rb') as f:
        audio.tags.add(APIC(mime='image/jpeg', type=3, desc='cover', data=f.read()))
    audio.save()


def load_artists(artists_file: pathlib.Path) -> (List[Artist], Dict[str, Artist]):
    with artists_file.open('r', encoding='utf8') as f:
        groups = yaml.load(f, Loader=yaml.FullLoader)

    artists = []
    artist_lookup = {}

    for group in groups.values():
        for artist in group:
            name = next(iter(artist))
            info = artist[name]

            created_artist = Artist(
                name=name,
                fuzzy_names=info['names'],
                yt_id=info['yt'],
            )

            artists.append(created_artist)

            for n in info['names']:
                artist_lookup[n] = created_artist

    return artists, artist_lookup


def get_thumbnail(artist: Optional[str] = None):
    pass
