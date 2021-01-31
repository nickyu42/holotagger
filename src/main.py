import logging
import sys
from concurrent.futures.process import ProcessPoolExecutor

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.dependencies import engine
from src.metadata import YoutubeAPI
from src.routers import data, download
from src.settings import VERSION, ROOT_URL


def create_app() -> FastAPI:
    # Setup logging
    logger = logging.getLogger(__name__)

    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.DEBUG)
    logger.addHandler(handler)

    app = FastAPI(
        root_path=ROOT_URL,
        version=VERSION,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_credentials=True,
        allow_origins=['*'],
        allow_methods=['*'],
        allow_headers=['*'],
    )

    @app.on_event('startup')
    def startup():
        YoutubeAPI.init()
        app.state.executor = ProcessPoolExecutor()

    @app.on_event('shutdown')
    def shutdown_event():
        app.state.executor.shutdown()
        engine.close()

    @app.get('/')
    async def root():
        return {'status': 'ready'}

    app.include_router(data.router)
    app.include_router(download.router)

    return app
