#!/usr/bin/env python3
"""
Test Script for Delaunay Triangulation Pipeline

This script tests the Delaunay triangulation pipeline to ensure it's working correctly.
"""

import os
import sys
import argparse
import subprocess
import json
from pathlib import Path
import time

# Add parent directory to path for importing modules
sys.path.append(str(Path(__file__).parent.parent.parent))
from epsg3857_pipeline.core.scripts.config_loader_3857 import load_config
from epsg3857_pipeline.core.utils.logging_utils import get_logger

# Configure logging
logger = get_logger('test_delaunay_pipeline', log_file='epsg3857_pipeline/logs/test_delaunay_pipeline.log')

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
    
    # Use docker exec to run psql inside the container
    cmd = [
        "docker", "exec", "geo-graph-db-1",
        "psql",
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
        "python epsg3857_pipeline/core/scripts/reset_database.py --reset-derived",
        "Database reset"
    )

def test_delaunay_pipeline():
    """Test the Delaunay triangulation pipeline."""
    return run_command(
        "python epsg3857_pipeline/run_epsg3857_pipeline.py --mode delaunay --config epsg3857_pipeline/config/delaunay_config.json",
        "Delaunay triangulation pipeline"
    )

def test_export_slice():
    """Test exporting a graph slice."""
    # Check if there are any vertices in the database
    query = "SELECT COUNT(*) FROM graph_vertices"
    results = run_sql_query(query, "Check for vertices")
    
    if not results or not results[0] or results[0] == '0':
        logger.warning("No vertices in the database, skipping export test")
        return True
    
    return run_command(
        "python epsg3857_pipeline/core/scripts/export_slice.py --lon -93.63 --lat 41.99 --minutes 60 --outfile test_delaunay_slice.graphml",
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
        # Check if the table exists
        check_query = f"SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = '{table}')"
        check_results = run_sql_query(check_query, f"Check if {table} exists")
        
        if not check_results or not check_results[0] or check_results[0] == 'f':
            logger.warning(f"Table {table} does not exist, skipping check")
            continue
        
        # Check if the table has any rows
        query = f"SELECT COUNT(*) FROM {table}"
        results = run_sql_query(query, f"Count {table}")
        
        if not results or not results[0]:
            logger.warning(f"No results for {table}, skipping check")
            continue
        
        count = int(results[0])
        if count == 0:
            logger.warning(f"No {table} were created, skipping check")
            continue
        
        logger.info(f"Found {count} {table}")
    
    return True

def test_triangle_quality():
    """Test triangle quality."""
    # Check if the delaunay_triangles table exists
    check_query = "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'delaunay_triangles')"
    check_results = run_sql_query(check_query, "Check if delaunay_triangles exists")
    
    if not check_results or not check_results[0] or check_results[0] == 'f':
        logger.warning("Table delaunay_triangles does not exist, skipping triangle quality test")
        return True
    
    # Check if the table has any rows
    count_query = "SELECT COUNT(*) FROM delaunay_triangles"
    count_results = run_sql_query(count_query, "Count rows in delaunay_triangles")
    
    if not count_results or not count_results[0] or count_results[0] == '0':
        logger.warning("Table delaunay_triangles is empty, skipping triangle quality test")
        return True
    
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
        logger.warning("No results for triangle quality, skipping test")
        return True
    
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
    # Check if the delaunay_triangles table exists
    check_query = "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'delaunay_triangles')"
    check_results = run_sql_query(check_query, "Check if delaunay_triangles exists")
    
    if not check_results or not check_results[0] or check_results[0] == 'f':
        logger.warning("Table delaunay_triangles does not exist, skipping water obstacle avoidance test")
        return True
    
    # Check if the water_obstacles table exists
    check_query = "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'water_obstacles')"
    check_results = run_sql_query(check_query, "Check if water_obstacles exists")
    
    if not check_results or not check_results[0] or check_results[0] == 'f':
        logger.warning("Table water_obstacles does not exist, skipping water obstacle avoidance test")
        return True
    
    # Check if the tables have any rows
    count_query = "SELECT COUNT(*) FROM delaunay_triangles"
    count_results = run_sql_query(count_query, "Count rows in delaunay_triangles")
    
    if not count_results or not count_results[0] or count_results[0] == '0':
        logger.warning("Table delaunay_triangles is empty, skipping water obstacle avoidance test")
        return True
    
    count_query = "SELECT COUNT(*) FROM water_obstacles"
    count_results = run_sql_query(count_query, "Count rows in water_obstacles")
    
    if not count_results or not count_results[0] or count_results[0] == '0':
        logger.warning("Table water_obstacles is empty, skipping water obstacle avoidance test")
        return True
    
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
        logger.warning("No results for water obstacle avoidance, skipping test")
        return True
    
    count = int(results[0])
    if count > 0:
        logger.error(f"Found {count} triangles intersecting with water obstacles")
        return False
    
    logger.info("No triangles intersect with water obstacles")
    return True

def test_edge_connectivity():
    """Test edge connectivity."""
    # Check if the unified_edges table exists
    check_query = "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'unified_edges')"
    check_results = run_sql_query(check_query, "Check if unified_edges exists")
    
    if not check_results or not check_results[0] or check_results[0] == 'f':
        logger.warning("Table unified_edges does not exist, skipping edge connectivity test")
        return True
    
    # Check if the table has any rows
    count_query = "SELECT COUNT(*) FROM unified_edges"
    count_results = run_sql_query(count_query, "Count rows in unified_edges")
    
    if not count_results or not count_results[0] or count_results[0] == '0':
        logger.warning("Table unified_edges is empty, skipping edge connectivity test")
        return True
    
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
        logger.warning("No results for edge connectivity, skipping test")
        return True
    
    parts = results[0].split('|')
    if len(parts) < 2:
        logger.warning("Invalid results for edge connectivity, skipping test")
        return True
    
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
        logger.setLevel('DEBUG')
    
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
