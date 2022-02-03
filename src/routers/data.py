from typing import List, Optional

import slugify
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from starlette.responses import FileResponse

from src import schemas
from src.db import get_songs, Artist
from src.dependencies import get_db, artist_lookup, artist_names, yt_lookup
from src.metadata import get_metadata
from src.schemas import MetadataRequest, SongMetadata
from src.settings import COVER_DIR

router = APIRouter()


@router.get('/songs', response_model=List[schemas.Song])
def songs(limit: Optional[int] = None, db: Session = Depends(get_db)):
    """Get all tagged songs"""
    return [schemas.Song.from_orm(s) for s in get_songs(db, limit=limit)]


@router.get('/cover/{artist_id}')
async def cover(artist_id: int, db: Session = Depends(get_db)):
    """Get the cover art of an artist if it exists"""
    artist = db.query(Artist).get(artist_id)
    if artist is None:
        raise HTTPException(status_code=404, detail=f'Artist with artist_id {artist_id} not found')

    db.close()

    cover_path = COVER_DIR / f'{slugify.slugify(artist.name)}.jpg'
    if not cover_path.exists():
        raise HTTPException(status_code=404, detail=f'Artist with artist_id {artist_id} does not have a cover')

    return FileResponse(cover_path.resolve(), media_type='image/jpeg')


@router.get('/search/artist', response_model=schemas.Artist)
async def search_artist(name: str, db: Session = Depends(get_db)):
    # TODO: improve search query
    artist = db.query(Artist).filter(Artist.name.like(f'%{name}%')).first()

    if artist is None:
        raise HTTPException(status_code=404, detail=f'Artist with name {name} does not exist')

    return schemas.Artist.from_orm(artist)


@router.post('/metadata', response_model=SongMetadata)
def metadata(req: MetadataRequest):
    """Guess info about song from given Youtube video id"""
    meta = get_metadata(req.video_id, artist_names, artist_lookup, yt_lookup)
    return meta.dict()
