#!/usr/bin/env python3
"""
Database Reset Script

This script resets the database by dropping and recreating tables used by the EPSG:3857 pipeline.
"""

import os
import sys
import argparse
import subprocess
from pathlib import Path

# Add the parent directory to the path so we can import from sibling packages
sys.path.append(str(Path(__file__).parent.parent.parent))

# Import our logging utility
from core.utils.logging_utils import get_logger

# Configure logging
logger = get_logger('reset_database')

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
        logger.debug(f"Output: {result.stdout}")
        if result.stderr:
            logger.debug(f"Error output: {result.stderr}")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Error executing SQL command: {e.stderr}")
        return False

def reset_derived_tables():
    """Reset derived tables."""
    # List of derived tables to reset
    derived_tables = [
        "water_features",
        "water_features_polygon",
        "water_features_line",
        "water_buffers",
        "dissolved_water_buffers",
        "terrain_grid",
        "terrain_grid_points",
        "terrain_edges",
        "water_edges",
        "environmental_tables"
    ]
    
    # Drop each derived table individually
    for table in derived_tables:
        if not run_sql_command(f"DROP TABLE IF EXISTS {table} CASCADE"):
            logger.warning(f"Failed to drop table {table}, but continuing...")
    
    logger.info("Derived tables reset successfully")
    return True

def reset_all_tables():
    """Reset all tables including OSM data."""
    if not reset_derived_tables():
        return False
    
    tables = [
        "planet_osm_line",
        "planet_osm_point",
        "planet_osm_polygon",
        "planet_osm_roads"
    ]
    
    for table in tables:
        if not run_sql_command(f"DROP TABLE IF EXISTS {table} CASCADE"):
            logger.error(f"Failed to drop table {table}")
            return False
    
    logger.info("All tables reset successfully")
    return True

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Reset the database",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Reset derived tables
  python reset_database.py --reset-derived
  
  # Reset all tables
  python reset_database.py --reset-all
  
  # Reset derived tables with confirmation
  python reset_database.py --reset-derived --confirm
"""
    )
    
    # Reset options
    parser.add_argument(
        "--reset-derived",
        action="store_true",
        help="Reset derived tables"
    )
    parser.add_argument(
        "--reset-all",
        action="store_true",
        help="Reset all tables including OSM data"
    )
    parser.add_argument(
        "--confirm",
        action="store_true",
        help="Skip confirmation prompt"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging"
    )
    
    args = parser.parse_args()
    
    # Set verbose logging if requested
    if args.verbose:
        logger.setLevel('DEBUG')
    
    # Confirm before resetting
    if not args.confirm:
        if args.reset_all:
            print("\n⚠️  WARNING: This will delete ALL tables in the database, including OSM data!")
            print("This operation cannot be undone and will require reimporting OSM data.")
        elif args.reset_derived:
            print("\n⚠️  WARNING: This will delete all derived tables in the database!")
            print("This operation cannot be undone and will require rerunning the pipeline.")
        
        confirm = input("\nAre you sure you want to continue? (y/N): ")
        if confirm.lower() != 'y':
            print("Operation cancelled.")
            return 0
    
    if args.reset_all:
        if not reset_all_tables():
            logger.error("Failed to reset all tables")
            return 1
    elif args.reset_derived:
        if not reset_derived_tables():
            logger.error("Failed to reset derived tables")
            return 1
    else:
        parser.print_help()
        return 1
    
    logger.info("Database reset completed successfully")
    return 0

if __name__ == "__main__":
    sys.exit(main())
