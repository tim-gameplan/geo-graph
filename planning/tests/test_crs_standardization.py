#!/usr/bin/env python3
"""
Test script for the CRS standardization implementation.

This script:
1. Connects to the PostgreSQL database
2. Runs a series of tests to verify the CRS standardization
3. Reports the results
"""

import os
import sys
import argparse
import logging
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
        logging.FileHandler('test_crs_standardization.log')
    ]
)
logger = logging.getLogger('test_crs_standardization')


def get_db_connection(conn_string=None):
    """Create a database connection."""
    if conn_string is None:
        conn_string = os.environ.get('PG_URL', 'postgresql://gis:gis@localhost:5432/gis')
    
    try:
        conn = psycopg2.connect(conn_string)
        logger.info(f"Connected to database: {conn_string.split('@')[-1]}")
        return conn
    except Exception as e:
        logger.error(f"Error connecting to database: {e}")
        raise


def test_table_exists(conn, table_name):
    """Test if a table exists in the database."""
    with conn.cursor() as cur:
        cur.execute(f"SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = '{table_name}')")
        exists = cur.fetchone()[0]
    
    if exists:
        logger.info(f"✅ Table '{table_name}' exists")
        return True
    else:
        logger.error(f"❌ Table '{table_name}' does not exist")
        return False


def test_geometry_srid(conn, table_name, geom_column='geom', expected_srid=3857):
    """Test if a geometry column has the expected SRID."""
    if not test_table_exists(conn, table_name):
        return False
    
    with conn.cursor() as cur:
        cur.execute(f"SELECT ST_SRID({geom_column}) FROM {table_name} LIMIT 1")
        srid = cur.fetchone()[0]
    
    if srid == expected_srid:
        logger.info(f"✅ Geometry column '{geom_column}' in table '{table_name}' has SRID {srid}")
        return True
    else:
        logger.error(f"❌ Geometry column '{geom_column}' in table '{table_name}' has SRID {srid}, expected {expected_srid}")
        return False


def test_buffer_distances(conn, buffer_table='water_buf', geom_column='geom'):
    """Test if buffer distances are reasonable in meters."""
    if not test_table_exists(conn, buffer_table):
        return False
    
    with conn.cursor() as cur:
        cur.execute(f"""
            SELECT 
                water_type, 
                buffer_rule_applied,
                buffer_size_m,
                ST_Area({geom_column}) / (PI() * buffer_size_m * buffer_size_m) AS area_ratio
            FROM {buffer_table}
            WHERE buffer_size_m > 0
            LIMIT 10
        """)
        results = cur.fetchall()
    
    if not results:
        logger.error(f"❌ No buffer results found in table '{buffer_table}'")
        return False
    
    all_valid = True
    for water_type, rule, size, ratio in results:
        # For a perfect circle, area / (pi * r^2) = 1
        # Allow some deviation due to geometry complexity
        if 0.5 <= ratio <= 2.0:
            logger.info(f"✅ Buffer for {water_type} ({rule}) with size {size}m has reasonable area ratio: {ratio:.2f}")
        else:
            logger.error(f"❌ Buffer for {water_type} ({rule}) with size {size}m has unusual area ratio: {ratio:.2f}")
            all_valid = False
    
    return all_valid


def test_dissolve_results(conn, dissolved_table='water_buf_dissolved', original_table='water_buf'):
    """Test if the dissolve operation produced reasonable results."""
    if not test_table_exists(conn, dissolved_table) or not test_table_exists(conn, original_table):
        return False
    
    with conn.cursor() as cur:
        cur.execute(f"""
            SELECT 
                (SELECT COUNT(*) FROM {original_table}) AS original_count,
                (SELECT COUNT(*) FROM {dissolved_table}) AS dissolved_count,
                (SELECT SUM(ST_Area(geom)) FROM {original_table}) AS original_area,
                (SELECT SUM(ST_Area(geom)) FROM {dissolved_table}) AS dissolved_area
        """)
        original_count, dissolved_count, original_area, dissolved_area = cur.fetchone()
    
    if dissolved_count < original_count:
        logger.info(f"✅ Dissolve reduced feature count from {original_count} to {dissolved_count}")
    else:
        logger.error(f"❌ Dissolve did not reduce feature count: {original_count} to {dissolved_count}")
        return False
    
    # Area should be similar (within 10%)
    area_ratio = dissolved_area / original_area if original_area else 0
    if 0.9 <= area_ratio <= 1.1:
        logger.info(f"✅ Dissolve preserved total area: ratio = {area_ratio:.2f}")
    else:
        logger.error(f"❌ Dissolve significantly changed total area: ratio = {area_ratio:.2f}")
        return False
    
    return True


def run_tests(conn_string=None):
    """Run all tests."""
    conn = get_db_connection(conn_string)
    
    try:
        # Test tables exist
        tables_exist = all([
            test_table_exists(conn, 'water_features'),
            test_table_exists(conn, 'water_buf'),
            test_table_exists(conn, 'water_buf_dissolved')
        ])
        
        if not tables_exist:
            logger.error("❌ Required tables do not exist. Run the pipeline first.")
            return False
        
        # Test geometry SRIDs
        srids_correct = all([
            test_geometry_srid(conn, 'water_features'),
            test_geometry_srid(conn, 'water_buf'),
            test_geometry_srid(conn, 'water_buf_dissolved')
        ])
        
        # Test buffer distances
        buffers_valid = test_buffer_distances(conn)
        
        # Test dissolve results
        dissolve_valid = test_dissolve_results(conn)
        
        # Overall result
        if srids_correct and buffers_valid and dissolve_valid:
            logger.info("✅ All tests passed! CRS standardization is working correctly.")
            return True
        else:
            logger.error("❌ Some tests failed. See log for details.")
            return False
    
    finally:
        conn.close()
        logger.info("Database connection closed")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Test the CRS standardization implementation")
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
    
    try:
        success = run_tests(args.conn_string)
        return 0 if success else 1
    except Exception as e:
        logger.error(f"Tests failed with exception: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
