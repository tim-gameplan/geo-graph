#!/usr/bin/env python3
"""
Hexagon Obstacle Boundary Pipeline Runner

This script runs the complete pipeline to generate a terrain graph with water obstacles
using a hexagonal grid and the obstacle boundary approach.
"""

import os
import sys
import argparse
from pathlib import Path

# Add the parent directory to the path so we can import from core packages
sys.path.append(str(Path(__file__).parent))

def main():
    """
    Parse arguments and run the core pipeline script.
    """
    parser = argparse.ArgumentParser(description='Run the hexagon obstacle boundary pipeline')
    parser.add_argument('--config', default='epsg3857_pipeline/config/hexagon_obstacle_boundary_config.json', help='Path to the configuration file')
    parser.add_argument('--sql-dir', default='epsg3857_pipeline/core/sql', help='Path to the directory containing SQL files')
    parser.add_argument('--container', default='geo-graph-db-1', help='Name of the Docker container')
    parser.add_argument('--verbose', action='store_true', help='Print verbose output')
    parser.add_argument('--skip-reset', action='store_true', help='Skip database reset')
    parser.add_argument('--visualize', action='store_true', help='Visualize the results after running the pipeline')
    parser.add_argument('--output', help='Path to save the visualization (only used with --visualize)')
    
    args = parser.parse_args()
    
    # Build the command to run the core script
    cmd = ["python", "epsg3857_pipeline/core/scripts/run_hexagon_obstacle_boundary_pipeline.py"]
    
    # Add arguments
    if args.config:
        cmd.append(f"--config={args.config}")
    if args.sql_dir:
        cmd.append(f"--sql-dir={args.sql_dir}")
    if args.container:
        cmd.append(f"--container={args.container}")
    if args.verbose:
        cmd.append("--verbose")
    if args.skip_reset:
        cmd.append("--skip-reset")
    if args.visualize:
        cmd.append("--visualize")
    if args.output:
        cmd.append(f"--output={args.output}")
    
    # Import the core script
    from core.scripts.run_hexagon_obstacle_boundary_pipeline import main as core_main
    
    # Run the core script
    return core_main()

if __name__ == "__main__":
    sys.exit(main())
