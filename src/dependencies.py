import cachetools
import uuid
from typing import TYPE_CHECKING

from sqlalchemy.orm import sessionmaker, Session

from src import settings
from src.db import init

from src.metadata import load_artists
from src.settings import ARTISTS, DOWNLOAD_REQUEST_TTL

if TYPE_CHECKING:
    # Prevent circular import
    from src.schemas import DownloadJob

# Setup download necessities
artists, artists_lookup = load_artists(ARTISTS)
jobs: cachetools.TTLCache[uuid.UUID, 'DownloadJob'] = cachetools.TTLCache(1_000, DOWNLOAD_REQUEST_TTL)

engine = init(settings.DB)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Session:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
