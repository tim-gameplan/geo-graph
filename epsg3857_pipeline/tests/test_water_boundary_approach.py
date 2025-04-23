#!/usr/bin/env python3
"""
Test script for the water boundary approach.

This script tests the water boundary approach for handling water obstacles in terrain graphs.
"""

import os
import sys
import argparse
import logging
import subprocess
import json
import time
from pathlib import Path

# Add the parent directory to the path so we can import from sibling packages
sys.path.append(str(Path(__file__).parent.parent.parent))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('test_water_boundary_approach.log')
    ]
)
logger = logging.getLogger('test_water_boundary_approach')

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
        
        return True, result.stdout
    except subprocess.CalledProcessError as e:
        logger.error(f"❌ {description} failed: {e}")
        logger.error(f"Error output: {e.stderr}")
        return False, e.stderr

def run_sql_query(query, description):
    """Run a SQL query and return the result."""
    cmd = [
        "docker", "exec", "geo-graph-db-1",
        "psql",
        "-U", "gis",
        "-d", "gis",
        "-t",  # Tuple only mode
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
        
        logger.info(f"✅ SQL query '{description}' executed successfully")
        return True, result.stdout.strip()
    except subprocess.CalledProcessError as e:
        logger.error(f"❌ SQL query '{description}' failed: {e.stderr}")
        return False, e.stderr

def check_table_exists(table_name):
    """Check if a table exists in the database."""
    query = f"SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = '{table_name}');"
    success, result = run_sql_query(query, f"Check if table {table_name} exists")
    
    if success:
        return result.strip() == "t"
    else:
        logger.warning(f"Could not check if table {table_name} exists")
        return False

def check_table_row_count(table_name):
    """Check the number of rows in a table."""
    if not check_table_exists(table_name):
        logger.warning(f"Table {table_name} does not exist")
        return 0
    
    query = f"SELECT COUNT(*) FROM {table_name};"
    success, result = run_sql_query(query, f"Count rows in {table_name}")
    
    if success:
        try:
            return int(result.strip())
        except ValueError:
            logger.warning(f"Could not convert row count to integer: {result}")
            return 0
    else:
        logger.warning(f"Could not count rows in {table_name}")
        return 0

def check_graph_connectivity():
    """Check if the graph is fully connected."""
    if not check_table_exists("unified_edges"):
        logger.warning("Table unified_edges does not exist")
        return False
    
    query = """
    WITH RECURSIVE
    connected_nodes(node_id) AS (
        -- Start with the first node
        SELECT source_id FROM unified_edges LIMIT 1
        UNION
        -- Add all nodes reachable from already connected nodes
        SELECT e.target_id
        FROM connected_nodes c
        JOIN unified_edges e ON c.node_id = e.source_id
        WHERE e.target_id NOT IN (SELECT node_id FROM connected_nodes)
    )
    SELECT 
        (SELECT COUNT(DISTINCT source_id) FROM unified_edges) AS total_nodes,
        COUNT(*) AS connected_nodes,
        COUNT(*) * 100.0 / (SELECT COUNT(DISTINCT source_id) FROM unified_edges) AS connectivity_percentage
    FROM 
        connected_nodes;
    """
    
    success, result = run_sql_query(query, "Check graph connectivity")
    
    if success:
        try:
            parts = result.strip().split("|")
            if len(parts) >= 3:
                total_nodes = int(parts[0].strip())
                connected_nodes = int(parts[1].strip())
                connectivity_percentage = float(parts[2].strip())
                
                logger.info(f"Graph connectivity: {connectivity_percentage:.2f}% ({connected_nodes}/{total_nodes} nodes)")
                
                # Consider the graph fully connected if connectivity percentage is at least 99%
                return connectivity_percentage >= 99.0
            else:
                logger.warning(f"Unexpected result format: {result}")
                return False
        except (ValueError, IndexError) as e:
            logger.warning(f"Could not parse connectivity result: {e}")
            return False
    else:
        logger.warning("Could not check graph connectivity")
        return False

def test_water_boundary_approach(config_path=None, reset_database=True):
    """Test the water boundary approach."""
    logger.info("Starting water boundary approach test")
    
    # Step 1: Reset the database if requested
    if reset_database:
        success, _ = run_command(
            "python epsg3857_pipeline/scripts/reset_database.py --reset-derived",
            "Database reset"
        )
        if not success:
            logger.error("Failed to reset the database")
            return False
    
    # Step 2: Run the water boundary approach pipeline
    config_arg = f"--config {config_path}" if config_path else ""
    success, _ = run_command(
        f"python epsg3857_pipeline/run_epsg3857_pipeline.py --water-boundary {config_arg}",
        "Water boundary approach pipeline"
    )
    if not success:
        logger.error("Failed to run the water boundary approach pipeline")
        return False
    
    # Step 3: Check if the required tables exist and have rows
    required_tables = [
        "water_features_polygon",
        "water_features_line",
        "water_buffers",
        "dissolved_water_buffers",
        "water_obstacles",
        "terrain_grid",
        "terrain_grid_points",
        "terrain_edges",
        "water_boundary_points",
        "water_edges",
        "unified_edges"
    ]
    
    for table in required_tables:
        if not check_table_exists(table):
            logger.error(f"Table {table} does not exist")
            return False
        
        row_count = check_table_row_count(table)
        if row_count == 0:
            logger.error(f"Table {table} has no rows")
            return False
        
        logger.info(f"Table {table} has {row_count} rows")
    
    # Step 4: Check if the terrain grid includes water cells
    success, result = run_sql_query(
        "SELECT COUNT(*) FROM terrain_grid WHERE is_water = TRUE;",
        "Count water cells in terrain grid"
    )
    if success:
        water_cell_count = int(result.strip())
        logger.info(f"Terrain grid has {water_cell_count} water cells")
        if water_cell_count == 0:
            logger.error("Terrain grid has no water cells")
            return False
    else:
        logger.error("Failed to count water cells in terrain grid")
        return False
    
    # Step 5: Check if the terrain edges include water crossings
    success, result = run_sql_query(
        "SELECT COUNT(*) FROM terrain_edges WHERE is_water_crossing = TRUE;",
        "Count water crossing edges in terrain edges"
    )
    if success:
        water_crossing_count = int(result.strip())
        logger.info(f"Terrain edges has {water_crossing_count} water crossing edges")
        if water_crossing_count == 0:
            logger.error("Terrain edges has no water crossing edges")
            return False
    else:
        logger.error("Failed to count water crossing edges in terrain edges")
        return False
    
    # Step 6: Check if the water edges include boundary and connection edges
    success, result = run_sql_query(
        "SELECT edge_type, COUNT(*) FROM water_edges GROUP BY edge_type ORDER BY edge_type;",
        "Count edge types in water edges"
    )
    if success:
        logger.info(f"Water edges by type:\n{result}")
        if "boundary" not in result or "connection" not in result:
            logger.error("Water edges does not have both boundary and connection edges")
            return False
    else:
        logger.error("Failed to count edge types in water edges")
        return False
    
    # Step 7: Check if the unified edges table includes all edge types
    success, result = run_sql_query(
        "SELECT edge_type, COUNT(*) FROM unified_edges GROUP BY edge_type ORDER BY edge_type;",
        "Count edge types in unified edges"
    )
    if success:
        logger.info(f"Unified edges by type:\n{result}")
        if "terrain" not in result or "water_boundary" not in result or "water_connection" not in result:
            logger.error("Unified edges does not have all required edge types")
            return False
    else:
        logger.error("Failed to count edge types in unified edges")
        return False
    
    # Step 8: Check graph connectivity
    if not check_graph_connectivity():
        logger.error("Graph is not fully connected")
        return False
    
    # Step 9: Export a graph slice for visualization
    success, _ = run_command(
        "python epsg3857_pipeline/run_epsg3857_pipeline.py --export --lon -93.63 --lat 41.99 --minutes 60 --outfile water_boundary_test.graphml",
        "Export graph slice"
    )
    if not success:
        logger.error("Failed to export graph slice")
        return False
    
    # Step 10: Visualize the results
    success, _ = run_command(
        "python epsg3857_pipeline/run_epsg3857_pipeline.py --visualize --viz-mode graphml --input water_boundary_test.graphml",
        "Visualize graph"
    )
    if not success:
        logger.warning("Failed to visualize graph (this is not a critical error)")
    
    logger.info("Water boundary approach test completed successfully")
    return True

def compare_approaches(config_path=None):
    """Compare the water boundary approach with other approaches."""
    logger.info("Starting approach comparison")
    
    approaches = [
        ("standard", "Standard approach"),
        ("improved", "Improved water edge creation"),
        ("boundary", "Water boundary approach")
    ]
    
    results = {}
    
    for approach_key, approach_name in approaches:
        logger.info(f"Testing {approach_name}")
        
        # Reset the database
        success, _ = run_command(
            "python epsg3857_pipeline/scripts/reset_database.py --reset-derived",
            f"Database reset for {approach_name}"
        )
        if not success:
            logger.error(f"Failed to reset the database for {approach_name}")
            continue
        
        # Run the pipeline with the appropriate approach
        config_arg = f"--config {config_path}" if config_path else ""
        if approach_key == "standard":
            cmd = f"python epsg3857_pipeline/run_epsg3857_pipeline.py {config_arg}"
        elif approach_key == "improved":
            cmd = f"python epsg3857_pipeline/run_epsg3857_pipeline.py --improved-water-edges {config_arg}"
        elif approach_key == "boundary":
            cmd = f"python epsg3857_pipeline/run_epsg3857_pipeline.py --water-boundary {config_arg}"
        
        start_time = time.time()
        success, _ = run_command(cmd, f"Run {approach_name} pipeline")
        end_time = time.time()
        
        if not success:
            logger.error(f"Failed to run {approach_name} pipeline")
            continue
        
        # Record the execution time
        execution_time = end_time - start_time
        logger.info(f"{approach_name} execution time: {execution_time:.2f} seconds")
        
        # Check graph connectivity
        connectivity = check_graph_connectivity()
        logger.info(f"{approach_name} graph connectivity: {'Yes' if connectivity else 'No'}")
        
        # Count the number of edges
        edge_count = check_table_row_count("unified_edges")
        logger.info(f"{approach_name} edge count: {edge_count}")
        
        # Store the results
        results[approach_key] = {
            "name": approach_name,
            "execution_time": execution_time,
            "connectivity": connectivity,
            "edge_count": edge_count
        }
    
    # Print the comparison results
    logger.info("Approach Comparison Results:")
    logger.info("===========================")
    logger.info(f"{'Approach':<20} {'Execution Time':<20} {'Connectivity':<15} {'Edge Count':<15}")
    logger.info(f"{'-'*20} {'-'*20} {'-'*15} {'-'*15}")
    
    for approach_key, approach_data in results.items():
        logger.info(
            f"{approach_data['name']:<20} "
            f"{approach_data['execution_time']:.2f} seconds{' '*(20-len(f'{approach_data['execution_time']:.2f} seconds'))} "
            f"{'Yes' if approach_data['connectivity'] else 'No':<15} "
            f"{approach_data['edge_count']:<15}"
        )
    
    return True

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Test the water boundary approach for terrain graph creation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run the basic test
  python test_water_boundary_approach.py
  
  # Run the test with a custom configuration
  python test_water_boundary_approach.py --config path/to/config.json
  
  # Run the test without resetting the database
  python test_water_boundary_approach.py --no-reset
  
  # Compare different approaches
  python test_water_boundary_approach.py --compare
"""
    )
    
    # Configuration options
    parser.add_argument(
        "--config",
        default="epsg3857_pipeline/config/crs_standardized_config_boundary.json",
        help="Path to the configuration file"
    )
    parser.add_argument(
        "--no-reset",
        action="store_true",
        help="Do not reset the database before running the test"
    )
    parser.add_argument(
        "--compare",
        action="store_true",
        help="Compare the water boundary approach with other approaches"
    )
    
    args = parser.parse_args()
    
    if args.compare:
        if not compare_approaches(args.config):
            logger.error("Approach comparison failed")
            return 1
    else:
        if not test_water_boundary_approach(args.config, not args.no_reset):
            logger.error("Water boundary approach test failed")
            return 1
    
    logger.info("All tests completed successfully")
    return 0

if __name__ == "__main__":
    sys.exit(main())
