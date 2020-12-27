import logging
import queue
import sys
import uuid
from enum import Enum
from pathlib import Path
from uuid import UUID

import cachetools
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from db import init
from metadata import get_metadata, YoutubeAPI, load_artists, SongMetadata

SONGS_STORAGE = 'data/songs'
DB_NAME = 'data/db.sqlite'
ARTISTS = 'data/artists.yaml'

logger = logging.getLogger('dl')

handler = logging.StreamHandler(sys.stdout)
handler.setLevel(logging.DEBUG)
logger.addHandler(handler)


class MetadataRequest(BaseModel):
    video_id: str


class DownloadRequest(BaseModel):
    meta: SongMetadata
    video_id: str


def create_app():
    YoutubeAPI.init()

    artists, artists_lookup = load_artists(Path(ARTISTS))
    download_queue = queue.Queue()

    db_engine = init(DB_NAME)

    # key value store where the key is the uuid of the request
    # and the value is the 0 to 100 of the download progress
    # -1 indicates that an error has occurred during downloading
    status_cache = cachetools.TTLCache(10_000, 30 * 60)

    app = FastAPI()

    app.add_middleware(
        CORSMiddleware,
        allow_credentials=True,
        allow_origins=['*'],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get('/')
    async def root():
        return {'status': 'ready'}

    @app.post('/metadata')
    async def metadata(req: MetadataRequest):
        meta = get_metadata(req.video_id, artists_lookup, artists)
        return meta.serialize()

    @app.post('/download')
    async def download(req: DownloadRequest):
        # # XXX: Maybe insecure, check if URL is valid youtube url
        # url = f'youtube.com/watch?v={req.video_id}'
        uuid_ = uuid.UUID()
        status_cache[uuid_] = 0
        download_queue.put((req, uuid_))

        return {'request_id': uuid_}

    @app.websocket('/status/{request_id}')
    async def download_status():
        return

    return app
