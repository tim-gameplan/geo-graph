#!/usr/bin/env python3
"""
Water Obstacle Pipeline with Boundary Approach

This script runs the water obstacle pipeline with the boundary approach for water edge creation.
"""

import os
import sys
import argparse
import logging
import subprocess
import time
from pathlib import Path

# Add the parent directory to the path so we can import from sibling packages
sys.path.append(str(Path(__file__).parent.parent.parent))

from epsg3857_pipeline.scripts.config_loader_3857 import load_config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('water_obstacle_pipeline_boundary.log')
    ]
)
logger = logging.getLogger('water_obstacle_pipeline_boundary')

def run_sql_file(file_path, params=None, description=None):
    """Run a SQL file with parameters."""
    if description is None:
        description = f"SQL file: {file_path}"
    logger.info(f"Running {description}")
    
    # Read the SQL file
    try:
        with open(file_path, 'r') as f:
            sql = f.read()
    except Exception as e:
        logger.error(f"Error reading SQL file {file_path}: {e}")
        return False
    
    # Replace parameters
    if params:
        for key, value in params.items():
            placeholder = f":{key}"
            sql = sql.replace(placeholder, str(value))
    
    # Write the SQL to a temporary file
    temp_file = f"temp_{int(time.time())}.sql"
    try:
        with open(temp_file, 'w') as f:
            f.write(sql)
    except Exception as e:
        logger.error(f"Error writing temporary SQL file: {e}")
        return False
    
    # Run the SQL file using Docker
    cmd = [
        "docker", "exec", "geo-graph-db-1",
        "psql",
        "-U", "gis",
        "-d", "gis",
        "-f", f"/tmp/{os.path.basename(temp_file)}"
    ]
    
    # Copy the temp file to the container
    copy_cmd = [
        "docker", "cp",
        temp_file,
        f"geo-graph-db-1:/tmp/{os.path.basename(temp_file)}"
    ]
    
    try:
        subprocess.run(
            copy_cmd,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
    except subprocess.CalledProcessError as e:
        logger.error(f"Error copying SQL file to container: {e.stderr}")
        return False
    
    try:
        result = subprocess.run(
            cmd,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        logger.info(f"✅ {description} completed successfully")
        
        # Clean up temporary file
        os.remove(temp_file)
        
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"❌ {description} failed: {e}")
        logger.error(f"Error output: {e.stderr}")
        
        # Clean up temporary file
        if os.path.exists(temp_file):
            os.remove(temp_file)
        
        return False

def run_pipeline(config_path, sql_dir):
    """Run the water obstacle pipeline with the boundary approach."""
    logger.info(f"Running water obstacle pipeline with boundary approach, config: {config_path}")
    
    # Load the configuration
    config_loader = load_config(config_path)
    if not config_loader:
        logger.error("Failed to load configuration")
        return False
    
    # Get SQL parameters from the config loader
    params = config_loader.get_sql_params()
    
    # Add water edge parameters (these are specific to the boundary approach)
    if config_loader.config and 'water_edges' in config_loader.config:
        water_edges = config_loader.config['water_edges']
        params["water_speed_factor"] = water_edges.get('water_speed_factor', 0.2)
        params["boundary_segment_length"] = water_edges.get('boundary_segment_length', 100)
        params["max_connection_distance"] = water_edges.get('max_connection_distance', 300)
    
    # Run the SQL files
    sql_files = [
        "01_extract_water_features_3857.sql",
        "02_create_water_buffers_3857.sql",
        "03_dissolve_water_buffers_3857.sql",
        "04_create_terrain_grid_with_water_3857.sql",  # Use the version that includes water areas
        "05_create_terrain_edges_with_water_3857.sql", # Use the version that includes water crossings
        "06_create_water_boundary_edges_3857.sql"      # Use the boundary approach for water edges
    ]
    
    for sql_file in sql_files:
        file_path = os.path.join(sql_dir, sql_file)
        if not run_sql_file(file_path, params):
            logger.error(f"Failed to run SQL file: {file_path}")
            return False
    
    logger.info("Water obstacle pipeline with boundary approach completed successfully")
    return True

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Run the water obstacle pipeline with the boundary approach for water edge creation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run the pipeline with the default configuration
  python run_water_obstacle_pipeline_boundary.py
  
  # Run the pipeline with a custom configuration
  python run_water_obstacle_pipeline_boundary.py --config path/to/config.json
"""
    )
    
    # Configuration options
    parser.add_argument(
        "--config",
        default="epsg3857_pipeline/config/crs_standardized_config_boundary.json",
        help="Path to the configuration file"
    )
    parser.add_argument(
        "--sql-dir",
        default="epsg3857_pipeline/sql",
        help="Path to the directory containing SQL files"
    )
    
    args = parser.parse_args()
    
    if not run_pipeline(args.config, args.sql_dir):
        logger.error("Failed to run water obstacle pipeline with boundary approach")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
