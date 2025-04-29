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
import subprocess
from pathlib import Path

# Add the parent directory to the path so we can import from core packages
sys.path.append(str(Path(__file__).parent))

# Import our core script
from core.scripts.run_water_obstacle_pipeline_boundary_hexagon import main as core_main
from core.scripts.visualize_boundary_hexagon_layer import visualize_boundary_hexagon_layer

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
    parser.add_argument('--visualize', action='store_true',
                        help='Generate a visualization after running the pipeline')
    parser.add_argument('--output', type=str,
                        help='Path to save the visualization (only used with --visualize)')
    
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
    
    # Save original sys.argv
    original_argv = sys.argv.copy()
    
    # Modify sys.argv to only include arguments that core_main expects
    sys.argv = [sys.argv[0]]
    if args.config:
        sys.argv.extend(['--config', args.config])
    if args.sql_dir:
        sys.argv.extend(['--sql-dir', args.sql_dir])
    if args.container:
        sys.argv.extend(['--container', args.container])
    if args.verbose:
        sys.argv.append('--verbose')
    
    # Run the pipeline
    try:
        result = core_main()
    finally:
        # Restore original sys.argv
        sys.argv = original_argv
    
    # Generate visualization if requested
    if args.visualize and result == 0:
        print("Generating visualization...")
        vis_success = visualize_boundary_hexagon_layer(args.output, args.container, args.verbose)
        if vis_success:
            print("✅ Visualization generated successfully")
        else:
            print("❌ Visualization generation failed")
    
    return result

if __name__ == '__main__':
    sys.exit(main())
