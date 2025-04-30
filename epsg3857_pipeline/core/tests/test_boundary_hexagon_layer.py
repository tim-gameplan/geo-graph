#!/usr/bin/env python3
"""
Test Boundary Hexagon Layer

This script tests the boundary hexagon layer approach, which preserves hexagons at water boundaries
and uses land portions of water hexagons to create more natural connections between terrain and water obstacles.
"""

import os
import sys
import unittest
import psycopg2
import subprocess
import time
from pathlib import Path

# Add the parent directory to the path so we can import from core packages
sys.path.append(str(Path(__file__).parent.parent.parent))

from core.utils.logging_utils import setup_logger

# Set up logging
logger = setup_logger('test_boundary_hexagon_layer')

class TestBoundaryHexagonLayer(unittest.TestCase):
    """
    Test the boundary hexagon layer approach.
    """
    
    @classmethod
    def setUpClass(cls):
        """
        Set up the test environment.
        """
        # Connect to the database
        cls.connection = psycopg2.connect(
            host='localhost',
            port=5432,
            dbname='gis',
            user='gis',
            password='gis'
        )
        
        # Reset the database
        cls._reset_database()
        
        # Run the boundary hexagon layer pipeline
        cls._run_boundary_hexagon_layer_pipeline()
    
    @classmethod
    def tearDownClass(cls):
        """
        Clean up the test environment.
        """
        # Close the database connection
        cls.connection.close()
    
    @classmethod
    def _reset_database(cls):
        """
        Reset the database to a clean state.
        """
        try:
            # Create a cursor
            cursor = cls.connection.cursor()
            
            # Drop tables
            tables = [
                'terrain_grid',
                'boundary_nodes',
                'water_boundary_nodes',
                'land_portion_nodes',
                'boundary_boundary_edges',
                'boundary_land_portion_edges',
                'land_portion_water_boundary_edges',
                'unified_boundary_nodes',
                'unified_boundary_edges',
                'unified_boundary_graph'
            ]
            
            for table in tables:
                cursor.execute(f"DROP TABLE IF EXISTS {table} CASCADE")
            
            # Commit the changes
            cls.connection.commit()
            
            # Close the cursor
            cursor.close()
            
            logger.info("Database reset successfully")
        
        except Exception as e:
            logger.error(f"Error resetting database: {str(e)}")
            cls.connection.rollback()
    
    @classmethod
    def _run_boundary_hexagon_layer_pipeline(cls):
        """
        Run the boundary hexagon layer pipeline.
        """
        try:
            # Run the pipeline
            cmd = [
                "python",
                "epsg3857_pipeline/run_boundary_hexagon_layer_pipeline.py",
                "--config",
                "epsg3857_pipeline/config/boundary_hexagon_layer_config.json",
                "--verbose"
            ]
            
            logger.info(f"Running command: {' '.join(cmd)}")
            
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            stdout, stderr = process.communicate()
            
            if process.returncode != 0:
                logger.error(f"Error running boundary hexagon layer pipeline: {stderr}")
                raise Exception(f"Error running boundary hexagon layer pipeline: {stderr}")
            
            logger.info("Boundary hexagon layer pipeline ran successfully")
        
        except Exception as e:
            logger.error(f"Error running boundary hexagon layer pipeline: {str(e)}")
            raise
    
    def test_terrain_grid_exists(self):
        """
        Test that the terrain grid table exists.
        """
        cursor = self.connection.cursor()
        cursor.execute("SELECT EXISTS(SELECT 1 FROM information_schema.tables WHERE table_name = 'terrain_grid')")
        exists = cursor.fetchone()[0]
        cursor.close()
        self.assertTrue(exists, "Terrain grid table does not exist")
    
    def test_terrain_grid_has_data(self):
        """
        Test that the terrain grid table has data.
        """
        cursor = self.connection.cursor()
        cursor.execute("SELECT COUNT(*) FROM terrain_grid")
        count = cursor.fetchone()[0]
        cursor.close()
        self.assertGreater(count, 0, "Terrain grid table has no data")
    
    def test_terrain_grid_has_hex_types(self):
        """
        Test that the terrain grid table has hex types.
        """
        cursor = self.connection.cursor()
        cursor.execute("SELECT DISTINCT hex_type FROM terrain_grid")
        hex_types = [row[0] for row in cursor.fetchall()]
        cursor.close()
        self.assertIn('land', hex_types, "Terrain grid table has no land hexagons")
        self.assertIn('boundary', hex_types, "Terrain grid table has no boundary hexagons")
        self.assertIn('water_with_land', hex_types, "Terrain grid table has no water_with_land hexagons")
    
    def test_boundary_nodes_exist(self):
        """
        Test that the boundary nodes table exists.
        """
        cursor = self.connection.cursor()
        cursor.execute("SELECT EXISTS(SELECT 1 FROM information_schema.tables WHERE table_name = 'boundary_nodes')")
        exists = cursor.fetchone()[0]
        cursor.close()
        self.assertTrue(exists, "Boundary nodes table does not exist")
    
    def test_boundary_nodes_have_data(self):
        """
        Test that the boundary nodes table has data.
        """
        cursor = self.connection.cursor()
        cursor.execute("SELECT COUNT(*) FROM boundary_nodes")
        count = cursor.fetchone()[0]
        cursor.close()
        self.assertGreater(count, 0, "Boundary nodes table has no data")
    
    def test_water_boundary_nodes_exist(self):
        """
        Test that the water boundary nodes table exists.
        """
        cursor = self.connection.cursor()
        cursor.execute("SELECT EXISTS(SELECT 1 FROM information_schema.tables WHERE table_name = 'water_boundary_nodes')")
        exists = cursor.fetchone()[0]
        cursor.close()
        self.assertTrue(exists, "Water boundary nodes table does not exist")
    
    def test_water_boundary_nodes_have_data(self):
        """
        Test that the water boundary nodes table has data.
        """
        cursor = self.connection.cursor()
        cursor.execute("SELECT COUNT(*) FROM water_boundary_nodes")
        count = cursor.fetchone()[0]
        cursor.close()
        self.assertGreater(count, 0, "Water boundary nodes table has no data")
    
    def test_land_portion_nodes_exist(self):
        """
        Test that the land portion nodes table exists.
        """
        cursor = self.connection.cursor()
        cursor.execute("SELECT EXISTS(SELECT 1 FROM information_schema.tables WHERE table_name = 'land_portion_nodes')")
        exists = cursor.fetchone()[0]
        cursor.close()
        self.assertTrue(exists, "Land portion nodes table does not exist")
    
    def test_land_portion_nodes_have_data(self):
        """
        Test that the land portion nodes table has data.
        """
        cursor = self.connection.cursor()
        cursor.execute("SELECT COUNT(*) FROM land_portion_nodes")
        count = cursor.fetchone()[0]
        cursor.close()
        self.assertGreater(count, 0, "Land portion nodes table has no data")
    
    def test_boundary_boundary_edges_exist(self):
        """
        Test that the boundary-to-boundary edges table exists.
        """
        cursor = self.connection.cursor()
        cursor.execute("SELECT EXISTS(SELECT 1 FROM information_schema.tables WHERE table_name = 'boundary_boundary_edges')")
        exists = cursor.fetchone()[0]
        cursor.close()
        self.assertTrue(exists, "Boundary-to-boundary edges table does not exist")
    
    def test_boundary_boundary_edges_have_data(self):
        """
        Test that the boundary-to-boundary edges table has data.
        """
        cursor = self.connection.cursor()
        cursor.execute("SELECT COUNT(*) FROM boundary_boundary_edges")
        count = cursor.fetchone()[0]
        cursor.close()
        self.assertGreater(count, 0, "Boundary-to-boundary edges table has no data")
    
    def test_boundary_land_portion_edges_exist(self):
        """
        Test that the boundary-to-land-portion edges table exists.
        """
        cursor = self.connection.cursor()
        cursor.execute("SELECT EXISTS(SELECT 1 FROM information_schema.tables WHERE table_name = 'boundary_land_portion_edges')")
        exists = cursor.fetchone()[0]
        cursor.close()
        self.assertTrue(exists, "Boundary-to-land-portion edges table does not exist")
    
    def test_boundary_land_portion_edges_have_data(self):
        """
        Test that the boundary-to-land-portion edges table has data.
        """
        cursor = self.connection.cursor()
        cursor.execute("SELECT COUNT(*) FROM boundary_land_portion_edges")
        count = cursor.fetchone()[0]
        cursor.close()
        self.assertGreater(count, 0, "Boundary-to-land-portion edges table has no data")
    
    def test_land_portion_water_boundary_edges_exist(self):
        """
        Test that the land-portion-to-water-boundary edges table exists.
        """
        cursor = self.connection.cursor()
        cursor.execute("SELECT EXISTS(SELECT 1 FROM information_schema.tables WHERE table_name = 'land_portion_water_boundary_edges')")
        exists = cursor.fetchone()[0]
        cursor.close()
        self.assertTrue(exists, "Land-portion-to-water-boundary edges table does not exist")
    
    def test_land_portion_water_boundary_edges_have_data(self):
        """
        Test that the land-portion-to-water-boundary edges table has data.
        """
        cursor = self.connection.cursor()
        cursor.execute("SELECT COUNT(*) FROM land_portion_water_boundary_edges")
        count = cursor.fetchone()[0]
        cursor.close()
        self.assertGreater(count, 0, "Land-portion-to-water-boundary edges table has no data")
    
    def test_unified_boundary_graph_exists(self):
        """
        Test that the unified boundary graph table exists.
        """
        cursor = self.connection.cursor()
        cursor.execute("SELECT EXISTS(SELECT 1 FROM information_schema.tables WHERE table_name = 'unified_boundary_graph')")
        exists = cursor.fetchone()[0]
        cursor.close()
        self.assertTrue(exists, "Unified boundary graph table does not exist")
    
    def test_unified_boundary_graph_has_data(self):
        """
        Test that the unified boundary graph table has data.
        """
        cursor = self.connection.cursor()
        cursor.execute("SELECT COUNT(*) FROM unified_boundary_graph")
        count = cursor.fetchone()[0]
        cursor.close()
        self.assertGreater(count, 0, "Unified boundary graph table has no data")
    
    def test_unified_boundary_graph_has_nodes_and_edges(self):
        """
        Test that the unified boundary graph table has both nodes and edges.
        """
        cursor = self.connection.cursor()
        cursor.execute("SELECT DISTINCT element_type FROM unified_boundary_graph")
        element_types = [row[0] for row in cursor.fetchall()]
        cursor.close()
        self.assertIn('node', element_types, "Unified boundary graph table has no nodes")
        self.assertIn('edge', element_types, "Unified boundary graph table has no edges")
    
    def test_unified_boundary_graph_has_all_node_types(self):
        """
        Test that the unified boundary graph table has all node types.
        """
        cursor = self.connection.cursor()
        cursor.execute("SELECT DISTINCT element_subtype FROM unified_boundary_graph WHERE element_type = 'node'")
        node_types = [row[0] for row in cursor.fetchall()]
        cursor.close()
        self.assertIn('boundary', node_types, "Unified boundary graph table has no boundary nodes")
        self.assertIn('water_boundary', node_types, "Unified boundary graph table has no water boundary nodes")
        self.assertIn('land_portion', node_types, "Unified boundary graph table has no land portion nodes")
    
    def test_unified_boundary_graph_has_all_edge_types(self):
        """
        Test that the unified boundary graph table has all edge types.
        """
        cursor = self.connection.cursor()
        cursor.execute("SELECT DISTINCT element_subtype FROM unified_boundary_graph WHERE element_type = 'edge'")
        edge_types = [row[0] for row in cursor.fetchall()]
        cursor.close()
        self.assertIn('boundary-boundary', edge_types, "Unified boundary graph table has no boundary-to-boundary edges")
        self.assertIn('boundary-land_portion', edge_types, "Unified boundary graph table has no boundary-to-land-portion edges")
        self.assertIn('land_portion-water_boundary', edge_types, "Unified boundary graph table has no land-portion-to-water-boundary edges")

if __name__ == '__main__':
    unittest.main()
