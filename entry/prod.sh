#!/bin/sh

uvicorn main:create_app --factory --uds /opt/holotagger/uvicorn.sock
