#!/usr/bin/env python3
"""
Boundary Hexagon Layer Pipeline Runner

This script runs the complete pipeline to generate a terrain graph with water obstacles
using the boundary hexagon layer approach, which preserves hexagons at water boundaries
for better connectivity.
"""

import os
import sys
import argparse
from pathlib import Path

# Add the parent directory to the path so we can import from core packages
sys.path.append(str(Path(__file__).parent))

# Import our core script
from core.scripts.run_water_obstacle_pipeline_boundary_hexagon import main as core_main

def main():
    """
    Main function to parse arguments and run the pipeline.
    """
    parser = argparse.ArgumentParser(description='Run the boundary hexagon layer pipeline')
    parser.add_argument('--config', type=str, default='epsg3857_pipeline/config/crs_standardized_config_boundary_hexagon.json',
                        help='Path to the configuration file')
    parser.add_argument('--sql-dir', type=str, default='epsg3857_pipeline/core/sql',
                        help='Path to the directory containing SQL scripts')
    parser.add_argument('--container', type=str, default='geo-graph-db-1',
                        help='Name of the Docker container')
    parser.add_argument('--verbose', action='store_true',
                        help='Print verbose output')
    parser.add_argument('--reset', action='store_true',
                        help='Reset the database before running the pipeline')
    
    args = parser.parse_args()
    
    # Reset the database if requested
    if args.reset:
        print("Resetting database...")
        reset_cmd = f"python epsg3857_pipeline/core/scripts/reset_database.py --reset-derived --confirm"
        reset_result = os.system(reset_cmd)
        if reset_result != 0:
            print(f"❌ Database reset failed: {reset_result}")
            return 1
        print("✅ Database reset completed successfully")
    
    # Run the pipeline
    return core_main()

if __name__ == '__main__':
    sys.exit(main())
