#!/usr/bin/env python3
"""
Database migration script.
This script runs database migrations using Alembic.
"""
import os
import sys
import logging
from pathlib import Path

# Add the project root to the Python path
sys.path.append(str(Path(__file__).parent.parent))

from alembic.config import Config
from alembic import command
from app.core.config import settings

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def run_migrations() -> None:
    """Run database migrations."""
    logger.info("Running database migrations...")
    
    # Get the directory containing this script
    script_dir = Path(__file__).parent
    
    # Path to the alembic.ini file
    alembic_ini_path = script_dir.parent / "alembic.ini"
    
    # Path to the migrations directory
    migrations_dir = script_dir.parent / "alembic"
    
    # Create Alembic config
    alembic_cfg = Config(alembic_ini_path)
    
    # Set the script location
    alembic_cfg.set_main_option("script_location", str(migrations_dir))
    
    # Set the database URL
    alembic_cfg.set_main_option("sqlalchemy.url", settings.DATABASE_URL)
    
    try:
        # Run migrations
        command.upgrade(alembic_cfg, "head")
        logger.info("Database migrations completed successfully!")
    except Exception as e:
        logger.error(f"Error running migrations: {e}")
        sys.exit(1)

def create_migration(message: str = None) -> None:
    """Create a new migration."""
    if not message:
        logger.error("Please provide a message for the migration")
        sys.exit(1)
    
    logger.info(f"Creating new migration: {message}")
    
    # Get the directory containing this script
    script_dir = Path(__file__).parent
    
    # Path to the alembic.ini file
    alembic_ini_path = script_dir.parent / "alembic.ini"
    
    # Path to the migrations directory
    migrations_dir = script_dir.parent / "alembic"
    
    # Create Alembic config
    alembic_cfg = Config(alembic_ini_path)
    
    # Set the script location
    alembic_cfg.set_main_option("script_location", str(migrations_dir))
    
    # Set the database URL
    alembic_cfg.set_main_option("sqlalchemy.url", settings.DATABASE_URL)
    
    try:
        # Create a new migration
        command.revision(
            config=alembic_cfg,
            autogenerate=True,
            message=message,
            autogenerate_args={
                "tables": None,  # Autodiscover all tables
                "include_schemas": False,
                "include_name": lambda name, type_, parent_names: True,
            }
        )
        logger.info("Migration created successfully!")
    except Exception as e:
        logger.error(f"Error creating migration: {e}")
        sys.exit(1)

def main() -> None:
    """Handle command line arguments."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Database migration utility")
    subparsers = parser.add_subparsers(dest="command", help="Command to run")
    
    # Create the parser for the "migrate" command
    migrate_parser = subparsers.add_parser("migrate", help="Run database migrations")
    
    # Create the parser for the "create" command
    create_parser = subparsers.add_parser("create", help="Create a new migration")
    create_parser.add_argument("message", help="Migration message")
    
    args = parser.parse_args()
    
    if args.command == "migrate":
        run_migrations()
    elif args.command == "create":
        create_migration(args.message)
    else:
        parser.print_help()
        sys.exit(1)

if __name__ == "__main__":
    main()
