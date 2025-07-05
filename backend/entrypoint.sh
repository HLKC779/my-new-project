#!/bin/sh
set -e

# If the command is 'python', run the startup script
if [ "$1" = 'python' ] || [ "$1" = 'gunicorn' ]; then
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

    # Create necessary directories
    mkdir -p /data/uploads /data/chroma_db
    chown -R appuser:appuser /data
fi

exec "$@"
