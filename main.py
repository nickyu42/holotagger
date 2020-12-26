import logging
import sys
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from metadata import get_metadata, YoutubeAPI, load_artists

logger = logging.getLogger('dl')

handler = logging.StreamHandler(sys.stdout)
handler.setLevel(logging.DEBUG)
logger.addHandler(handler)


class MetadataRequest(BaseModel):
    video_id: str


def create_app():
    YoutubeAPI.init()

    artists, artists_lookup = load_artists(Path('artists.yaml'))

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

    return app
