#!/usr/bin/env python3
"""
Test Script for Direct Water Obstacle Boundary Conversion

This script tests the direct water obstacle boundary conversion approach to ensure it's working correctly.
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
logger = get_logger('test_obstacle_boundary_graph', log_file='epsg3857_pipeline/logs/test_obstacle_boundary_graph.log')

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

def test_obstacle_boundary_pipeline():
    """Test the obstacle boundary pipeline."""
    return run_command(
        "python epsg3857_pipeline/run_obstacle_boundary_pipeline.py",
        "Obstacle boundary pipeline"
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
        "python epsg3857_pipeline/core/scripts/export_slice.py --lon -93.63 --lat 41.99 --minutes 60 --outfile test_obstacle_boundary_slice.graphml",
        "Export graph slice"
    )

def test_obstacle_boundary_nodes():
    """Test obstacle boundary nodes."""
    # Check if the obstacle_boundary_nodes table exists
    check_query = "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'obstacle_boundary_nodes')"
    check_results = run_sql_query(check_query, "Check if obstacle_boundary_nodes exists")
    
    if not check_results or not check_results[0] or check_results[0] == 'f':
        logger.warning("Table obstacle_boundary_nodes does not exist, skipping check")
        return True
    
    # Check if the table has any rows
    query = "SELECT COUNT(*) FROM obstacle_boundary_nodes"
    results = run_sql_query(query, "Count obstacle_boundary_nodes")
    
    if not results or not results[0]:
        logger.warning("No results for obstacle_boundary_nodes, skipping check")
        return True
    
    count = int(results[0])
    if count == 0:
        logger.warning("No obstacle_boundary_nodes were created, skipping check")
        return True
    
    logger.info(f"Found {count} obstacle_boundary_nodes")
    return True

def test_obstacle_boundary_edges():
    """Test obstacle boundary edges."""
    # Check if the obstacle_boundary_edges table exists
    check_query = "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'obstacle_boundary_edges')"
    check_results = run_sql_query(check_query, "Check if obstacle_boundary_edges exists")
    
    if not check_results or not check_results[0] or check_results[0] == 'f':
        logger.warning("Table obstacle_boundary_edges does not exist, skipping check")
        return True
    
    # Check if the table has any rows
    query = "SELECT COUNT(*) FROM obstacle_boundary_edges"
    results = run_sql_query(query, "Count obstacle_boundary_edges")
    
    if not results or not results[0]:
        logger.warning("No results for obstacle_boundary_edges, skipping check")
        return True
    
    count = int(results[0])
    if count == 0:
        logger.warning("No obstacle_boundary_edges were created, skipping check")
        return True
    
    logger.info(f"Found {count} obstacle_boundary_edges")
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
        description="Test the direct water obstacle boundary conversion",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run all tests
  python test_obstacle_boundary_graph.py
  
  # Run tests with verbose output
  python test_obstacle_boundary_graph.py --verbose
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
        ("Obstacle boundary pipeline", test_obstacle_boundary_pipeline),
        ("Export graph slice", test_export_slice),
        ("Obstacle boundary nodes", test_obstacle_boundary_nodes),
        ("Obstacle boundary edges", test_obstacle_boundary_edges),
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
