#!/usr/bin/env python3
"""
Reset All Tables Script

This script resets ALL tables in the database by dropping and recreating the public schema.
Use this script when you want to start with a completely clean database.

WARNING: This will delete ALL data in the database, including both OSM data tables
and derived tables. You will need to reload OSM data after running this script.
"""

import os
import sys
import argparse
import logging
import subprocess
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('reset_all_tables.log')
    ]
)
logger = logging.getLogger('reset_all_tables')

def run_sql_command(command):
    """Run a SQL command."""
    logger.info(f"Running SQL command: {command}")
    
    # Use docker exec to run psql inside the container
    cmd = [
        "docker", "exec", "geo-graph-db-1",
        "psql",
        "-U", "gis",
        "-d", "gis",
        "-c", command
    ]
    
    try:
        result = subprocess.run(
            cmd,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        logger.info(f"SQL command executed successfully")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Error executing SQL command: {e.stderr}")
        return False

def reset_all_tables():
    """Reset all tables in the database."""
    # Drop and recreate the public schema
    if not run_sql_command("DROP SCHEMA public CASCADE"):
        logger.error("Failed to drop public schema")
        return False
    
    if not run_sql_command("CREATE SCHEMA public"):
        logger.error("Failed to create public schema")
        return False
    
    # Recreate necessary extensions
    extensions = ["postgis", "pgrouting", "hstore"]
    for extension in extensions:
        if not run_sql_command(f"CREATE EXTENSION IF NOT EXISTS {extension}"):
            logger.error(f"Failed to create extension {extension}")
            return False
    
    logger.info("All tables reset successfully")
    return True

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Reset ALL tables in the database",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Reset all tables
  python reset_all_tables.py
  
  # Reset all tables with confirmation
  python reset_all_tables.py --confirm
"""
    )
    
    # Options
    parser.add_argument(
        "--confirm",
        action="store_true",
        help="Require confirmation before resetting all tables"
    )
    
    args = parser.parse_args()
    
    if args.confirm:
        confirmation = input("WARNING: This will delete ALL data in the database. Are you sure? (y/n): ")
        if confirmation.lower() != 'y':
            logger.info("Operation cancelled by user")
            return 0
    
    if not reset_all_tables():
        logger.error("Failed to reset all tables")
        return 1
    
    logger.info("All tables reset completed successfully")
    logger.warning("You will need to reload OSM data before running the pipeline")
    return 0

if __name__ == "__main__":
    sys.exit(main())
