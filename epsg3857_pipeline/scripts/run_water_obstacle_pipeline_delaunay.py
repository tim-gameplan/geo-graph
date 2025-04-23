#!/usr/bin/env python3
"""
Water Obstacle Pipeline with Delaunay Triangulation

This script runs the water obstacle pipeline with Delaunay triangulation for more natural terrain representation.
"""

import os
import sys
import argparse
import logging
import subprocess
import json
from pathlib import Path
import time

# Add parent directory to path for importing config_loader_3857
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config_loader_3857 import load_config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('water_obstacle_pipeline_delaunay.log')
    ]
)
logger = logging.getLogger('water_obstacle_pipeline_delaunay')

def run_sql_file(sql_file, params, description):
    """Run a SQL file with parameters."""
    logger.info(f"Running {description}: {sql_file}")
    
    # Read the SQL file
    try:
        with open(sql_file, 'r') as f:
            sql = f.read()
    except Exception as e:
        logger.error(f"Error reading SQL file {sql_file}: {e}")
        return False
    
    # Replace parameters
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

def run_pipeline(config_file, sql_dir):
    """Run the water obstacle pipeline with Delaunay triangulation."""
    # Load configuration
    loader = load_config(config_file)
    if not loader:
        logger.error("Failed to load configuration")
        return False
    
    # Get SQL parameters
    params = loader.get_sql_params()
    
    # Get water feature types
    polygon_types, line_types = loader.get_water_feature_types()
    
    # Add water feature types to parameters
    params['polygon_types'] = "'" + "','".join(polygon_types) + "'"
    params['line_types'] = "'" + "','".join(line_types) + "'"
    
    # Check if Delaunay triangulation parameters are present
    if 'boundary_point_spacing' not in params:
        logger.error("Missing Delaunay triangulation parameters in configuration")
        return False
    
    # Add connection distance parameter for backward compatibility
    if 'connection_dist' not in params:
        params['connection_dist'] = params.get('max_edge_length', 500)
    
    # Run SQL files in order
    sql_files = [
        ("01_extract_water_features_3857.sql", "Extract water features"),
        ("02_create_water_buffers_3857.sql", "Create water buffers"),
        ("03_dissolve_water_buffers_3857.sql", "Dissolve water buffers"),
        ("04_create_terrain_grid_delaunay_3857.sql", "Create terrain grid with Delaunay triangulation"),
        ("05_create_terrain_edges_delaunay_3857.sql", "Create terrain edges from Delaunay triangulation"),
        ("06_create_water_edges_3857.sql", "Create water edges"),
        ("07_create_environmental_tables_3857.sql", "Create environmental tables")
    ]
    
    for sql_file, description in sql_files:
        sql_path = os.path.join(sql_dir, sql_file)
        if not run_sql_file(sql_path, params, description):
            logger.error(f"Failed to run {sql_file}")
            return False
    
    logger.info("Water obstacle pipeline with Delaunay triangulation completed successfully")
    return True

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Run the water obstacle pipeline with Delaunay triangulation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run the pipeline with default configuration
  python run_water_obstacle_pipeline_delaunay.py
  
  # Run the pipeline with custom configuration
  python run_water_obstacle_pipeline_delaunay.py --config path/to/config.json
"""
    )
    
    # Configuration options
    parser.add_argument(
        "--config",
        default="epsg3857_pipeline/config/delaunay_config.json",
        help="Configuration file"
    )
    parser.add_argument(
        "--sql-dir",
        default="epsg3857_pipeline/sql",
        help="SQL directory"
    )
    
    args = parser.parse_args()
    
    # Run the pipeline
    if not run_pipeline(args.config, args.sql_dir):
        logger.error("Failed to run the water obstacle pipeline with Delaunay triangulation")
        return 1
    
    logger.info("Water obstacle pipeline with Delaunay triangulation completed successfully")
    return 0

if __name__ == "__main__":
    sys.exit(main())
