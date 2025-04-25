#!/usr/bin/env python3
"""
Reset OSM Tables Script

This script resets only the OSM data tables (planet_osm_*) in the database.
Use this script when you want to change the OSM data source or reload the OSM data.

Note: This will NOT affect derived tables, but without OSM data, the pipeline
will not be able to create new derived data.
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
        logging.FileHandler('reset_osm_tables.log')
    ]
)
logger = logging.getLogger('reset_osm_tables')

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

def reset_osm_tables(verbose=False):
    """Reset only the OSM data tables."""
    # List of OSM tables to drop
    osm_tables = [
        "planet_osm_line",
        "planet_osm_point",
        "planet_osm_polygon",
        "planet_osm_roads"
    ]
    
    success = True
    for table in osm_tables:
        if verbose:
            logger.info(f"Dropping table: {table}")
        if not run_sql_command(f"DROP TABLE IF EXISTS {table} CASCADE"):
            logger.warning(f"Failed to drop table {table}")
            success = False
    
    if success:
        logger.info("OSM tables reset successfully")
    else:
        logger.warning("Some OSM tables could not be reset")
    
    return success

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Reset only the OSM data tables (planet_osm_*)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Reset OSM tables
  python reset_osm_tables.py
  
  # Reset OSM tables with verbose output
  python reset_osm_tables.py --verbose
"""
    )
    
    # Options
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose output"
    )
    
    args = parser.parse_args()
    
    if not reset_osm_tables(args.verbose):
        logger.error("Failed to reset OSM tables")
        return 1
    
    logger.info("OSM tables reset completed successfully")
    return 0

if __name__ == "__main__":
    sys.exit(main())
