import logging
import multiprocessing
from enum import Enum
from pathlib import Path
from typing import List, Any, Optional

import youtube_dl
from sqlalchemy.orm import Session

import settings
from db import add_song, db
from metadata import SongMetadata, add_metadata, force_mp3

logger = logging.getLogger(__name__)


class Status(Enum):
    WAITING = 'waiting'
    DOWNLOADING = 'downloading'
    DONE = 'done'
    ERROR = 'error'


def init_ydl_options(output_dir: Path, song_title: str, hooks: list) -> dict:
    return {
        'format': 'bestaudio/best',
        # XXX: If the outputted codec is not mp3
        #   we do two ffmpeg steps
        # The supported formats are:
        # - MP3 audio in MP3/WAV container
        # - PCM audio in WAV container
        # - AAC audio in MOV container
        # - FLAC audio
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '0',
        }],
        'logger': logger,
        'progress_hooks': hooks,
        'outtmpl': f'{output_dir.resolve()}/{song_title}.%(ext)s',
    }


def download_song(urls: List[str], ydl_options: dict):
    with youtube_dl.YoutubeDL(ydl_options) as ydl:
        ydl.download(urls)


def download_and_tag(storage_dir: Path, url: str, meta: SongMetadata, db_engine: Any, hooks: Optional[list] = None):
    if hooks is None:
        hooks = []

    out_dir = storage_dir / meta.album

    # Step 1: Download song
    ydl_options = init_ydl_options(out_dir, meta.title, hooks)
    download_song([url], ydl_options)

    # Step 2: Add metadata to song
    try:
        # XXX: glob for downloaded file, the caller should ensure that
        #   there is no existing song with the same title
        song_path = next(out_dir.glob(f'{meta.title}.*'))
    except StopIteration:
        raise RuntimeError('Missing downloaded file')

    song_path = force_mp3(song_path)

    # TODO: remove hardcoded cover
    add_metadata(song_path, meta,
                 'https://i1.sndcdn.com/avatars-32EHFzqYhcwAzmuk-mE2q0g-t500x500.jpg')

    # Step 3: Add song info to persistence
    # Note: weirdly enough SQLAlchemy 1.3 does not work with the session context manager
    #       using `with Session(engine)` results in an AttributeError]
    s = Session(db_engine)
    try:
        add_song(s, meta, song_path)
    except:  # noqa
        s.rollback()
        raise
    s.close()


def download_worker(req: SongMetadata):
    logging.info(f'Worker started on {req.title}')
    url = f'http://youtube.com/watch?v={req.video_id}'
    download_and_tag(settings.SONGS_STORAGE, url, req, db, [])
