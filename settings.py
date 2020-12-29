from pathlib import Path

SONGS_STORAGE = Path('data/songs')
DB = Path('data/db.sqlite')
ARTISTS = Path('data/artists.yaml')

REDIS_HOST = 'localhost'
REDIS_PORT = 6379

# The amount of seconds a download request should exist until timeout
DOWNLOAD_REQUEST_TTL = 10 * 60
