#!/usr/bin/env python3
"""
Script to update environmental conditions in the database.

This script:
1. Loads configuration from a JSON file or command-line arguments
2. Updates the environmental_conditions table in the database
3. Runs the update_water_crossability() function to recalculate water edge costs
"""

import os
import sys
import argparse
import logging
import json
import tempfile
from pathlib import Path
from typing import Dict, Any, Optional

import psycopg2

# Add the parent directory to the path so we can import config_loader
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scripts.config_loader import ConfigLoader


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('environmental_conditions.log')
    ]
)
logger = logging.getLogger('environmental_conditions')


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


def update_conditions(
    config_path: str,
    conditions_override: Optional[Dict[str, float]] = None,
    conn_string: Optional[str] = None
) -> None:
    """
    Update environmental conditions in the database.
    
    Args:
        config_path: Path to configuration JSON file
        conditions_override: Dictionary of conditions to override from the config
        conn_string: PostgreSQL connection string
    
    Raises:
        Exception: If update fails
    """
    # Load configuration
    try:
        config = ConfigLoader(config_path)
        env_conditions = config.get_section('environmental_conditions')
        logger.info(f"Loaded configuration from {config_path}")
        
        # Override conditions if specified
        if conditions_override:
            env_conditions.update(conditions_override)
            logger.info(f"Overriding conditions: {conditions_override}")
        
        # Log the conditions that will be applied
        logger.info(f"Applying environmental conditions: {env_conditions}")
    except Exception as e:
        logger.error(f"Error loading configuration: {e}")
        raise
    
    # Connect to database
    conn = get_db_connection(conn_string)
    
    try:
        with conn.cursor() as cur:
            # Check if the environmental_conditions table exists
            cur.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'environmental_conditions'
                )
            """)
            table_exists = cur.fetchone()[0]
            
            if not table_exists:
                logger.error("Environmental conditions table does not exist. Run the pipeline first.")
                raise Exception("Environmental conditions table does not exist")
            
            # Update each environmental condition
            for condition, value in env_conditions.items():
                cur.execute(
                    """
                    INSERT INTO environmental_conditions (condition_name, value)
                    VALUES (%s, %s)
                    ON CONFLICT (condition_name) DO UPDATE
                    SET value = EXCLUDED.value,
                        last_updated = CURRENT_TIMESTAMP
                    """,
                    (condition, value)
                )
            
            # Run the update function to recalculate crossability
            cur.execute("SELECT update_water_crossability()")
            
            # Get the updated conditions
            cur.execute("SELECT * FROM current_environment")
            updated_conditions = cur.fetchall()
            
            # Get the effect on water edges
            cur.execute("""
                SELECT 
                    MIN(cost) as min_cost,
                    MAX(cost) as max_cost,
                    AVG(cost) as avg_cost
                FROM water_edges
            """)
            cost_stats = cur.fetchone()
            
            conn.commit()
            
            # Log the results
            logger.info("Environmental conditions updated successfully")
            logger.info("Current environmental conditions:")
            for row in updated_conditions:
                logger.info(f"  {row[0]}: {row[1]} ({row[3]})")
            
            logger.info("Effect on water edge costs:")
            logger.info(f"  Min cost: {cost_stats[0]:.2f}")
            logger.info(f"  Max cost: {cost_stats[1]:.2f}")
            logger.info(f"  Avg cost: {cost_stats[2]:.2f}")
    
    except Exception as e:
        conn.rollback()
        logger.error(f"Error updating environmental conditions: {e}")
        raise
    
    finally:
        conn.close()
        logger.info("Database connection closed")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Update environmental conditions")
    parser.add_argument(
        "--config",
        default="config/default_config.json",
        help="Path to configuration JSON file"
    )
    parser.add_argument(
        "--conditions",
        help="JSON string with conditions to override config file"
    )
    parser.add_argument(
        "--rainfall",
        type=float,
        help="Rainfall value (0.0 = dry, 1.0 = heavy rain)"
    )
    parser.add_argument(
        "--snow-depth",
        type=float,
        help="Snow depth in meters"
    )
    parser.add_argument(
        "--temperature",
        type=float,
        help="Temperature in Celsius"
    )
    parser.add_argument(
        "--conn-string",
        help="PostgreSQL connection string (default: from PG_URL environment variable)"
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
    
    # Build conditions override dictionary
    conditions_override = {}
    
    # From JSON string
    if args.conditions:
        try:
            conditions_override.update(json.loads(args.conditions))
        except json.JSONDecodeError as e:
            logger.error(f"Error parsing conditions JSON: {e}")
            return 1
    
    # From individual arguments
    if args.rainfall is not None:
        conditions_override['rainfall'] = args.rainfall
    
    if args.snow_depth is not None:
        conditions_override['snow_depth'] = args.snow_depth
    
    if args.temperature is not None:
        conditions_override['temperature'] = args.temperature
    
    try:
        update_conditions(
            config_path=str(config_path),
            conditions_override=conditions_override if conditions_override else None,
            conn_string=args.conn_string
        )
        return 0
    except Exception as e:
        logger.error(f"Update failed: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
