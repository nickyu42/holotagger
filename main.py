import logging
import multiprocessing
import sys
import uuid
from typing import List

import cachetools
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from db import db
from download import init_download_workers
from metadata import get_metadata, YoutubeAPI, load_artists, SongMetadata
from settings import ARTISTS

logger = logging.getLogger(__name__)

handler = logging.StreamHandler(sys.stdout)
handler.setLevel(logging.DEBUG)
logger.addHandler(handler)


class MetadataRequest(BaseModel):
    video_id: str


class DownloadRequest(BaseModel):
    meta: SongMetadata
    video_id: str


def create_app():
    download_workers: List[multiprocessing.Process] = []
    artists, artists_lookup = load_artists(ARTISTS)
    download_queue = multiprocessing.Queue()

    # key value store where the key is the uuid of the request
    # and the value is the 0 to 100 of the download progress
    # -1 indicates that an error has occurred during downloading
    status_cache = cachetools.TTLCache(10_000, 30 * 60)

    app = FastAPI()

    @app.on_event('startup')
    def startup():
        YoutubeAPI.init()
        download_workers.extend(init_download_workers(download_queue, status_cache))

    @app.on_event('shutdown')
    def shutdown():
        download_queue.close()
        for w in download_workers:
            w.close()

        db.close()

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
        uuid_ = uuid.uuid4().hex
        status_cache[uuid_] = 0
        download_queue.put((req, uuid_))

        return {'request_id': uuid_}

    @app.websocket('/status/{request_id}')
    async def download_status():
        return

    return app
