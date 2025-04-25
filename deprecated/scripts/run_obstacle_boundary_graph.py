#!/usr/bin/env python3
"""
Direct Water Obstacle Boundary Conversion

This script runs the SQL script that directly converts water obstacle polygons to graph elements:
- Extracts vertices from water obstacles as graph nodes
- Creates edges between adjacent vertices
- Connects terrain grid points to obstacle boundary nodes
- Creates a unified graph for navigation

Usage:
    python run_obstacle_boundary_graph.py [--storage-srid SRID] [--max-connection-distance DISTANCE] [--water-speed-factor FACTOR]

Options:
    --storage-srid SRID                    SRID for storage (default: 3857)
    --max-connection-distance DISTANCE     Maximum distance for connecting terrain points to boundary nodes (default: 300)
    --water-speed-factor FACTOR            Speed factor for water edges (default: 0.2)
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
        logging.FileHandler('obstacle_boundary_graph.log')
    ]
)
logger = logging.getLogger('obstacle_boundary_graph')

def run_sql_script(sql_file, params):
    """Run a SQL script with parameters."""
    # Read the SQL file
    with open(sql_file, 'r') as f:
        sql = f.read()
    
    # Replace parameters
    for key, value in params.items():
        sql = sql.replace(f':{key}', str(value))
    
    # Write to a temporary file
    temp_file = f'temp_{os.getpid()}.sql'
    with open(temp_file, 'w') as f:
        f.write(sql)
    
    # Execute the SQL script
    cmd = f'docker exec geo-graph-db-1 psql -U gis -d gis -f /tmp/{temp_file}'
    
    try:
        # Copy the temp file to the Docker container
        copy_cmd = f'docker cp {temp_file} geo-graph-db-1:/tmp/{temp_file}'
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
    """Main entry point."""
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
        "--sql-dir",
        default="epsg3857_pipeline/sql",
        help="Directory containing SQL scripts"
    )
    
    args = parser.parse_args()
    
    # Set up parameters
    params = {
        'storage_srid': args.storage_srid,
        'max_connection_distance': args.max_connection_distance,
        'water_speed_factor': args.water_speed_factor
    }
    
    # Run the SQL script
    sql_file = os.path.join(args.sql_dir, 'create_obstacle_boundary_graph.sql')
    if not os.path.exists(sql_file):
        logger.error(f"SQL file not found: {sql_file}")
        return 1
    
    if not run_sql_script(sql_file, params):
        logger.error("Failed to run the SQL script")
        return 1
    
    logger.info("Direct water obstacle boundary conversion completed successfully")
    return 0

if __name__ == "__main__":
    sys.exit(main())
