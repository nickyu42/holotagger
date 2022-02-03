#!/bin/sh

uvicorn src.main:create_app \
  --factory \
  --port 80 \
  --host 0.0.0.0 \
  --proxy-headers \
  --forwarded-allow-ips "*" \
  --log-config entry/logging.conf
