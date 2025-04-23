#!/usr/bin/env python3
"""
Test Script for Delaunay Triangulation Pipeline

This script tests the Delaunay triangulation pipeline to ensure it's working correctly.
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
        logging.FileHandler('test_delaunay_pipeline.log')
    ]
)
logger = logging.getLogger('test_delaunay_pipeline')

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

def test_delaunay_pipeline():
    """Test the Delaunay triangulation pipeline."""
    return run_command(
        "python epsg3857_pipeline/scripts/run_water_obstacle_pipeline_delaunay.py --config epsg3857_pipeline/config/delaunay_config.json --sql-dir epsg3857_pipeline/sql",
        "Delaunay triangulation pipeline"
    )

def test_export_slice():
    """Test exporting a graph slice."""
    return run_command(
        "python epsg3857_pipeline/scripts/export_slice.py --lon -93.63 --lat 41.99 --minutes 60 --outfile test_delaunay_slice.graphml",
        "Export graph slice"
    )

def test_delaunay_triangulation():
    """Test Delaunay triangulation."""
    # Check that Delaunay triangles and edges were created
    tables = [
        "delaunay_triangles",
        "delaunay_edges"
    ]
    
    for table in tables:
        query = f"SELECT COUNT(*) FROM {table}"
        results = run_sql_query(query, f"Count {table}")
        
        if not results or not results[0]:
            logger.error(f"No results for {table}")
            return False
        
        count = int(results[0])
        if count == 0:
            logger.error(f"No {table} were created")
            return False
        
        logger.info(f"Found {count} {table}")
    
    return True

def test_triangle_quality():
    """Test triangle quality."""
    # Check that triangles have reasonable shapes
    query = """
    SELECT 
        id,
        ST_Area(geom) AS area,
        ST_Perimeter(geom) AS perimeter,
        ST_Perimeter(geom)^2 / (4 * pi() * ST_Area(geom)) AS circularity
    FROM 
        delaunay_triangles
    ORDER BY 
        circularity DESC
    LIMIT 10
    """
    
    results = run_sql_query(query, "Check triangle quality")
    
    if not results:
        logger.error("No results for triangle quality")
        return False
    
    for result in results:
        if not result:
            continue
        
        parts = result.split('|')
        if len(parts) < 4:
            continue
        
        triangle_id = int(parts[0])
        area = float(parts[1])
        perimeter = float(parts[2])
        circularity = float(parts[3])
        
        # Circularity is 1 for a circle, higher for less circular shapes
        # For triangles, it should be reasonable (not extremely high)
        if circularity > 100.0:
            logger.error(f"Triangle {triangle_id} has poor quality: circularity = {circularity}")
            return False
    
    logger.info("Triangle quality is reasonable")
    return True

def test_water_obstacle_avoidance():
    """Test water obstacle avoidance."""
    # Check that triangles don't intersect with water obstacles
    query = """
    SELECT 
        COUNT(*) 
    FROM 
        delaunay_triangles dt
    JOIN 
        water_obstacles wo ON ST_Intersects(dt.geom, wo.geom)
    """
    
    results = run_sql_query(query, "Check water obstacle avoidance")
    
    if not results or not results[0]:
        logger.error("No results for water obstacle avoidance")
        return False
    
    count = int(results[0])
    if count > 0:
        logger.error(f"Found {count} triangles intersecting with water obstacles")
        return False
    
    logger.info("No triangles intersect with water obstacles")
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
        description="Test the Delaunay triangulation pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run all tests
  python test_delaunay_pipeline.py
  
  # Run tests with verbose output
  python test_delaunay_pipeline.py --verbose
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
        ("Delaunay triangulation pipeline", test_delaunay_pipeline),
        ("Export graph slice", test_export_slice),
        ("Delaunay triangulation", test_delaunay_triangulation),
        ("Triangle quality", test_triangle_quality),
        ("Water obstacle avoidance", test_water_obstacle_avoidance),
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
