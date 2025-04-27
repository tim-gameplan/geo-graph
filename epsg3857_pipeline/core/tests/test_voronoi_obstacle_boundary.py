#!/usr/bin/env python3
"""
Test Voronoi Obstacle Boundary Pipeline

This script tests the Voronoi obstacle boundary pipeline by:
1. Running the pipeline with test parameters
2. Verifying that the expected tables are created and populated
3. Checking that the graph is fully connected
4. Validating the Voronoi cell generation and connection assignment
"""

import os
import sys
import unittest
import subprocess
from pathlib import Path

# Add the parent directory to the path so we can import from core packages
sys.path.append(str(Path(__file__).parent.parent.parent))

from core.utils.logging_utils import setup_logger

# Set up logging
logger = setup_logger('test_voronoi_obstacle_boundary')

class TestVoronoiObstacleBoundary(unittest.TestCase):
    """
    Test case for the Voronoi obstacle boundary pipeline.
    """

    @classmethod
    def setUpClass(cls):
        """
        Set up the test environment by running the pipeline with test parameters.
        """
        logger.info("Setting up test environment...")
        
        # Reset the database
        logger.info("Resetting the database...")
        # Go back to using subprocess to run the reset script
        reset_cmd = "python epsg3857_pipeline/tools/database/reset_non_osm_tables.py --confirm"
        try:
            subprocess.run(reset_cmd, shell=True, check=True)
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to reset the database: {e}")
            raise
        
        # Run the pipeline with test parameters
        pipeline_cmd = "python epsg3857_pipeline/core/scripts/run_voronoi_obstacle_boundary_pipeline.py --skip-reset"
        try:
            subprocess.run(pipeline_cmd, shell=True, check=True)
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to run the pipeline: {e}")
            raise
    
    def run_query(self, query):
        """
        Run a SQL query and return the result.

        Args:
            query (str): SQL query to run

        Returns:
            str: Query result
        """
        cmd = f'docker exec geo-graph-db-1 psql -U gis -d gis -c "{query}" -t'
        try:
            result = subprocess.run(
                cmd,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            if result.returncode != 0:
                logger.error(f"Error executing query: {result.stderr}")
                return None
            
            return result.stdout.strip()
            
        except Exception as e:
            logger.error(f"Error executing query: {str(e)}")
            return None
    
    def test_terrain_grid_points_table(self):
        """
        Test that the terrain_grid_points table is created and populated.
        """
        query = "SELECT COUNT(*) FROM terrain_grid_points"
        result = self.run_query(query)
        self.assertIsNotNone(result, "Failed to query terrain_grid_points table")
        count = int(result)
        self.assertGreater(count, 0, "terrain_grid_points table is empty")
        logger.info(f"terrain_grid_points table has {count} rows")
    
    def test_water_obstacles_table(self):
        """
        Test that the water_obstacles table is created and populated.
        """
        query = "SELECT COUNT(*) FROM water_obstacles"
        result = self.run_query(query)
        self.assertIsNotNone(result, "Failed to query water_obstacles table")
        count = int(result)
        self.assertGreater(count, 0, "water_obstacles table is empty")
        logger.info(f"water_obstacles table has {count} rows")
    
    def test_obstacle_boundary_nodes_table(self):
        """
        Test that the obstacle_boundary_nodes table is created and populated.
        """
        query = "SELECT COUNT(*) FROM obstacle_boundary_nodes"
        result = self.run_query(query)
        self.assertIsNotNone(result, "Failed to query obstacle_boundary_nodes table")
        count = int(result)
        self.assertGreater(count, 0, "obstacle_boundary_nodes table is empty")
        logger.info(f"obstacle_boundary_nodes table has {count} rows")
    
    def test_obstacle_boundary_edges_table(self):
        """
        Test that the obstacle_boundary_edges table is created and populated.
        """
        query = "SELECT COUNT(*) FROM obstacle_boundary_edges"
        result = self.run_query(query)
        self.assertIsNotNone(result, "Failed to query obstacle_boundary_edges table")
        count = int(result)
        self.assertGreater(count, 0, "obstacle_boundary_edges table is empty")
        logger.info(f"obstacle_boundary_edges table has {count} rows")
    
    def test_voronoi_cells_table(self):
        """
        Test that the voronoi_cells table is created and populated.
        """
        query = "SELECT COUNT(*) FROM voronoi_cells"
        result = self.run_query(query)
        self.assertIsNotNone(result, "Failed to query voronoi_cells table")
        count = int(result)
        self.assertGreater(count, 0, "voronoi_cells table is empty")
        logger.info(f"voronoi_cells table has {count} rows")
    
    def test_obstacle_boundary_connection_edges_table(self):
        """
        Test that the obstacle_boundary_connection_edges table is created and populated.
        """
        query = "SELECT COUNT(*) FROM obstacle_boundary_connection_edges"
        result = self.run_query(query)
        self.assertIsNotNone(result, "Failed to query obstacle_boundary_connection_edges table")
        count = int(result)
        self.assertGreater(count, 0, "obstacle_boundary_connection_edges table is empty")
        logger.info(f"obstacle_boundary_connection_edges table has {count} rows")
    
    def test_unified_obstacle_edges_table(self):
        """
        Test that the unified_obstacle_edges table is created and populated.
        """
        query = "SELECT COUNT(*) FROM unified_obstacle_edges"
        result = self.run_query(query)
        self.assertIsNotNone(result, "Failed to query unified_obstacle_edges table")
        count = int(result)
        self.assertGreater(count, 0, "unified_obstacle_edges table is empty")
        logger.info(f"unified_obstacle_edges table has {count} rows")
    
    def test_unified_obstacle_nodes_table(self):
        """
        Test that the unified_obstacle_nodes table is created and populated.
        """
        query = "SELECT COUNT(*) FROM unified_obstacle_nodes"
        result = self.run_query(query)
        self.assertIsNotNone(result, "Failed to query unified_obstacle_nodes table")
        count = int(result)
        self.assertGreater(count, 0, "unified_obstacle_nodes table is empty")
        logger.info(f"unified_obstacle_nodes table has {count} rows")
    
    def test_graph_connectivity(self):
        """
        Test that the graph is fully connected.
        """
        query = """
        WITH RECURSIVE connected_nodes(node_id) AS (
            -- Start with the first node
            SELECT source_id FROM unified_obstacle_edges LIMIT 1
            UNION
            -- Add all nodes reachable from already connected nodes
            SELECT e.target_id
            FROM connected_nodes c
            JOIN unified_obstacle_edges e ON c.node_id = e.source_id
            WHERE e.target_id NOT IN (SELECT node_id FROM connected_nodes)
        )
        SELECT
            (SELECT COUNT(DISTINCT source_id) FROM unified_obstacle_edges) AS total_nodes,
            COUNT(*) AS connected_nodes,
            COUNT(*) * 100.0 / (SELECT COUNT(DISTINCT source_id) FROM unified_obstacle_edges) AS connectivity_percentage
        FROM
            connected_nodes;
        """
        result = self.run_query(query)
        self.assertIsNotNone(result, "Failed to query graph connectivity")
        
        # Parse the result
        parts = result.split('|')
        if len(parts) >= 3:
            total_nodes = int(parts[0].strip())
            connected_nodes = int(parts[1].strip())
            connectivity_percentage = float(parts[2].strip())
            
            self.assertGreater(total_nodes, 0, "No nodes in the graph")
            self.assertGreater(connected_nodes, 0, "No connected nodes in the graph")
            self.assertGreaterEqual(connectivity_percentage, 90.0, "Graph connectivity is less than 90%")
            
            logger.info(f"Graph connectivity: {connectivity_percentage:.2f}% ({connected_nodes}/{total_nodes} nodes)")
        else:
            self.fail("Failed to parse graph connectivity result")
    
    def test_voronoi_cell_coverage(self):
        """
        Test that the Voronoi cells cover the terrain grid points.
        """
        query = """
        SELECT COUNT(*) FROM terrain_grid_points tgp
        WHERE (tgp.hex_type = 'land' OR tgp.hex_type = 'boundary')
        AND EXISTS (
            SELECT 1 FROM voronoi_cells vc
            WHERE ST_Contains(vc.cell_geom, tgp.geom)
        );
        """
        result = self.run_query(query)
        self.assertIsNotNone(result, "Failed to query Voronoi cell coverage")
        covered_points = int(result)
        
        # Get total land and boundary points
        query = """
        SELECT COUNT(*) FROM terrain_grid_points
        WHERE hex_type = 'land' OR hex_type = 'boundary';
        """
        result = self.run_query(query)
        self.assertIsNotNone(result, "Failed to query total land and boundary points")
        total_points = int(result)
        
        self.assertGreater(total_points, 0, "No land or boundary points in the terrain grid")
        self.assertGreater(covered_points, 0, "No terrain points covered by Voronoi cells")
        
        coverage_percentage = (covered_points / total_points) * 100 if total_points > 0 else 0
        self.assertGreaterEqual(coverage_percentage, 80.0, "Voronoi cell coverage is less than 80%")
        
        logger.info(f"Voronoi cell coverage: {coverage_percentage:.2f}% ({covered_points}/{total_points} points)")
    
    def test_connection_assignment(self):
        """
        Test that the connection edges are assigned based on Voronoi cells.
        """
        query = """
        SELECT COUNT(*) FROM obstacle_boundary_connection_edges obce
        JOIN terrain_grid_points tgp ON obce.source_id = tgp.id
        JOIN obstacle_boundary_nodes obn ON obce.target_id = obn.node_id
        JOIN voronoi_cells vc ON vc.node_id = obn.node_id
        WHERE ST_Contains(vc.cell_geom, tgp.geom);
        """
        result = self.run_query(query)
        self.assertIsNotNone(result, "Failed to query connection assignment")
        valid_connections = int(result)
        
        # Get total connections
        query = "SELECT COUNT(*) FROM obstacle_boundary_connection_edges;"
        result = self.run_query(query)
        self.assertIsNotNone(result, "Failed to query total connections")
        total_connections = int(result)
        
        self.assertGreater(total_connections, 0, "No connection edges in the graph")
        self.assertGreater(valid_connections, 0, "No valid connections based on Voronoi cells")
        
        validity_percentage = (valid_connections / total_connections) * 100 if total_connections > 0 else 0
        self.assertGreaterEqual(validity_percentage, 90.0, "Connection validity is less than 90%")
        
        logger.info(f"Connection validity: {validity_percentage:.2f}% ({valid_connections}/{total_connections} connections)")

if __name__ == '__main__':
    unittest.main()
