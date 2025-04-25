#!/usr/bin/env python3
"""
Reset Non-OSM Tables Script

This script dynamically identifies and drops all tables in the public schema
that are not part of the OSM data (planet_osm_*). It preserves the OSM data
tables while ensuring all other tables are removed.

Use this script when you want to clean up all non-OSM tables and ensure
a clean slate for running the pipeline, without having to reload OSM data.
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
        logging.FileHandler('reset_non_osm_tables.log')
    ]
)
logger = logging.getLogger('reset_non_osm_tables')

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
        return result.stdout
    except subprocess.CalledProcessError as e:
        logger.error(f"Error executing SQL command: {e.stderr}")
        return None

def reset_non_osm_tables(verbose=False):
    """Reset all non-OSM tables in the database."""
    # Get list of all tables in public schema that don't start with planet_osm_
    # and aren't system tables like spatial_ref_sys
    query = """
    SELECT tablename FROM pg_tables 
    WHERE schemaname = 'public' 
    AND tablename NOT LIKE 'planet_osm_%'
    AND tablename != 'spatial_ref_sys'
    AND tablename != 'geography_columns'
    AND tablename != 'geometry_columns'
    AND tablename != 'raster_columns'
    AND tablename != 'raster_overviews';
    """
    
    result = run_sql_command(query)
    if result is None:
        logger.error("Failed to get list of tables")
        return False
    
    # Parse the result to get table names
    tables = [line.strip() for line in result.split('\n') if line.strip() and not line.startswith('-') and not line.startswith('(')]
    # Remove header and footer lines
    if tables and tables[0] == 'tablename':
        tables = tables[1:]
    
    if not tables:
        logger.info("No non-OSM tables found to drop")
        return True
    
    if verbose:
        logger.info(f"Found {len(tables)} non-OSM tables to drop: {', '.join(tables)}")
    
    # Drop each table
    success = True
    for table in tables:
        if verbose:
            logger.info(f"Dropping table: {table}")
        if run_sql_command(f"DROP TABLE IF EXISTS {table} CASCADE") is None:
            logger.warning(f"Failed to drop table {table}")
            success = False
    
    # Also drop any views that might be left
    query = """
    SELECT viewname FROM pg_views 
    WHERE schemaname = 'public' 
    AND viewname NOT LIKE 'planet_osm_%'
    AND viewname != 'geography_columns'
    AND viewname != 'geometry_columns';
    """
    
    result = run_sql_command(query)
    if result is None:
        logger.error("Failed to get list of views")
        return False
    
    # Parse the result to get view names
    views = [line.strip() for line in result.split('\n') if line.strip() and not line.startswith('-') and not line.startswith('(')]
    # Remove header and footer lines
    if views and views[0] == 'viewname':
        views = views[1:]
    
    if views:
        if verbose:
            logger.info(f"Found {len(views)} views to drop: {', '.join(views)}")
        
        # Drop each view
        for view in views:
            if verbose:
                logger.info(f"Dropping view: {view}")
            if run_sql_command(f"DROP VIEW IF EXISTS {view} CASCADE") is None:
                logger.warning(f"Failed to drop view {view}")
                # Don't set success to False for views, as they might not exist
    
    if success:
        logger.info("Non-OSM tables reset successfully")
    else:
        logger.warning("Some non-OSM tables could not be reset")
    
    return success

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Reset all non-OSM tables in the database",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Reset non-OSM tables
  python reset_non_osm_tables.py
  
  # Reset non-OSM tables with verbose output
  python reset_non_osm_tables.py --verbose
  
  # Reset non-OSM tables with confirmation
  python reset_non_osm_tables.py --confirm
"""
    )
    
    # Options
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose output"
    )
    
    parser.add_argument(
        "--confirm",
        action="store_true",
        help="Require confirmation before resetting tables"
    )
    
    args = parser.parse_args()
    
    if args.confirm:
        confirmation = input("This will delete all non-OSM tables in the database. Are you sure? (y/n): ")
        if confirmation.lower() != 'y':
            logger.info("Operation cancelled by user")
            return 0
    
    if not reset_non_osm_tables(args.verbose):
        logger.error("Failed to reset non-OSM tables")
        return 1
    
    logger.info("Non-OSM tables reset completed successfully")
    return 0

if __name__ == "__main__":
    sys.exit(main())
