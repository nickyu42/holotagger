import asyncio
import logging
import multiprocessing
import sys
import uuid
from typing import List

import cachetools
import redis
from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from db import db
from download import init_download_workers, Status
from metadata import get_metadata, YoutubeAPI, load_artists, SongMetadata
from settings import ARTISTS, REDIS_PORT, REDIS_HOST, DOWNLOAD_REQUEST_TTL


class MetadataRequest(BaseModel):
    video_id: str


class DownloadResponse(BaseModel):
    request_id: str


def create_app():
    # Setup logging
    logger = logging.getLogger(__name__)

    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.DEBUG)
    logger.addHandler(handler)

    # Setup download necessities
    download_workers: List[multiprocessing.Process] = []
    artists, artists_lookup = load_artists(ARTISTS)
    download_queue = multiprocessing.Queue()

    r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)

    app = FastAPI()

    app.add_middleware(
        CORSMiddleware,
        allow_credentials=True,
        allow_origins=['*'],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.on_event('startup')
    def startup():
        YoutubeAPI.init()
        download_workers.extend(init_download_workers(download_queue))

    @app.on_event('shutdown')
    def shutdown():
        download_queue.close()
        for w in download_workers:
            w.close()

        db.close()

    @app.get('/')
    async def root():
        return {'status': 'ready'}

    @app.post('/metadata', response_model=SongMetadata)
    def metadata(req: MetadataRequest):
        meta = get_metadata(req.video_id, artists_lookup, artists)
        return meta.dict()

    @app.post('/download', response_model=DownloadResponse)
    def download(req: SongMetadata):
        uuid_ = uuid.uuid4().hex
        r.set(uuid_, Status.WAITING)
        r.expire(uuid_, DOWNLOAD_REQUEST_TTL)
        download_queue.put((req, uuid_))

        return {'request_id': uuid_}

    @app.websocket('/status/{request_id}')
    async def download_status(websocket: WebSocket, request_id: str):
        await websocket.accept()

        status = r.get(request_id)
        if status is None:
            await websocket.close()
            return

        while status == Status.WAITING:
            await websocket.send_json({'status': Status.WAITING})
            await asyncio.sleep(0.1)
            status = r.get(request_id)

        p = r.pubsub()
        p.subscribe(request_id)

        while status == Status.DOWNLOADING:
            percentage = p.get_message(timeout=1.0)['data']
            await websocket.send_json({'status': Status.DOWNLOADING, 'percentage': percentage})
            status = r.get(request_id)

        await websocket.send_json({'status': str(status)})
        await websocket.close()

    return app
