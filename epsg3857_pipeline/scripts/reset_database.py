#!/usr/bin/env python3
"""
Database Reset Script

This script resets the database by dropping and recreating tables used by the EPSG:3857 pipeline.
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
        logging.FileHandler('reset_database.log')
    ]
)
logger = logging.getLogger('reset_database')

def run_sql_command(command):
    """Run a SQL command."""
    logger.info(f"Running SQL command: {command}")
    
    cmd = [
        "psql",
        "-h", "localhost",
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

def reset_derived_tables():
    """Reset derived tables."""
    tables = [
        "graph_topology",
        "graph_vertices",
        "graph_edges",
        "environmental_conditions",
        "elevation_data",
        "unified_edges",
        "water_edges",
        "terrain_edges",
        "terrain_vertices",
        "delaunay_edges",
        "delaunay_triangles",
        "terrain_grid",
        "water_obstacles",
        "dissolved_water_buffers",
        "water_buffers",
        "water_features"
    ]
    
    for table in tables:
        if not run_sql_command(f"DROP TABLE IF EXISTS {table} CASCADE"):
            logger.error(f"Failed to drop table {table}")
            return False
    
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
    
    args = parser.parse_args()
    
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
