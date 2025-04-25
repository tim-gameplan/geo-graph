#!/usr/bin/env python3
"""
Direct Water Obstacle Boundary Conversion

This script runs the SQL script that directly converts water obstacle polygons to graph elements:
- Extracts vertices from water obstacles as graph nodes
- Creates edges between adjacent vertices
- Connects terrain grid points to obstacle boundary nodes
- Creates a unified graph for navigation

Usage:
    python run_obstacle_boundary_pipeline.py [--storage-srid SRID] [--max-connection-distance DISTANCE] [--water-speed-factor FACTOR] [--verbose]

Options:
    --storage-srid SRID                    SRID for storage (default: 3857)
    --max-connection-distance DISTANCE     Maximum distance for connecting terrain points to boundary nodes (default: 300)
    --water-speed-factor FACTOR            Speed factor for water edges (default: 0.2)
    --verbose                              Enable verbose logging
"""

import os
import sys
import argparse
import logging
import subprocess
import tempfile
from pathlib import Path

# Add the parent directory to the path so we can import from sibling packages
sys.path.append(str(Path(__file__).parent.parent.parent))

# Import our logging utility
from core.utils.logging_utils import get_logger

def run_sql_script(sql_file, params, logger):
    """
    Run a SQL script with parameters.
    
    Args:
        sql_file (str): Path to the SQL file
        params (dict): Parameters to replace in the SQL file
        logger: Logger instance
        
    Returns:
        bool: True if successful, False otherwise
    """
    # Read the SQL file
    with open(sql_file, 'r') as f:
        sql = f.read()
    
    # Replace parameters
    for key, value in params.items():
        sql = sql.replace(f':{key}', str(value))
    
    # Write to a temporary file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.sql', delete=False) as f:
        temp_file = f.name
        f.write(sql)
    
    # Execute the SQL script
    cmd = f'docker exec geo-graph-db-1 psql -U gis -d gis -f /tmp/{os.path.basename(temp_file)}'
    
    try:
        # Copy the temp file to the Docker container
        copy_cmd = f'docker cp {temp_file} geo-graph-db-1:/tmp/{os.path.basename(temp_file)}'
        subprocess.run(copy_cmd, shell=True, check=True)
        
        # Execute the SQL script
        result = subprocess.run(
            cmd,
            shell=True,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # Log the output
        logger.info(f"SQL script executed successfully")
        logger.info(result.stdout)
        if result.stderr:
            logger.warning(f"SQL script warnings: {result.stderr}")
        
        # Clean up
        os.remove(temp_file)
        
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Error executing SQL script: {e}")
        logger.error(f"Error output: {e.stderr}")
        
        # Clean up
        if os.path.exists(temp_file):
            os.remove(temp_file)
        
        return False

def main():
    """
    Main entry point for the script.
    
    Returns:
        int: 0 if successful, 1 otherwise
    """
    parser = argparse.ArgumentParser(
        description="Direct Water Obstacle Boundary Conversion",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    
    parser.add_argument(
        "--storage-srid",
        type=int,
        default=3857,
        help="SRID for storage (default: 3857)"
    )
    
    parser.add_argument(
        "--max-connection-distance",
        type=int,
        default=300,
        help="Maximum distance for connecting terrain points to boundary nodes (default: 300)"
    )
    
    parser.add_argument(
        "--water-speed-factor",
        type=float,
        default=0.2,
        help="Speed factor for water edges (default: 0.2)"
    )
    
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging"
    )
    
    args = parser.parse_args()
    
    # Configure logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logger = get_logger('obstacle_boundary_pipeline', level=log_level)
    
    # Set up parameters
    params = {
        'storage_srid': args.storage_srid,
        'max_connection_distance': args.max_connection_distance,
        'water_speed_factor': args.water_speed_factor
    }
    
    # Get the SQL file path
    sql_file = Path(__file__).parent / 'create_obstacle_boundary_graph.sql'
    if not sql_file.exists():
        logger.error(f"SQL file not found: {sql_file}")
        return 1
    
    logger.info(f"Running obstacle boundary pipeline with parameters: {params}")
    
    # Run the SQL script
    if not run_sql_script(sql_file, params, logger):
        logger.error("Failed to run the SQL script")
        return 1
    
    logger.info("Direct water obstacle boundary conversion completed successfully")
    return 0

if __name__ == "__main__":
    sys.exit(main())
