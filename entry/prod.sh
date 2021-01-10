#!/bin/sh

mkdir /opt/holotagger
uvicorn main:create_app --factory --uds /opt/holotagger/uvicorn.sock
