import datetime
import logging
import uuid
from enum import Enum
from typing import Callable, List, Optional

from pydantic import BaseModel, PrivateAttr, validator
from sqlalchemy.orm import Query

logger = logging.getLogger(__name__)


class OrmBase(BaseModel):
    id: int

    # Pre-processing validator that evaluates lazy relationships before any other validation
    # NOTE: If high throughput/performance is a concern, you can/should probably apply
    #       this validator in a more targeted fashion instead of a wildcard in a base class.
    #       This approach is by no means slow, but adds a minor amount of overhead for every field
    @validator("*", pre=True)
    def evaluate_lazy_columns(cls, v):
        if isinstance(v, Query):
            return v.all()
        return v

    class Config:
        orm_mode = True


class Status(Enum):
    WAITING = 'waiting'
    DOWNLOADING = 'downloading'
    DONE = 'done'
    ERROR = 'error'


class DownloadJob(BaseModel):
    request_id: uuid.UUID
    status: Status
    percentage_done: float
    last_update: float

    _observers: List[Callable] = PrivateAttr(default_factory=list)

    async def notify(self):
        for o in self._observers:
            await o(self)

    def listen(self, o: Callable):
        logger.debug('Added listener to job %s', self)
        self._observers.append(o)

    def remove_observer(self, o: Callable):
        if o in self._observers:
            self._observers.remove(o)

    class Config:
        use_enum_values = True


class MetadataRequest(BaseModel):
    video_id: str


class Tagger(OrmBase):
    name: str


class Album(OrmBase):
    name: str


class Artist(OrmBase):
    name: str
    yt_id: Optional[str]


class Song(OrmBase):
    title: str
    tagger: Optional[Tagger]
    album: Optional[Album]
    artists: List[Artist]
    original_artists: List[str]
    created_date: datetime.datetime


class SongMetadata(BaseModel):
    # Embedded metadata
    title: str
    artists: List[str]
    album: str
    original_artists: List[str]

    # Other metadata
    video_id: str
    tagger: Optional[str]
    thumbnail_url: Optional[str]


class ArtistMetadata(BaseModel):
    name: str
    fuzzy_names: List[str]
    yt_id: str
