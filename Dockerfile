FROM python:3.9.1-alpine

ENV PYTHONUNBUFFERED 1

RUN mkdir /code
WORKDIR /code

# Install gcc.
RUN apk add --no-cache --virtual .build-deps gcc musl-dev

# Copy all our files into the image.
COPY requirements.txt requirements.txt

ENV PATH="/root/.local/bin:${PATH}"

# Install our requirements and remove build dependencies
RUN pip install --no-cache-dir -Ur requirements.txt \
    && apk del .build-deps

COPY . /code/

# Specify the command to run when the image is run.
CMD ["/code/entry/prod.sh"]