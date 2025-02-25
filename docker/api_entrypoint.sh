#!/bin/bash
set -e

# Enable better error reporting
trap "echo \"An error occurred. Exiting...\" >&2" ERR

# Wait for database to be ready
echo "Waiting for database to be ready..."
while ! pg_isready -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -t 1; do
  echo "Waiting for database connection..."
  sleep 2
done
echo "Database is ready!"

# Start the API service
echo "Starting ZMap Scanner API..."
cd /app
exec uvicorn api.app:app --host 0.0.0.0 --port "${API_PORT:-8000}" --workers 2