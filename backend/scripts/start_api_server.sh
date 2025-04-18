#!/bin/bash
alembic upgrade head && \
echo "Starting Api Server" && \
uvicorn onyx.main:app --host 0.0.0.0 --port 8080