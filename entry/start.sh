#!/bin/sh

export DEBUG=true
uvicorn src.main:create_app --factory --debug --port 8000
