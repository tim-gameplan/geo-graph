#!/usr/bin/env python3
"""
Simple test to verify that the scripts can be imported without errors.
"""

import os
import sys
import unittest
from pathlib import Path

# Add the parent directory to the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestScriptImports(unittest.TestCase):
    """Test that scripts can be imported without errors."""
    
    def test_test_water_obstacle_pipeline_import(self):
        """Test that test_water_obstacle_pipeline.py can be imported."""
        try:
            from scripts.test_water_obstacle_pipeline import (
                run_command,
                reset_database,
                run_pipeline,
                visualize_results,
                update_environmental_conditions,
                analyze_water_features,
                main
            )
            self.assertTrue(True)
        except ImportError as e:
            self.fail(f"Failed to import from test_water_obstacle_pipeline.py: {e}")
    
    def test_visualize_water_obstacles_import(self):
        """Test that visualize_water_obstacles.py can be imported."""
        try:
            from scripts.visualize_water_obstacles import (
                get_db_connection,
                get_data_extent,
                get_data_for_visualization,
                create_visualization,
                main
            )
            self.assertTrue(True)
        except ImportError as e:
            self.fail(f"Failed to import from visualize_water_obstacles.py: {e}")
    
    def test_run_water_obstacle_pipeline_import(self):
        """Test that run_water_obstacle_pipeline.py can be imported."""
        try:
            from scripts.run_water_obstacle_pipeline import (
                get_db_connection,
                execute_sql_file,
                run_pipeline,
                main
            )
            self.assertTrue(True)
        except ImportError as e:
            self.fail(f"Failed to import from run_water_obstacle_pipeline.py: {e}")


if __name__ == "__main__":
    unittest.main()
