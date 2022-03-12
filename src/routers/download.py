import asyncio
import copy
import time
import uuid
from http import HTTPStatus

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from starlette.background import BackgroundTasks
from starlette.requests import Request
from starlette.responses import FileResponse
from starlette.websockets import WebSocket, WebSocketState

from src.db import Song
from src.dependencies import get_db, jobs
from src.schemas import DownloadJob, Status, SongMetadata
from src.tasks.download import start_download

router = APIRouter()


@router.get('/download/{song_id}')
def download(song_id: int, db: Session = Depends(get_db)):
    """Download stored song with given id"""
    song = db.query(Song).get(song_id)
    if song is None:
        raise HTTPException(status_code=404, detail=f'Song with song_id {song_id} not found')

    # Append .mp3 to the filename, if we do not append a file extension
    # and the song title would happen to have a period in it, the browser would
    # assume that it does and replace the 'incorrect' extension with the content-type
    # e.g. this would happen "LOVE SPACE ver. Enna Alouette" -> "LOVE SPACE ver.mp3"
    return FileResponse(song.filepath, filename=f'{song.title}.mp3', media_type='audio/mp3')


@router.get('/status/{uid}', response_model=DownloadJob)
async def status(uid: uuid.UUID):
    """Get status on download job"""
    if uid not in jobs:
        return HTTPException(status_code=404, detail=f'Job with uid {uid} not found')

    return jobs[uid].dict()


@router.post('/convert', response_model=DownloadJob, status_code=HTTPStatus.ACCEPTED)
def convert(req: SongMetadata, background_tasks: BackgroundTasks, request: Request):
    """Start download and conversion of song with given metadata in the background"""
    uid = uuid.uuid4()
    jobs[uid] = DownloadJob(request_id=uid, status=Status.WAITING, percentage_done=0.0, last_update=time.time())
    background_tasks.add_task(start_download, request.app.state.executor, uid, req)

    return jobs[uid].dict()


@router.websocket('/status/ws/{uid}')
async def status_ws(uid: uuid.UUID, ws: WebSocket):
    await ws.accept()

    closing_ws = False

    async def notifier(j: DownloadJob):
        nonlocal closing_ws

        if closing_ws or ws.client_state != WebSocketState.CONNECTED:
            return

        await ws.send_text(j.json())

    job = jobs[uid]
    job.listen(notifier)

    await ws.send_text(job.json())

    while job.status != Status.DONE and job.status != Status.ERROR:
        # Send error on timeout
        if time.time() - job.last_update > 60:
            job.remove_observer(notifier)
            # copy job so we don't modify the original
            jc = copy.deepcopy(job)
            jc.status = Status.ERROR
            await ws.send_text(jc.json())
            break

        await asyncio.sleep(0.5)

    closing_ws = True
    await ws.close()
