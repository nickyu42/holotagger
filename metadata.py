import logging
import os
import pathlib
from typing import List, Optional

import googleapiclient.discovery
import googleapiclient.errors
from fuzzywuzzy import process
from mutagen.easyid3 import EasyID3
from mutagen.id3 import APIC, ID3
from mutagen.mp3 import MP3

logger = logging.Logger('dl')


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


def guess_artist(song_title: str, choices: dict, guess_threshold=0.8) -> List[str]:
    bests = process.extractBests(song_title, tuple(choices.keys()), score_cutoff=guess_threshold)
    return [choices[t[0]] for t in bests]


def add_metadata(
        song_file: pathlib.Path,
        title: str,
        artist: str,
        thumbnail: pathlib.Path,
):
    audio = MP3(song_file.resolve(), ID3=EasyID3)

    audio['title'] = title
    audio['artist'] = artist
    audio['album'] = 'Vtuber Covers'
    audio.save()

    audio = MP3(song_file.resolve(), ID3=ID3)
    with open(str(thumbnail), 'rb') as f:
        audio.tags.add(APIC(mime='image/jpeg', type=3, desc='cover', data=f.read()))
    audio.save()


def get_thumbnail(artist: Optional[str] = None):
    pass
