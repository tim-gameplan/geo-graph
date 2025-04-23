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

def run_sql_file(file_path, params=None):
    """Run a SQL file with parameters."""
    logger.info(f"Running SQL file: {file_path}")
    
    # Use docker exec to run psql inside the container
    cmd = [
        "docker", "exec", "geo-graph-db-1",
        "psql",
        "-U", "gis",
        "-d", "gis",
        "-v", "ON_ERROR_STOP=1"
    ]
    
    # Add parameters
    if params:
        for key, value in params.items():
            cmd.extend(["-v", f"{key}={value}"])
    
    # Add the file
    cmd.extend(["-f", f"/var/lib/postgresql/data/{file_path}"])
    
    try:
        result = subprocess.run(
            cmd,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        logger.info(f"SQL file executed successfully")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Error executing SQL file: {e.stderr}")
        return False

def run_pipeline(config_path, sql_dir):
    """Run the water obstacle pipeline with the boundary approach."""
    logger.info(f"Running water obstacle pipeline with boundary approach, config: {config_path}")
    
    # Load the configuration
    config = load_config(config_path)
    
    # Extract parameters from the configuration
    params = {}
    
    # Add CRS parameters
    params["source_srid"] = config["crs"]["source_srid"]
    params["storage_srid"] = config["crs"]["storage_srid"]
    params["output_srid"] = config["crs"]["output_srid"]
    
    # Add water buffer sizes
    for feature_type, buffer_size in config["water_buffers"].items():
        params[f"{feature_type}_buffer"] = buffer_size
    
    # Add terrain grid parameters
    params["grid_spacing"] = config["terrain_grid"]["grid_spacing"]
    params["max_edge_length"] = config["terrain_grid"]["max_edge_length"]
    
    # Add water edge parameters
    params["water_speed_factor"] = config["water_edges"]["water_speed_factor"]
    params["boundary_segment_length"] = config["water_edges"]["boundary_segment_length"]
    params["max_connection_distance"] = config["water_edges"]["max_connection_distance"]
    
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
