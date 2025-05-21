#!/bin/bash
set -e

echo "Waiting for PostgreSQL to be ready..."
until pg_isready -h "$POSTGRES_HOST" -p "$POSTGRES_PORT" -U "$POSTGRES_USER"; do
  echo "PostgreSQL is unavailable, waiting..."
  sleep 1
done


ORIGINAL_DIR=$(pwd)
cd /usr/local/lib/python3.13/site-packages/flux_orm/
alembic upgrade head
cd "$ORIGINAL_DIR"
echo "Alembic migrations completed."

echo "Starting the main process..."
exec "$@"