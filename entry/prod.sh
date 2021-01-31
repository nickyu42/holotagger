#!/bin/sh

uvicorn src.main:create_app --factory --uds /opt/holotagger/uvicorn.sock
