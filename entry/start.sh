#!/bin/sh

export DEBUG=true
uvicorn main:create_app --factory --debug --port 8000
