#!/bin/sh

export DEBUG=true
uvicorn src.main:create_app --log-config entry/logging.conf --factory --debug --port 8000
