import asyncio
import logging
import time
import uuid
from pathlib import Path
from typing import Any
from typing import List, Optional

import yt_dlp
from slugify import slugify
from sqlalchemy.orm import Session

import src.settings as settings
from src.db import add_song
from src.dependencies import engine, jobs
from src.metadata import add_metadata, force_mp3
from src.schemas import DownloadJob, SongMetadataForDownload, Status

logger = logging.getLogger(__name__)


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


def download_and_tag(
    storage_dir: Path, 
    url: str, 
    meta: SongMetadataForDownload, 
    db_engine: Any, 
    job: DownloadJob,
    hooks: Optional[list] = None,
):
    if hooks is None:
        hooks = []

    out_dir = storage_dir / meta.album

    # TODO: replace this with a more elegant solution.
    #   E.g. replace slashes in the name
    stored_song_name = slugify(meta.title)

    # Step 1: Download song
    ydl_options = init_ydl_options(out_dir, stored_song_name, hooks)
    with yt_dlp.YoutubeDL(ydl_options) as ydl:
        ydl.download([url])

    # HACK: force 100 if ytd does not fire final hook
    if job.percentage_done < 1.0:
        job.percentage_done = 1.0

    # Step 2: Add metadata to song
    try:
        # XXX: glob for downloaded file, the caller should ensure that
        #   there is no existing song with the same title
        song_path = next(out_dir.glob(f'{stored_song_name}.*'))
    except StopIteration:
        raise RuntimeError('Missing downloaded file')

    song_path = force_mp3(song_path)

    add_metadata(song_path, meta, meta.thumbnail_url)

    # Step 3: Add song info to persistence
    # Note: weirdly enough SQLAlchemy 1.3 does not work with the session context manager
    #       using `with Session(engine)` results in an AttributeError, that's why the
    #       session is created manually.
    s = Session(db_engine)
    try:
        add_song(s, meta, song_path)
    except Exception as e:  # noqa
        logger.error(e)
        s.rollback()
        raise
    s.close()


def create_download_hook(job: DownloadJob):
    def download_hook(response):
        loop = asyncio.get_event_loop()

        if response['status'] == 'finished' or response['total_bytes'] == response['downloaded_bytes']:
            job.status = Status.CONVERTING
            loop.run_until_complete(job.notify())
            return

        total_bytes = response['total_bytes']
        downloaded_bytes = response['downloaded_bytes']
        job.percentage_done = downloaded_bytes / total_bytes
        job.last_update = time.time()

        loop.run_until_complete(job.notify())

    return download_hook


def download_worker(req: SongMetadataForDownload, job: DownloadJob):
    """
    Synchronous CPU-bound download job.
    This should be run in a separate thread/process.
    """
    # Create new asyncio event loop, in case threading is used
    asyncio.set_event_loop(asyncio.new_event_loop())

    download_hook = create_download_hook(job)

    logger.info('Worker %s starting %s', job.request_id, req.title)
    url = f'http://youtube.com/watch?v={req.video_id}'
    download_and_tag(settings.SONGS_STORAGE, url, req, engine, job, hooks=[download_hook])


async def start_download(executor: Any, uid: uuid.UUID, req) -> None:
    loop = asyncio.get_event_loop()
    job = jobs[uid]
    job.status = Status.DOWNLOADING

    logger.debug('Starting download job, job=%s', id(job))

    await job.notify()
    try:
        await loop.run_in_executor(executor, download_worker, req, job)
    except Exception as e:  # noqa
        logger.error(e, exc_info=True)
        job.status = Status.ERROR
    else:
        logger.debug('Job finished, job=%s', id(job))
        job.status = Status.DONE
    finally:
        await job.notify()
