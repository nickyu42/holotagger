import asyncio
import logging
import multiprocessing
import sys
import uuid
import time
from concurrent.futures.process import ProcessPoolExecutor
from typing import List, Optional, Callable
from http import HTTPStatus

import cachetools
import redis
from fastapi import FastAPI, WebSocket, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, PrivateAttr
from sqlalchemy.orm import Session

from db import db, get_songs, Song
from download import Status, download_worker
from metadata import get_metadata, YoutubeAPI, load_artists, SongMetadata
from settings import ARTISTS, REDIS_PORT, REDIS_HOST, DOWNLOAD_REQUEST_TTL


class MetadataRequest(BaseModel):
    video_id: str


class DownloadJob(BaseModel):
    request_id: uuid.UUID
    status: Status

    _observers: List[Callable] = PrivateAttr(default_factory=list)

    async def notify(self):
        for o in self._observers:
            await o(self)

    def listen(self, o: Callable):
        self._observers.append(o)

    class Config:
        use_enum_values = True


def create_app():
    # Setup logging
    logger = logging.getLogger(__name__)

    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.DEBUG)
    logger.addHandler(handler)

    # Setup download necessities
    artists, artists_lookup = load_artists(ARTISTS)
    jobs: cachetools.TTLCache[uuid.UUID, DownloadJob] = \
        cachetools.TTLCache(1_000, 10 * 60)

    app = FastAPI()

    app.add_middleware(
        CORSMiddleware,
        allow_credentials=True,
        allow_origins=['*'],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    async def start_download(uid: uuid.UUID, *args) -> None:
        loop = asyncio.get_event_loop()
        job = jobs[uid]
        job.status = Status.DOWNLOADING
        await job.notify()
        try:
            await loop.run_in_executor(app.state.executor, download_worker, *args)
        except:
            job.status = Status.ERROR
            await job.notify()
            return
        
        job.status = Status.DONE
        await job.notify()

    @app.on_event('startup')
    def startup():
        YoutubeAPI.init()
        app.state.executor = ProcessPoolExecutor()

    @app.on_event('shutdown')
    def shutdown_event():
        app.state.executor.shutdown()
        db.close()

    @app.get('/')
    async def root():
        return {'status': 'ready'}

    @app.post('/metadata', response_model=SongMetadata)
    def metadata(req: MetadataRequest):
        """Guess info about song from given youtube video id"""
        meta = get_metadata(req.video_id, artists_lookup, artists)
        return meta.dict()

    @app.get('/songs', response_model=List[Song.Model])
    def songs(limit: Optional[int] = None):
        s = Session(db)
        try:
            return [s.to_model() for s in get_songs(s, limit=limit)]
        except:  # noqa
            s.rollback()
            raise
        finally:
            s.close()

    @app.post('/download', response_model=DownloadJob, status_code=HTTPStatus.ACCEPTED)
    def download(req: SongMetadata, background_tasks: BackgroundTasks):
        """
        Start download of song with given metadata in the background.
        """
        uid = uuid.uuid4()
        jobs[uid] = DownloadJob(request_id=uid, status=Status.WAITING)
        background_tasks.add_task(start_download, uid, req)

        return jobs[uid].dict()

    @app.get('/status/{uid}', response_model=DownloadJob)
    async def status(uid: uuid.UUID):
        """Get status on download job"""
        if uid not in jobs:
            return HTTPException(status_code=404, detail='Job with uid not found')

        return jobs[uid].dict()

    @app.websocket('/status/ws/{uid}')
    async def status_ws(uid: uuid.UUID, ws: WebSocket):
        await ws.accept()

        async def notifier(job):
            await ws.send_text(job.json())

        start = time.time()
        job = jobs[uid]
        job.listen(notifier)

        await ws.send_text(job.json())

        while (job.status == Status.DOWNLOADING or job.status == Status.WAITING) and time.time() - start <= 30:
            await asyncio.sleep(0.1)

        await ws.close()

    return app
