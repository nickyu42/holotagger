FROM node:15.8-alpine as builder

RUN mkdir -p /code/app
WORKDIR /code/app

COPY app /code

# Build bundle.js
RUN npm install
RUN npm run prod

FROM python:3.9.1-alpine

ENV PYTHONUNBUFFERED 1

RUN mkdir /code
WORKDIR /code

# Install gcc and ffmpeg
RUN apk add --no-cache ffmpeg
RUN apk add --no-cache --virtual .build-deps gcc musl-dev 

# Copy all our files into the image.
COPY requirements.txt requirements.txt

ENV PATH="/root/.local/bin:${PATH}"

# Install our requirements and remove build dependencies
RUN pip install --no-cache-dir -Ur requirements.txt \
    && apk del .build-deps

# Copy entrypoint scripts
COPY entry /code/entry

# Copy static assets
COPY app/static /code/app/static
COPY app/templates /code/app/templates
COPY --from=builder /code/static/bundle.js /code/app/static/bundle.js

EXPOSE 80

# Copy code
COPY src /code/src

# Specify the command to run when the image is run.
CMD ["/code/entry/prod.sh"]