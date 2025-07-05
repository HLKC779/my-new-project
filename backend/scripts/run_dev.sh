#!/bin/bash
set -e

# Set environment variables for development
export ENVIRONMENT=development
export LOG_LEVEL=DEBUG
export DEBUG=True

# Install development dependencies
echo "Installing development dependencies..."
pip install -r requirements-dev.txt

# Install the package in development mode
echo "Installing package in development mode..."
pip install -e .

# Initialize the database
echo "Initializing database..."
python -c "from app.db.base import init_db; init_db()"

# Run database migrations
echo "Running database migrations..."
python -m alembic upgrade head

# Create necessary directories
mkdir -p uploads chroma_db

# Start the development server with auto-reload
echo "Starting development server..."
uvicorn app.main:app \
    --host 0.0.0.0 \
    --port 8000 \
    --reload \
    --reload-dir /app \
    --reload-include "*.py" \
    --log-level debug
