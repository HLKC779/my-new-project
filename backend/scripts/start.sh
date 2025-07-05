#!/bin/bash
set -e

# Wait for the database to be ready
echo "Waiting for PostgreSQL to be ready..."
until PGPASSWORD=$POSTGRES_PASSWORD psql -h "$POSTGRES_HOST" -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c '\q' >/dev/null 2>&1; do
  echo "PostgreSQL is unavailable - sleeping"
  sleep 1
done

echo "PostgreSQL is up - continuing"

# Run database migrations
echo "Running database migrations..."
alembic upgrade head

# Initialize the database if needed
echo "Initializing database..."
python -c "from app.db.base import init_db; init_db()"

# Start the application
echo "Starting application..."
exec "$@"
