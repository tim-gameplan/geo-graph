#!/usr/bin/env python3
"""
Delaunay-based water obstacle modeling pipeline.

This script:
1. Loads configuration from a JSON file with CRS settings
2. Connects to the PostgreSQL database
3. Executes SQL scripts in sequence with parameters from the configuration
4. Uses EPSG:3857 (Web Mercator) for all processing
5. Uses Delaunay triangulation for terrain grid and edges
6. Only transforms to EPSG:4326 for export
"""

import os
import sys
import argparse
import logging
import time
from pathlib import Path
from typing import Dict, Any, List, Optional

import psycopg2
from psycopg2.extras import DictCursor

# Add the parent directory to the path so we can import config_loader
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scripts.config_loader import ConfigLoader


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


def get_db_connection(conn_string: Optional[str] = None) -> psycopg2.extensions.connection:
    """
    Create a database connection.
    
    Args:
        conn_string: PostgreSQL connection string
    
    Returns:
        Database connection
    
    Raises:
        Exception: If connection fails
    """
    if conn_string is None:
        conn_string = os.environ.get('PG_URL', 'postgresql://gis:gis@localhost:5432/gis')
    
    try:
        conn = psycopg2.connect(conn_string)
        logger.info(f"Connected to database: {conn_string.split('@')[-1]}")
        return conn
    except Exception as e:
        logger.error(f"Error connecting to database: {e}")
        raise


def execute_sql_file(
    conn: psycopg2.extensions.connection,
    sql_file: str,
    params: Dict[str, Any]
) -> None:
    """
    Execute a SQL file with parameters.
    
    Args:
        conn: Database connection
        sql_file: Path to SQL file
        params: Dictionary of parameters to replace in the SQL
    
    Raises:
        Exception: If SQL execution fails
    """
    logger.info(f"Executing SQL file: {os.path.basename(sql_file)}")
    
    start_time = time.time()
    
    try:
        with open(sql_file, 'r') as f:
            sql = f.read()
        
        # Debug: Log parameters
        logger.debug(f"SQL parameters: {params}")
        
        # Replace parameters in SQL
        for key, value in params.items():
            if isinstance(value, list):
                # Convert lists to PostgreSQL arrays
                pg_array = "'{" + ",".join([str(item) for item in value]) + "}'"
                sql = sql.replace(f":{key}", pg_array)
                logger.debug(f"Replaced :{key} with {pg_array}")
            elif isinstance(value, bool):
                # Convert booleans to PostgreSQL booleans
                sql = sql.replace(f":{key}", str(value).lower())
                logger.debug(f"Replaced :{key} with {str(value).lower()}")
            elif isinstance(value, dict):
                # For nested dictionaries, use the 'default' value if it exists
                if 'default' in value:
                    sql = sql.replace(f":{key}", str(value['default']))
                    logger.debug(f"Replaced :{key} with {str(value['default'])}")
            else:
                # For all other types, convert to string
                # Ensure we're using just the numeric value for parameters ending with _m
                if key.endswith('_m') and isinstance(value, (int, float)):
                    sql = sql.replace(f":{key}", str(value))
                    logger.debug(f"Replaced :{key} with {str(value)}")
                else:
                    sql = sql.replace(f":{key}", str(value))
                    logger.debug(f"Replaced :{key} with {str(value)}")
        
        with conn.cursor() as cur:
            cur.execute(sql)
        
        conn.commit()
        
        elapsed_time = time.time() - start_time
        logger.info(f"Completed {os.path.basename(sql_file)} in {elapsed_time:.2f} seconds")
    
    except Exception as e:
        conn.rollback()
        logger.error(f"Error executing {os.path.basename(sql_file)}: {e}")
        raise


def run_pipeline(
    config_path: str,
    sql_dir: str,
    conn_string: Optional[str] = None,
    skip_steps: Optional[List[str]] = None
) -> None:
    """
    Run the Delaunay-based water obstacle modeling pipeline.
    
    Args:
        config_path: Path to configuration JSON file
        sql_dir: Directory containing SQL scripts
        conn_string: PostgreSQL connection string
        skip_steps: List of steps to skip (e.g., ['01', '02'])
    
    Raises:
        Exception: If pipeline execution fails
    """
    # Load configuration
    try:
        config = ConfigLoader(config_path)
        params = config.get_sql_params()
        
        # Add additional parameters for the CRS-standardized scripts
        if 'dissolve' in config.config:
            dissolve_config = config.config['dissolve']
            params['work_mem_mb'] = dissolve_config.get('work_mem_mb', 256)
            params['parallel_workers'] = dissolve_config.get('parallel_workers', 4)
            params['simplify_tolerance_m'] = dissolve_config.get('simplify_tolerance_m', 5)
            params['max_area_sqkm'] = dissolve_config.get('max_area_sqkm', 5000)
        
        # Add terrain grid parameters with _m suffix for CRS-standardized scripts
        if 'terrain_grid' in config.config:
            terrain_grid = config.config['terrain_grid']
            params['cell_size_m'] = terrain_grid.get('cell_size_m', terrain_grid.get('cell_size', 200))
            params['connection_distance_m'] = terrain_grid.get('connection_distance_m', terrain_grid.get('connection_distance', 300))
        
        # Add width multiplier and min width parameters
        params['width_multiplier'] = 1.5
        params['min_width'] = 10
        
        logger.info(f"Loaded configuration from {config_path}")
        logger.info(f"Using CRS: EPSG:{config.config.get('crs', {}).get('storage', 3857)}")
        logger.info(f"Using Delaunay triangulation for terrain grid and edges")
    except Exception as e:
        logger.error(f"Error loading configuration: {e}")
        raise
    
    # Connect to database
    conn = get_db_connection(conn_string)
    
    try:
        # Define SQL scripts to execute in order
        sql_files = [
            "01_extract_water_features_3857.sql",
            "02_create_water_buffers_3857.sql",
            "03_dissolve_water_buffers_3857.sql",
            "04_create_terrain_grid_delaunay_3857.sql",  # Use Delaunay version
            "05_create_terrain_edges_delaunay_3857.sql", # Use Delaunay version
            "06_create_water_edges_3857.sql",
            "07_create_environmental_tables_3857.sql"
        ]
        
        # Skip steps if specified
        if skip_steps:
            sql_files = [f for f in sql_files if not any(f.startswith(step) for step in skip_steps)]
        
        # Execute SQL scripts in order
        for sql_file in sql_files:
            sql_path = os.path.join(sql_dir, sql_file)
            if not os.path.exists(sql_path):
                logger.warning(f"SQL file not found: {sql_path}")
                
                # Try alternatives based on the file name
                if "delaunay" in sql_file:
                    # Try the regular 3857 version if delaunay version not found
                    regular_sql_file = sql_file.replace("_delaunay", "")
                    regular_sql_path = os.path.join(sql_dir, regular_sql_file)
                    
                    if os.path.exists(regular_sql_path):
                        logger.warning(f"Falling back to regular 3857 version: {regular_sql_file}")
                        sql_path = regular_sql_path
                    else:
                        # Try the original version without any suffix
                        original_sql_file = sql_file.replace("_delaunay_3857", "")
                        original_sql_path = os.path.join(sql_dir, original_sql_file)
                        
                        if os.path.exists(original_sql_path):
                            logger.warning(f"Falling back to original version: {original_sql_file}")
                            sql_path = original_sql_path
                        else:
                            logger.error(f"No suitable alternative found for: {sql_file}")
                            raise FileNotFoundError(f"SQL file not found: {sql_path}")
                else:
                    # For non-delaunay files, try the original version without the _3857 suffix
                    original_sql_file = sql_file.replace("_3857", "")
                    original_sql_path = os.path.join(sql_dir, original_sql_file)
                    
                    if os.path.exists(original_sql_path):
                        logger.warning(f"Falling back to original version: {original_sql_file}")
                        sql_path = original_sql_path
                    else:
                        logger.error(f"No suitable alternative found for: {sql_file}")
                        raise FileNotFoundError(f"SQL file not found: {sql_path}")
            
            execute_sql_file(conn, sql_path, params)
        
        logger.info("Delaunay-based water obstacle modeling pipeline completed successfully")
    
    except Exception as e:
        logger.error(f"Pipeline execution failed: {e}")
        raise
    
    finally:
        conn.close()
        logger.info("Database connection closed")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Run the Delaunay-based water obstacle modeling pipeline")
    parser.add_argument(
        "--config",
        default="config/crs_standardized_config.json",
        help="Path to configuration JSON file"
    )
    parser.add_argument(
        "--sql-dir",
        default="sql",
        help="Directory containing SQL scripts"
    )
    parser.add_argument(
        "--conn-string",
        help="PostgreSQL connection string (default: from PG_URL environment variable)"
    )
    parser.add_argument(
        "--skip",
        nargs="+",
        help="Steps to skip (e.g., 01 02)"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging"
    )
    
    args = parser.parse_args()
    
    # Set log level
    if args.verbose:
        logger.setLevel(logging.DEBUG)
    
    # Resolve paths
    base_dir = Path(__file__).parent.parent
    # Fix the path resolution to avoid duplicate 'planning' in the path
    if args.config.startswith('planning/'):
        config_path = os.path.join(os.path.dirname(base_dir), args.config)
    else:
        config_path = base_dir / args.config if not os.path.isabs(args.config) else args.config
    
    if args.sql_dir.startswith('planning/'):
        sql_dir = os.path.join(os.path.dirname(base_dir), args.sql_dir)
    else:
        sql_dir = base_dir / args.sql_dir if not os.path.isabs(args.sql_dir) else args.sql_dir
    
    try:
        run_pipeline(
            config_path=str(config_path),
            sql_dir=str(sql_dir),
            conn_string=args.conn_string,
            skip_steps=args.skip
        )
        return 0
    except Exception as e:
        logger.error(f"Pipeline failed: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
