#!/bin/sh

uvicorn src.main:create_app --factory --port 80
