import logging
import sys
import urllib.parse as urlparse

from fastapi import FastAPI

from metadata import YoutubeAPI

logger = logging.Logger('dl')

handler = logging.StreamHandler(sys.stdout)
handler.setLevel(logging.DEBUG)
logger.addHandler(handler)


def create_app():
    YoutubeAPI.init()

    app = FastAPI()

    @app.get('/')
    async def root():
        return {'message': 'Hello World'}

    @app.get('/info/{video_id}')
    async def info(video_id: str):
        return YoutubeAPI.video_info([video_id])[0]

    return app
