import asyncio
import uuid
from typing import Any

from src.dependencies import jobs
from src.download import download_worker
from src.schemas import Status


async def start_download(executor: Any, uid: uuid.UUID, *args) -> None:
    loop = asyncio.get_event_loop()
    job = jobs[uid]
    job.status = Status.DOWNLOADING
    await job.notify()
    try:
        await loop.run_in_executor(executor, download_worker, *args)
    except:  # noqa
        job.status = Status.ERROR
        await job.notify()
        return

    job.status = Status.DONE
    await job.notify()