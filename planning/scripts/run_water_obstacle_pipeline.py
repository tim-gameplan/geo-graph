#!/usr/bin/env python3
"""
Main script to run the water obstacle modeling pipeline.

This script:
1. Loads configuration from a JSON file
2. Connects to the PostgreSQL database
3. Executes SQL scripts in sequence with parameters from the configuration
4. Logs the results of each step
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
        logging.FileHandler('water_obstacle_pipeline.log')
    ]
)
logger = logging.getLogger('water_obstacle_pipeline')


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
        
        # Replace parameters in SQL
        for key, value in params.items():
            if isinstance(value, list):
                # Convert lists to PostgreSQL arrays
                pg_array = "'{" + ",".join([str(item) for item in value]) + "}'"
                sql = sql.replace(f":{key}", pg_array)
            elif isinstance(value, bool):
                # Convert booleans to PostgreSQL booleans
                sql = sql.replace(f":{key}", str(value).lower())
            else:
                sql = sql.replace(f":{key}", str(value))
        
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
    Run the water obstacle modeling pipeline.
    
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
        logger.info(f"Loaded configuration from {config_path}")
    except Exception as e:
        logger.error(f"Error loading configuration: {e}")
        raise
    
    # Connect to database
    conn = get_db_connection(conn_string)
    
    try:
        # Define SQL scripts to execute in order
        sql_files = [
            "01_extract_water_features.sql",
            "02_create_water_buffers.sql",
            "03_dissolve_water_buffers.sql",
            "04_create_terrain_grid.sql",
            "05_create_terrain_edges.sql",
            "06_create_water_edges.sql",
            "07_create_environmental_tables.sql"
        ]
        
        # Skip steps if specified
        if skip_steps:
            sql_files = [f for f in sql_files if not any(f.startswith(step) for step in skip_steps)]
        
        # Execute SQL scripts in order
        for sql_file in sql_files:
            sql_path = os.path.join(sql_dir, sql_file)
            if not os.path.exists(sql_path):
                logger.error(f"SQL file not found: {sql_path}")
                raise FileNotFoundError(f"SQL file not found: {sql_path}")
            
            execute_sql_file(conn, sql_path, params)
        
        logger.info("Water obstacle modeling pipeline completed successfully")
    
    except Exception as e:
        logger.error(f"Pipeline execution failed: {e}")
        raise
    
    finally:
        conn.close()
        logger.info("Database connection closed")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Run the water obstacle modeling pipeline")
    parser.add_argument(
        "--config",
        default="config/default_config.json",
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
    config_path = base_dir / args.config if not os.path.isabs(args.config) else args.config
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
