import logging
import sys
from concurrent.futures.process import ProcessPoolExecutor
from datetime import timezone

from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from starlette.requests import Request
from starlette.responses import HTMLResponse
from starlette.staticfiles import StaticFiles
from starlette.templating import Jinja2Templates

from src.db import get_songs
from src.dependencies import engine, get_db
from src.metadata import YoutubeAPI
from src.routers import data, download
from src.settings import VERSION, API_URL


def create_app() -> FastAPI:
    app = FastAPI(
        version=VERSION,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_credentials=True,
        allow_origins=['*'],
        allow_methods=['*'],
        allow_headers=['*'],
    )

    app.mount('/static', StaticFiles(directory='app/static'), name='static')
    templates = Jinja2Templates(directory='app/templates')

    @app.on_event('startup')
    def startup():
        YoutubeAPI.init()
        app.state.executor = ProcessPoolExecutor()

    @app.on_event('shutdown')
    def shutdown_event():
        app.state.executor.shutdown()
        engine.close()

    @app.get('/', response_class=HTMLResponse)
    async def index(request: Request, db: Session = Depends(get_db)):
        songs = get_songs(db)
        ctx = {
            'request': request,
            'api_url': API_URL,
            'songs': songs,
            'timezone': timezone,
        }
        return templates.TemplateResponse('index.html', ctx)

    app.include_router(data.router, prefix=API_URL)
    app.include_router(download.router, prefix=API_URL)

    return app
