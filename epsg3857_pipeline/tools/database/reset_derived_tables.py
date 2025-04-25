#!/usr/bin/env python3
"""
Reset Derived Tables Script

This script resets only the derived tables created by the EPSG:3857 pipeline,
preserving the OSM data tables (planet_osm_*).

Use this script during development when you want to rerun the pipeline
without reloading the OSM data.
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
        logging.FileHandler('reset_derived_tables.log')
    ]
)
logger = logging.getLogger('reset_derived_tables')

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

def reset_derived_tables(verbose=False):
    """Reset only the derived tables, preserving OSM data tables."""
    # List of derived tables to drop
    derived_tables = [
        # Water feature tables
        "water_features", "water_features_polygon", "water_features_line",
        # Water buffer tables
        "water_buffers", "dissolved_water_buffers",
        # Terrain grid tables
        "terrain_grid", "terrain_grid_points", 
        # Edge tables
        "terrain_edges", "water_edges", "unified_edges",
        # Environmental tables
        "environmental_conditions",
        # Obstacle boundary tables
        "obstacle_boundary_nodes", "obstacle_boundary_edges", 
        "obstacle_boundary_connections", "obstacle_boundary_unified",
        # Delaunay triangulation tables
        "delaunay_points", "delaunay_triangles", "delaunay_edges"
    ]
    
    success = True
    for table in derived_tables:
        if verbose:
            logger.info(f"Dropping table: {table}")
        if not run_sql_command(f"DROP TABLE IF EXISTS {table} CASCADE"):
            logger.warning(f"Failed to drop table {table}")
            success = False
    
    # Also drop any views
    views = [
        "water_features"  # This is a view in the typed table approach
    ]
    
    for view in views:
        if verbose:
            logger.info(f"Dropping view: {view}")
        if not run_sql_command(f"DROP VIEW IF EXISTS {view} CASCADE"):
            logger.warning(f"Failed to drop view {view}")
            # Don't set success to False for views, as they might not exist
    
    if success:
        logger.info("Derived tables reset successfully")
    else:
        logger.warning("Some derived tables could not be reset")
    
    return success

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Reset only the derived tables created by the EPSG:3857 pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Reset derived tables
  python reset_derived_tables.py
  
  # Reset derived tables with verbose output
  python reset_derived_tables.py --verbose
"""
    )
    
    # Options
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose output"
    )
    
    args = parser.parse_args()
    
    if not reset_derived_tables(args.verbose):
        logger.error("Failed to reset derived tables")
        return 1
    
    logger.info("Derived tables reset completed successfully")
    return 0

if __name__ == "__main__":
    sys.exit(main())
