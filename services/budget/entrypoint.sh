#!/bin/bash
set -e

DB_HOST="${POSTGRES_HOST}"
DB_PORT="${POSTGRES_PORT}"
DB_USER="${POSTGRES_USER}"
DB_PASS="${POSTGRES_PASSWORD}"
DB_NAME="${POSTGRES_DB_NAME}"

echo "Waiting for database at $DB_HOST:$DB_PORT..."

# Wait for the database to be ready
/app/shared/healthcheck.sh  "$DB_HOST" "$DB_PORT" "$DB_USER" "$DB_PASS" "$DB_NAME"

echo "Database is ready. Running migrations..."

# Run migrations
alembic upgrade head

echo "Migrations complete. Starting FastAPI application..."

# Start the FastAPI application
if [ "$ENV" = "production" ]; then
  exec uvicorn main:app --host 0.0.0.0 --port 8000
else
  exec uvicorn main:app --host 0.0.0.0 --port 8000 --reload
fi
