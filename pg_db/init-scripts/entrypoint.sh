#!/bin/bash
set -e

echo "Waiting for PostgreSQL to be ready..."
until pg_isready -h "$POSTGRES_HOST" -p "$POSTGRES_PORT" -U "$POSTGRES_USER"; do
  echo "PostgreSQL is unavailable, waiting..."
  sleep 1
done

echo "Checking for tables in the database..."
# Check if there is at least one table in the public schema
TABLE_COUNT=$(PGPASSWORD="$POSTGRES_PASSWORD" psql -h "$POSTGRES_HOST" -p "$POSTGRES_PORT" -U "$POSTGRES_USER" -d "$POSTGRES_DB" -tAc "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public';")

# Remove spaces from the result
TABLE_COUNT=$(echo "$TABLE_COUNT" | xargs)

if [ "$TABLE_COUNT" -eq 0 ]; then
  echo "No tables found. Running Alembic migrations..."
  ORIGINAL_DIR=$(pwd)
  cd /usr/local/lib/python3.13/site-packages/flux_orm/psql_database/
  alembic upgrade head
  cd "$ORIGINAL_DIR"
  echo "Alembic migrations completed."
else
  echo "Tables already exist (found $TABLE_COUNT tables). Skipping migrations."
fi

echo "Starting the main process..."
exec "$@"