#!/usr/bin/env python3
"""
Test Script for EPSG:3857 Pipeline

This script tests the EPSG:3857 pipeline to ensure it's working correctly.
"""

import os
import sys
import argparse
import logging
import subprocess
import json
from pathlib import Path
import time

# Add parent directory to path for importing modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scripts.config_loader_3857 import load_config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('test_epsg3857_pipeline.log')
    ]
)
logger = logging.getLogger('test_epsg3857_pipeline')

def run_command(command, description):
    """Run a command and log the result."""
    logger.info(f"Running {description}: {command}")
    
    try:
        result = subprocess.run(
            command,
            shell=True,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        logger.info(f"✅ {description} completed successfully")
        logger.debug(f"Output: {result.stdout}")
        if result.stderr:
            logger.debug(f"Error output: {result.stderr}")
        
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"❌ {description} failed: {e}")
        logger.error(f"Error output: {e.stderr}")
        return False

def run_sql_query(query, description):
    """Run a SQL query and return the results."""
    logger.info(f"Running {description}: {query}")
    
    cmd = [
        "psql",
        "-h", "localhost",
        "-U", "gis",
        "-d", "gis",
        "-t",  # Tuple only, no header
        "-A",  # Unaligned output
        "-c", query
    ]
    
    try:
        result = subprocess.run(
            cmd,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        logger.info(f"✅ {description} completed successfully")
        return result.stdout.strip().split('\n')
    except subprocess.CalledProcessError as e:
        logger.error(f"❌ {description} failed: {e}")
        logger.error(f"Error output: {e.stderr}")
        return []

def test_database_reset():
    """Test database reset."""
    return run_command(
        "python scripts/reset_database.py --reset-derived",
        "Database reset"
    )

def test_standard_pipeline():
    """Test the standard EPSG:3857 pipeline."""
    return run_command(
        "python epsg3857_pipeline/scripts/run_water_obstacle_pipeline_crs.py --config epsg3857_pipeline/config/crs_standardized_config.json --sql-dir epsg3857_pipeline/sql",
        "Standard EPSG:3857 pipeline"
    )

def test_export_slice():
    """Test exporting a graph slice."""
    return run_command(
        "python epsg3857_pipeline/scripts/export_slice.py --lon -93.63 --lat 41.99 --minutes 60 --outfile test_slice.graphml",
        "Export graph slice"
    )

def test_crs_consistency():
    """Test CRS consistency."""
    # Check that all geometries in the database have the correct SRID
    tables = [
        "water_features",
        "water_buffers",
        "dissolved_water_buffers",
        "water_obstacles",
        "terrain_grid",
        "terrain_edges",
        "water_edges",
        "unified_edges",
        "graph_edges",
        "graph_vertices"
    ]
    
    for table in tables:
        query = f"SELECT ST_SRID(geom) FROM {table} LIMIT 1"
        results = run_sql_query(query, f"Check SRID for {table}")
        
        if not results or not results[0]:
            logger.error(f"No results for {table}")
            return False
        
        srid = results[0]
        if srid != "3857":
            logger.error(f"Incorrect SRID for {table}: {srid}, expected 3857")
            return False
    
    logger.info("All tables have the correct SRID (3857)")
    return True

def test_buffer_sizes():
    """Test buffer sizes."""
    # Check that buffer sizes are in meters
    query = """
    SELECT 
        buffer_size,
        ST_Length(ST_ExteriorRing(geom)) / buffer_size AS ratio
    FROM 
        water_buffers
    LIMIT 10
    """
    
    results = run_sql_query(query, "Check buffer sizes")
    
    if not results:
        logger.error("No results for buffer sizes")
        return False
    
    for result in results:
        if not result:
            continue
        
        parts = result.split('|')
        if len(parts) < 2:
            continue
        
        buffer_size = float(parts[0])
        ratio = float(parts[1])
        
        # The ratio of perimeter to buffer size should be reasonable
        # For a circle, it would be 2*pi (about 6.28)
        if ratio < 3.0 or ratio > 20.0:
            logger.error(f"Unreasonable buffer size ratio: {ratio}")
            return False
    
    logger.info("Buffer sizes are reasonable")
    return True

def test_edge_connectivity():
    """Test edge connectivity."""
    # Check that the graph is connected
    query = """
    SELECT 
        COUNT(*) AS edge_count,
        COUNT(DISTINCT source_id) + COUNT(DISTINCT target_id) AS vertex_count
    FROM 
        unified_edges
    """
    
    results = run_sql_query(query, "Check edge connectivity")
    
    if not results or not results[0]:
        logger.error("No results for edge connectivity")
        return False
    
    parts = results[0].split('|')
    if len(parts) < 2:
        logger.error("Invalid results for edge connectivity")
        return False
    
    edge_count = int(parts[0])
    vertex_count = int(parts[1])
    
    # A connected graph should have at least vertex_count - 1 edges
    if edge_count < vertex_count - 1:
        logger.error(f"Graph may not be connected: {edge_count} edges, {vertex_count} vertices")
        return False
    
    logger.info(f"Graph connectivity looks good: {edge_count} edges, {vertex_count} vertices")
    return True

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Test the EPSG:3857 pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run all tests
  python test_epsg3857_pipeline.py
  
  # Run tests with verbose output
  python test_epsg3857_pipeline.py --verbose
"""
    )
    
    # Test options
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose output"
    )
    
    args = parser.parse_args()
    
    # Set logging level
    if args.verbose:
        logger.setLevel(logging.DEBUG)
    
    # Run tests
    tests = [
        ("Database reset", test_database_reset),
        ("Standard EPSG:3857 pipeline", test_standard_pipeline),
        ("Export graph slice", test_export_slice),
        ("CRS consistency", test_crs_consistency),
        ("Buffer sizes", test_buffer_sizes),
        ("Edge connectivity", test_edge_connectivity)
    ]
    
    success = True
    for test_name, test_func in tests:
        logger.info(f"Running test: {test_name}")
        if not test_func():
            logger.error(f"Test failed: {test_name}")
            success = False
            break
        logger.info(f"Test passed: {test_name}")
    
    if success:
        logger.info("All tests passed!")
        return 0
    else:
        logger.error("Some tests failed!")
        return 1

if __name__ == "__main__":
    sys.exit(main())
