#!/usr/bin/env python3
"""
Improved Water Obstacle Pipeline with EPSG:3857 CRS

This script runs the water obstacle pipeline with EPSG:3857 CRS and the improved
water edge creation algorithm for better graph connectivity.
"""

import os
import sys
import argparse
import subprocess
import json
from pathlib import Path
import time

# Add the parent directory to the path so we can import from sibling packages
sys.path.append(str(Path(__file__).parent.parent.parent))

# Import our logging utility
from core.utils.logging_utils import get_logger

# Import config loader
from core.scripts.config_loader_3857 import load_config

# Configure logging
logger = get_logger('water_obstacle_pipeline_improved')

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
        logger.debug(f"Output: {result.stdout}")
        if result.stderr:
            logger.debug(f"Error output: {result.stderr}")
        
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

def run_pipeline(config_file, sql_dir, use_improved_water_edges=True):
    """Run the water obstacle pipeline."""
    # Load configuration
    loader = load_config(config_file)
    if not loader:
        logger.error("Failed to load configuration")
        return False
    
    # If sql_dir doesn't exist, try relative to the script's location
    if not os.path.exists(sql_dir):
        script_dir = Path(__file__).parent.resolve()
        alternative_sql_dir = script_dir.parent / 'sql'
        logger.info(f"SQL directory not found at {sql_dir}, trying {alternative_sql_dir}")
        if os.path.exists(alternative_sql_dir):
            sql_dir = alternative_sql_dir
    
    # Get SQL parameters
    params = loader.get_sql_params()
    
    # Get water feature types
    polygon_types, line_types = loader.get_water_feature_types()
    
    # Add water feature types to parameters
    params['polygon_types'] = "'" + "','".join(polygon_types) + "'"
    params['line_types'] = "'" + "','".join(line_types) + "'"
    
    # Get water crossing parameters
    water_crossing = loader.config.get('water_crossing', {})
    crossing_strategies = water_crossing.get('crossing_strategies', {})
    speed_factors = water_crossing.get('speed_factors', {})
    
    # Add water crossing parameters to params
    for water_type, strategy in crossing_strategies.items():
        params[f'{water_type}_crossing_strategy'] = f"'{strategy}'"
    
    for crossing_type, factor in speed_factors.items():
        params[f'{crossing_type}_speed_factor'] = factor
    
    # Determine which water edges script to use
    water_edges_script = "06_create_water_edges_improved_3857.sql" if use_improved_water_edges else "06_create_water_edges_3857.sql"
    
    # Run SQL files in order
    sql_files = [
        ("01_extract_water_features_3857.sql", "Extract water features"),
        ("02_create_water_buffers_3857.sql", "Create water buffers"),
        ("03_dissolve_water_buffers_3857.sql", "Dissolve water buffers"),
        ("04_create_terrain_grid_3857.sql", "Create terrain grid"),
        ("05_create_terrain_edges_3857.sql", "Create terrain edges"),
        (water_edges_script, "Create water edges"),
        ("07_create_environmental_tables_3857.sql", "Create environmental tables")
    ]
    
    for sql_file, description in sql_files:
        sql_path = os.path.join(sql_dir, sql_file)
        if not run_sql_file(sql_path, params, description):
            logger.error(f"Failed to run {sql_file}")
            return False
    
    logger.info("Water obstacle pipeline completed successfully")
    return True

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Run the water obstacle pipeline with EPSG:3857 CRS and improved water edge creation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run the pipeline with improved water edge creation
  python run_water_obstacle_pipeline_improved.py
  
  # Run the pipeline with original water edge creation
  python run_water_obstacle_pipeline_improved.py --use-original-water-edges
  
  # Run the pipeline with custom configuration
  python run_water_obstacle_pipeline_improved.py --config path/to/config.json
"""
    )
    
    # Configuration options
    parser.add_argument(
        "--config",
        default="../../config/crs_standardized_config_improved.json",
        help="Configuration file"
    )
    parser.add_argument(
        "--sql-dir",
        default="core/sql",
        help="SQL directory"
    )
    parser.add_argument(
        "--use-original-water-edges",
        action="store_true",
        help="Use the original water edge creation algorithm instead of the improved one"
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
    
    # Run the pipeline
    if not run_pipeline(args.config, args.sql_dir, not args.use_original_water_edges):
        logger.error("Failed to run the water obstacle pipeline")
        return 1
    
    logger.info("Water obstacle pipeline completed successfully")
    return 0

if __name__ == "__main__":
    sys.exit(main())
