import logging
import multiprocessing
from pathlib import Path
from typing import List, Any, Callable, Optional

import youtube_dl
from cachetools import TTLCache
from sqlalchemy.orm import Session

import settings
from db import add_song, db
from metadata import SongMetadata, add_metadata

logger = logging.getLogger(__name__)


def init_ydl_options(output_dir: Path, song_title: str, hooks: Optional[list] = None) -> dict:
    if hooks is None:
        hooks = []

    return {
        'format': 'bestaudio/best',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '0',
        }],
        'logger': logger,
        'progress_hooks': hooks,
        'outtmpl': f'{output_dir.resolve()}/{song_title}.mp3',
    }


def download_song(urls: List[str], ydl_options: dict):
    with youtube_dl.YoutubeDL(ydl_options) as ydl:
        ydl.download(urls)


def download_and_tag(storage_dir: Path, url: str, meta: SongMetadata, db_engine: Any, hooks: Optional[list] = None):
    out_dir = storage_dir / meta.album

    # Step 1: Download song
    ydl_options = init_ydl_options(out_dir, meta.title, hooks)
    download_song([url], ydl_options)

    # Step 2: Add metadata to song
    song_path = Path(ydl_options['outtmpl'])
    # TODO: remove hardcoded cover
    add_metadata(song_path, meta, Path('./data/thumbnail.jpg'))

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


def download_worker(q: multiprocessing.Queue, cache: TTLCache, storage: Path):
    db.dispose()

    while True:
        req, uuid = q.get()
        print(f'Worker started on {uuid}')

        # XXX: Maybe insecure, add check if url is valid youtube url
        url = f'http://youtube.com/watch?v={req.video_id}'

        # function that updates the status of the download in the cache
        def progress_hook(d: dict):
            if d['status'] == 'finished':
                cache[uuid] = 100
            elif d['status'] == 'downloading' and 'downloaded_bytes' in d and 'total_bytes' in d:
                cache[uuid] = 100 * d['downloaded_bytes'] / d['total_bytes']
            elif d['status'] == 'error':
                cache[uuid] = -1

        download_and_tag(storage, url, req.meta, db, [progress_hook])


def init_download_workers(q: multiprocessing.Queue, cache: TTLCache, num_workers: int = 3) -> list:
    workers = []

    for i in range(num_workers):
        logger.info(f'Started worker {i}')
        p = multiprocessing.Process(target=download_worker, args=(q, cache, settings.SONGS_STORAGE))
        p.start()
        workers.append(p)

    return workers
