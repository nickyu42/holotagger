import logging
import tempfile
from typing import List

import youtube_dl

logger = logging.Logger('dl')


def init_ydl_options() -> dict:
    temp_dir = tempfile.mkdtemp()

    return {
        'format': 'bestaudio/best',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '0',
        }],
        'logger': logger,
        'progress_hooks': [],
        'outtmpl': f'{temp_dir}/%(title)s.%(ext)s',
    }


def download_songs(urls: List[str], options: dict):
    with youtube_dl.YoutubeDL(options) as ydl:
        ydl.download(urls)
