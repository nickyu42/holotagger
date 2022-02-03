import json
import logging
import os
import pathlib
import warnings
from typing import Dict, List, Union
from urllib import request

import eyed3
import ffmpeg
import googleapiclient.discovery
import googleapiclient.errors
import pykakasi
import yaml
from fuzzywuzzy import process
from pydantic import BaseModel

import src.settings as settings
from src.schemas import ArtistAccount, ArtistMetadata, SongMetadata

PREFERRED_THUMBNAIL_RES = [
    'maxres',
    'high',
    'medium',
    'default',
]

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
            cls._youtube = googleapiclient.discovery.build(
                cls._API_SERVICE_NAME,
                cls._API_VERSION,
                developerKey=key,
                cache_discovery=False
            )

            logger.info('Created Youtube API Resource')

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


def guess_artist(song_title: str, artist_names: list,
                 artist_lookup: dict[str, ArtistMetadata], guess_threshold=80) -> dict[str, tuple[ArtistMetadata, int]]:
    bests = process.extractBests(song_title, artist_names, score_cutoff=guess_threshold)
    logger.debug('guessed based on title: %s', bests)

    guessed_artists = {}
    for choice, score in bests:
        artist = artist_lookup[choice]
        guessed_artists[artist.name] = (artist, score)

    return guessed_artists


def get_metadata(video_id: str, artist_names: list, artist_lookup: dict,
                 yt_lookup: dict[str, ArtistMetadata]) -> SongMetadata:
    response = YoutubeAPI.video_info([video_id])[0]

    title = response['title']
    channel_id = response['channelId']

    logger.debug('guessing artist based on yt_id')
    guessed_artists: dict[str, tuple[ArtistMetadata, int]] = {}

    if channel_id in yt_lookup:
        artist = yt_lookup[channel_id]
        logger.debug('guessed %s from yt_id', artist.name)
        guessed_artists[artist.name] = (artist, 100)

    logger.debug('guessing artist using fuzzy matching')
    guessed_artists.update(guess_artist(title, artist_names, artist_lookup))

    artists = sorted(guessed_artists.values(), key=lambda a: a[1], reverse=True)

    # Get thumbnail from video
    for res in PREFERRED_THUMBNAIL_RES:
        if res in response['thumbnails']:
            thumbnail_url = response['thumbnails'][res]['url']
            break
    else:
        # XXX: This should never be triggered, unless the 'default' key is missing
        raise RuntimeError(f'Youtube response is missing default thumbnail url: {response["thumbnails"]}')

    return SongMetadata(
        title=title,
        artists=artists,
        album='Vtuber Covers',
        original_artists=[],
        video_id=video_id,
        tagger=None,
        thumbnail_url=thumbnail_url,
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
    audio.tag.artist = ','.join(a[0] for a in meta.artists)
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
    warnings.warn('load_artists should not be used anymore', DeprecationWarning, stacklevel=2)

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


def load_vdb_artists(
    artists_file: pathlib.Path
) -> (list[str], dict[str, ArtistMetadata], dict[str, ArtistMetadata]):
    """
    Loads the virtual youtubers database from a JSON file and processes it
    to objects used for metadata matching.

    - Filter by 'vtuber' type
    - Extracts all youtube channel IDs
    - Converts jp to romaiji for some names
    - Creates lookups for fast matching
    """
    with artists_file.open('r', encoding='utf8') as f:
        vbd = json.load(f)

    # Optimization: also create a list of all artist names, this is so we do not
    # need to get the list from the lookup when doing fuzzymatching
    artists = []
    artist_lookup = {}
    yt_lookup = {}

    # For converting jp to romaiji
    kks = pykakasi.kakasi()

    for artist in filter(lambda v: v['type'] == 'vtuber', vbd['vtbs']):
        default_name_lang = artist['name']['default']
        default_name = artist['name'][default_name_lang]

        all_names: dict = artist['name']
        extras = all_names.pop('extra')
        names = list(all_names.values())
        names.extend(extras)
        names.remove(default_name)
        names.remove(default_name_lang)

        if 'jp' in all_names and 'en' not in all_names:
            romaiji_words = kks.convert(all_names['jp'])
            romaiji_name = ' '.join(w['hepburn'] for w in romaiji_words)
            names.append(romaiji_name)

        created_artist = ArtistMetadata(
            name=default_name,
            alternative_names=names,
            accounts=[ArtistAccount(**a) for a in artist['accounts']],
        )

        for acc in created_artist.accounts:
            if acc.platform == 'youtube':
                yt_lookup[acc.id] = created_artist

        artists.append(default_name)
        artist_lookup[default_name] = created_artist

        for name in names:
            artists.append(name)
            artist_lookup[name] = created_artist

    return artists, artist_lookup, yt_lookup
