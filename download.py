import logging
from pathlib import Path
from typing import List, Any

import youtube_dl
from sqlalchemy.orm import Session

from db import add_song
from metadata import SongMetadata, add_metadata

logger = logging.getLogger('dl')


def init_ydl_options(output_dir: Path, song_title: str) -> dict:
    return {
        'format': 'bestaudio/best',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '0',
        }],
        'logger': logger,
        'progress_hooks': [],
        'outtmpl': f'{output_dir.resolve()}/{song_title}.mp3',
    }


def download_song(urls: List[str], ydl_options: dict):
    with youtube_dl.YoutubeDL(ydl_options) as ydl:
        ydl.download(urls)


def download_and_tag(storage_dir: Path, url: str, meta: SongMetadata, db_engine: Any):
    out_dir = storage_dir / meta.album

    # Step 1: Download song
    ydl_options = init_ydl_options(out_dir, meta.title)
    download_song([url], ydl_options)

    # Step 2: Add metadata to song
    song_path = Path(ydl_options['outtmpl'])
    # TODO: remove hardcoded cover
    add_metadata(song_path, meta, Path('./data/thumbnail.jpg'))

    # Step 3: Add song info to persistence
    s = Session(db_engine)
    # Note: weirdly enough SQLAlchemy 1.3 does not work with the session context manager
    #       using `with Session(engine)` results in an AttributeError
    try:
        add_song(s, meta, song_path)
    except:  # noqa
        s.rollback()
        raise
    s.close()
