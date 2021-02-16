import logging
import os
import pathlib
from typing import List, Dict, Set, Union
from urllib import request

import eyed3
import ffmpeg
import googleapiclient.discovery
import googleapiclient.errors
import yaml
from fuzzywuzzy import process
from pydantic import BaseModel

import src.settings as settings
from src.schemas import SongMetadata, ArtistMetadata

logger = logging.getLogger(__name__)


class YtChannelSnippet(BaseModel):
    thumbnails: Dict[str, dict]


class YtChannelInfo(BaseModel):
    kind: str
    id: str
    snippet: YtChannelSnippet


class YoutubeAPI:
    _API_SERVICE_NAME = 'youtube'
    _API_VERSION = 'v3'

    _youtube = None

    @classmethod
    def init(cls):
        if cls._youtube is None:
            key = settings.YOUTUBE_DEVELOPER_KEY

            if key is None:
                raise RuntimeError('YOUTUBE_DEVELOPER_KEY is not set')

            if settings.IS_DEBUG:
                os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

            # Get credentials and create an API client
            cls._youtube = googleapiclient.discovery.build(cls._API_SERVICE_NAME, cls._API_VERSION, developerKey=key)
            logging.info('Created Youtube API Resource')

        return cls._youtube

    @classmethod
    def video_info(cls, video_ids: List[str]) -> list:
        response = cls._youtube.videos().list(
            part='snippet',
            id=','.join(video_ids)
        ).execute()

        return [i['snippet'] for i in response['items']]

    @classmethod
    def channel_info(cls, channel_ids: List[str]) -> List[YtChannelInfo]:
        response = cls._youtube.channels().list(
            part='snippet',
            id=','.join(channel_ids)
        ).execute()

        total = [YtChannelInfo(**item) for item in response['items']]

        while 'nextPageToken' in response:
            response = cls._youtube.channels().list(
                part='snippet',
                id=','.join(channel_ids),
                pageToken=response['nextPageToken'],
            ).execute()
            total.extend(YtChannelInfo(**item) for item in response['items'])

        return total


def guess_artist(song_title: str, choices: Dict[str, ArtistMetadata], guess_threshold=80) -> Set[str]:
    bests = process.extractBests(song_title, tuple(choices.keys()), score_cutoff=guess_threshold)
    return set(choices[t[0]].name for t in bests)


def get_metadata(video_id: str, choices: dict, artists: List[ArtistMetadata]) -> SongMetadata:
    response = YoutubeAPI.video_info([video_id])[0]

    title = response['title']

    guessed_artists = set()

    for a in artists:
        if a.yt_id == response['channelId']:
            guessed_artists.add(a.name)

    guessed_artists |= guess_artist(title, choices)

    return SongMetadata(
        title=title,
        artists=list(guessed_artists),
        album='Vtuber Covers',
        original_artists=[],
        video_id=video_id,
        tagger=None,
        thumbnail_url=response['thumbnails']['maxres']['url'],
    )


def add_metadata(
        song_file: pathlib.Path,
        meta: SongMetadata,
        thumbnail: Union[pathlib.Path, str],
):
    """
    Add ID3 metadata to mp3 file.

    :param song_file: path to the mp3 file
    :param meta: the metadata to add
    :param thumbnail: the album cover image, if a path is given, it will use that file.
        A string represents a url and the thumbnail will be downloaded from there, if a url is given,
        it must be a jpeg
    """
    audio = eyed3.load(song_file.resolve())

    audio.tag.title = meta.title
    audio.tag.artist = ','.join(meta.artists)
    audio.tag.album = meta.album
    if isinstance(thumbnail, pathlib.Path):
        with thumbnail.open('rb') as f:
            audio.tag.images.set(3, f.read(), f'image/{thumbnail.suffix}', 'Album Art')
    else:
        response = request.urlopen(thumbnail)
        audio.tag.images.set(3, response.read(), response.info().get_content_type(), 'Album Art')
    audio.tag.save()


def force_mp3(song: pathlib.Path) -> pathlib.Path:
    """
    Encode media file into mp3 using ffmpeg.

    :param song: path to the file to encode
    :return: the changed path if the file was modified, otherwise the same path
    """
    audio = eyed3.load(song.resolve())

    # If the youtube native audio format can't be converted to mp3
    # without loss of quality by re-encoding, it seems youtube-dl
    # will choose not to, force re-encode if necessary
    if audio is None:
        logging.info(f'Force encode of {song}')

        song = song.with_suffix('.mp3')
        # TODO: improve encoding pipeline
        # TODO: replace library with subprocess?
        (ffmpeg
         .input(song.resolve())
         # -q:a 0 => variable bit rate
         .output(song, **{'q:a': 0})
         .run())
        return song

    return song


def load_artists(artists_file: pathlib.Path) -> (List[ArtistMetadata], Dict[str, ArtistMetadata]):
    with artists_file.open('r', encoding='utf8') as f:
        groups = yaml.load(f, Loader=yaml.FullLoader)

    artists = []
    artist_lookup = {}

    for group in groups.values():
        for artist in group:
            name = next(iter(artist))
            info = artist[name]

            created_artist = ArtistMetadata(
                name=name,
                fuzzy_names=info['names'],
                yt_id=info['yt'],
            )

            artists.append(created_artist)

            for n in info['names']:
                artist_lookup[n] = created_artist

    return artists, artist_lookup
