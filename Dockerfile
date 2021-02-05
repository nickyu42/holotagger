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

# Copy code
COPY src /code/src

# Specify the command to run when the image is run.
CMD ["/code/entry/prod.sh"]