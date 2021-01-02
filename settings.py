import os
from pathlib import Path

from dotenv import load_dotenv

ROOT_PATH = Path('.')

# Load environment variables if they exist
if (ROOT_PATH / '.env').exists():
    load_dotenv(ROOT_PATH / '.env')

IS_DEBUG = os.environ.get('DEBUG', 'false').lower() == 'true'

# Data storage settings
SONGS_STORAGE = ROOT_PATH / 'data' / 'songs'
DB = ROOT_PATH / 'data' / 'db.sqlite'
ARTISTS = ROOT_PATH / 'data' / 'artists' / 'artists.yaml'
COVER_DIR = ROOT_PATH / 'data' / 'artists' / 'covers'

# The amount of seconds a download request should exist until timeout
DOWNLOAD_REQUEST_TTL = 10 * 60

# For getting video info
YOUTUBE_DEVELOPER_KEY = os.environ.get('YOUTUBE_DEVELOPER_KEY')
