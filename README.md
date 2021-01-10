# HoloTagger

![version](https://img.shields.io/badge/version-0.0.1-brightgreen)

Web application for tagging and downloading karaoke covers sung by vtubers.  
Currently, supports Hololive members.

The application consists of an API and simple web interface.  
A firefox extension is planned for the future.

## Deployment

There are two entrypoint scripts:

- `entry/start.sh` for development, will run a http server on port 8000
- `entry/prod.sh` for running in a production environment, binds API to a unix socket at `/opt/holotagger/uvicorn.sock`

Deploying can be done using docker-compose.  
First create an `.env` in the root directory with:

```
YOUTUBE_DEVELOPER_KEY=<INSERT YOUR KEY>
```

Then run:

```console
docker-compose up -d
```

Production consists of a Nginx server that serves the static frontend in `app/web` and
also acts as a reverse proxy for the API.