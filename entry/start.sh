#!/bin/sh

export DEBUG=true
uvicorn main:create_app --factory --port 8000
