#!/usr/bin/env python3
"""
Test script for Delaunay triangulation implementation.

This script tests the Delaunay triangulation implementation for terrain grid generation.
It verifies that:
1. The triangulation is created correctly
2. The terrain grid points are generated correctly
3. The terrain edges are created correctly
4. The triangulation follows water buffer boundaries
"""

import os
import sys
import unittest
import logging
import psycopg2
from psycopg2.extras import DictCursor

# Add the parent directory to the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from planning.scripts.run_water_obstacle_pipeline_delaunay import run_pipeline

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('test_delaunay.log')
    ]
)
logger = logging.getLogger('test_delaunay')


class TestDelaunayTriangulation(unittest.TestCase):
    """Test case for Delaunay triangulation implementation."""
    
    @classmethod
    def setUpClass(cls):
        """Set up the test case."""
        # Connect to the database
        cls.conn_string = os.environ.get('PG_URL', 'postgresql://gis:gis@localhost:5432/gis')
        cls.conn = psycopg2.connect(cls.conn_string)
        
        # Run the pipeline with Delaunay triangulation
        config_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            'config/crs_standardized_config.json'
        )
        sql_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            'sql'
        )
        
        # Skip the pipeline execution if the tables already exist
        with cls.conn.cursor() as cur:
            cur.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'terrain_triangulation'
                )
            """)
            has_triangulation = cur.fetchone()[0]
            
            if not has_triangulation:
                logger.info("Running pipeline with Delaunay triangulation")
                run_pipeline(
                    config_path=config_path,
                    sql_dir=sql_dir,
                    conn_string=cls.conn_string
                )
            else:
                logger.info("Delaunay triangulation tables already exist, skipping pipeline execution")
    
    @classmethod
    def tearDownClass(cls):
        """Tear down the test case."""
        cls.conn.close()
    
    def test_triangulation_exists(self):
        """Test that the triangulation table exists and has rows."""
        with self.conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM terrain_triangulation")
            count = cur.fetchone()[0]
            self.assertGreater(count, 0, "Triangulation table should have rows")
    
    def test_terrain_grid_exists(self):
        """Test that the terrain grid table exists and has rows."""
        with self.conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM terrain_grid")
            count = cur.fetchone()[0]
            self.assertGreater(count, 0, "Terrain grid table should have rows")
    
    def test_terrain_edges_exists(self):
        """Test that the terrain edges table exists and has rows."""
        with self.conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM terrain_edges")
            count = cur.fetchone()[0]
            self.assertGreater(count, 0, "Terrain edges table should have rows")
    
    def test_triangulation_geometry_type(self):
        """Test that the triangulation geometry type is Polygon."""
        with self.conn.cursor() as cur:
            cur.execute("""
                SELECT ST_GeometryType(geom) 
                FROM terrain_triangulation 
                LIMIT 1
            """)
            geom_type = cur.fetchone()[0]
            self.assertEqual(geom_type, 'ST_Polygon', "Triangulation geometry type should be Polygon")
    
    def test_terrain_grid_geometry_type(self):
        """Test that the terrain grid geometry type is Point."""
        with self.conn.cursor() as cur:
            cur.execute("""
                SELECT ST_GeometryType(geom) 
                FROM terrain_grid 
                LIMIT 1
            """)
            geom_type = cur.fetchone()[0]
            self.assertEqual(geom_type, 'ST_Point', "Terrain grid geometry type should be Point")
    
    def test_terrain_edges_geometry_type(self):
        """Test that the terrain edges geometry type is LineString."""
        with self.conn.cursor() as cur:
            cur.execute("""
                SELECT ST_GeometryType(geom) 
                FROM terrain_edges 
                LIMIT 1
            """)
            geom_type = cur.fetchone()[0]
            self.assertEqual(geom_type, 'ST_LineString', "Terrain edges geometry type should be LineString")
    
    def test_terrain_grid_points_not_in_water(self):
        """Test that terrain grid points do not intersect with water buffers."""
        with self.conn.cursor() as cur:
            cur.execute("""
                SELECT COUNT(*) 
                FROM terrain_grid tg
                JOIN water_buf_dissolved wb ON ST_Intersects(tg.geom, wb.geom)
            """)
            count = cur.fetchone()[0]
            self.assertEqual(count, 0, "Terrain grid points should not intersect with water buffers")
    
    def test_terrain_edges_not_cross_water(self):
        """Test that terrain edges do not cross water buffers."""
        with self.conn.cursor() as cur:
            cur.execute("""
                SELECT COUNT(*) 
                FROM terrain_edges te
                JOIN water_buf_dissolved wb ON ST_Intersects(te.geom, wb.geom)
                WHERE ST_Crosses(te.geom, wb.geom)
            """)
            count = cur.fetchone()[0]
            self.assertEqual(count, 0, "Terrain edges should not cross water buffers")
    
    def test_terrain_edges_connectivity(self):
        """Test that terrain edges form a connected graph."""
        with self.conn.cursor() as cur:
            # Count the number of distinct source and target IDs
            cur.execute("""
                SELECT COUNT(DISTINCT id) 
                FROM (
                    SELECT source_id AS id FROM terrain_edges
                    UNION
                    SELECT target_id AS id FROM terrain_edges
                ) AS ids
            """)
            node_count = cur.fetchone()[0]
            
            # Count the number of edges
            cur.execute("SELECT COUNT(*) FROM terrain_edges")
            edge_count = cur.fetchone()[0]
            
            # A connected graph should have at least n-1 edges for n nodes
            self.assertGreaterEqual(edge_count, node_count - 1, 
                                   "Terrain edges should form a connected graph")
    
    def test_triangulation_quality(self):
        """Test the quality of the triangulation."""
        with self.conn.cursor() as cur:
            # Calculate the minimum angle of each triangle
            cur.execute("""
                WITH triangle_angles AS (
                    SELECT 
                        id,
                        degrees(
                            LEAST(
                                ST_Angle(
                                    ST_PointN(ST_ExteriorRing(geom), 1),
                                    ST_PointN(ST_ExteriorRing(geom), 2),
                                    ST_PointN(ST_ExteriorRing(geom), 3)
                                ),
                                ST_Angle(
                                    ST_PointN(ST_ExteriorRing(geom), 2),
                                    ST_PointN(ST_ExteriorRing(geom), 3),
                                    ST_PointN(ST_ExteriorRing(geom), 1)
                                ),
                                ST_Angle(
                                    ST_PointN(ST_ExteriorRing(geom), 3),
                                    ST_PointN(ST_ExteriorRing(geom), 1),
                                    ST_PointN(ST_ExteriorRing(geom), 2)
                                )
                            )
                        ) AS min_angle
                    FROM (
                        SELECT 
                            ROW_NUMBER() OVER () AS id,
                            geom
                        FROM terrain_triangulation
                        LIMIT 100 -- Limit to 100 triangles for performance
                    ) AS triangles
                )
                SELECT AVG(min_angle) FROM triangle_angles
            """)
            avg_min_angle = cur.fetchone()[0]
            
            # Delaunay triangulation should maximize the minimum angle
            # A good Delaunay triangulation should have an average minimum angle > 30 degrees
            self.assertGreater(avg_min_angle, 30, 
                              "Average minimum angle should be greater than 30 degrees")
    
    def test_edge_length_distribution(self):
        """Test the distribution of edge lengths."""
        with self.conn.cursor() as cur:
            # Calculate edge length statistics
            cur.execute("""
                SELECT 
                    MIN(length_m) AS min_length,
                    MAX(length_m) AS max_length,
                    AVG(length_m) AS avg_length,
                    STDDEV(length_m) AS stddev_length
                FROM terrain_edges
            """)
            stats = cur.fetchone()
            min_length, max_length, avg_length, stddev_length = stats
            
            # Edge lengths should be reasonable
            self.assertGreater(min_length, 0, "Minimum edge length should be greater than 0")
            self.assertLess(max_length, 1000, "Maximum edge length should be less than 1000 meters")
            
            # Coefficient of variation (stddev/mean) should be reasonable
            cv = stddev_length / avg_length if avg_length > 0 else float('inf')
            self.assertLess(cv, 1.0, "Coefficient of variation should be less than 1.0")


if __name__ == '__main__':
    unittest.main()
