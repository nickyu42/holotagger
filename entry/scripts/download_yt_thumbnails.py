#!/bin/env python
import sys
import os
from pathlib import Path
from urllib import request

import slugify
from dotenv import load_dotenv

sys.path.append(os.getcwd())
from src.metadata import load_artists, YoutubeAPI

load_dotenv('.env')
artists, _ = load_artists(Path('data/artists/artists.yaml'))

YoutubeAPI.init()

channels = YoutubeAPI.channel_info([a.yt_id for a in artists])

for ch in channels:
    artist = next(a for a in artists if a.yt_id == ch.id)

    thumbnail_url = ch.snippet.thumbnails['high']['url']

    with request.urlopen(thumbnail_url) as response:
        subtype = response.info().get_content_subtype()

        print(f'{slugify.slugify(artist.name)}.{subtype}')
        with open(f'data/artists/covers/{slugify.slugify(artist.name)}.{subtype}', 'wb') as f:
            f.write(response.read())
