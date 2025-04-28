#!/usr/bin/env python3
"""
Reversed Voronoi Obstacle Boundary Pipeline Runner

This script is a simple wrapper around the core Reversed Voronoi obstacle boundary pipeline script.
It runs the pipeline with default parameters and visualizes the results.

The Reversed Voronoi approach creates Voronoi cells for boundary terrain points instead of boundary nodes,
which can lead to more natural connections and better distribution of connections across the water boundary.
"""

import os
import sys
import argparse
import subprocess
from pathlib import Path

def main():
    """
    Main function to parse arguments and run the pipeline.
    """
    parser = argparse.ArgumentParser(description='Run the Reversed Voronoi obstacle boundary pipeline')
    parser.add_argument('--config', default='epsg3857_pipeline/config/voronoi_obstacle_boundary_config.json', help='Path to the configuration file')
    parser.add_argument('--sql-dir', default='epsg3857_pipeline/core/sql', help='Path to the directory containing SQL files')
    parser.add_argument('--container', default='geo-graph-db-1', help='Name of the Docker container')
    parser.add_argument('--verbose', action='store_true', help='Print verbose output')
    parser.add_argument('--skip-reset', action='store_true', default=True, help='Skip database reset by default')
    parser.add_argument('--visualize', action='store_true', help='Visualize the results after running the pipeline')
    parser.add_argument('--output', help='Path to save the visualization (only used with --visualize)')
    parser.add_argument('--show-voronoi', action='store_true', help='Show Voronoi cells in the visualization')
    parser.add_argument('--use-robust-voronoi', action='store_true', default=True, help='Use robust Voronoi diagram generation (default: True)')
    
    args = parser.parse_args()
    
    # Build the command
    cmd = [
        "python",
        "epsg3857_pipeline/core/scripts/run_reversed_voronoi_obstacle_boundary_pipeline.py"
    ]
    
    # Add arguments
    if args.config:
        cmd.extend(["--config", args.config])
    if args.sql_dir:
        cmd.extend(["--sql-dir", args.sql_dir])
    if args.container:
        cmd.extend(["--container", args.container])
    if args.verbose:
        cmd.append("--verbose")
    if args.skip_reset:
        cmd.append("--skip-reset")
    if args.visualize:
        cmd.append("--visualize")
    if args.output:
        cmd.extend(["--output", args.output])
    if args.show_voronoi:
        cmd.append("--show-voronoi")
    if args.use_robust_voronoi:
        cmd.append("--use-robust-voronoi")
    
    # Run the command
    try:
        result = subprocess.run(
            cmd,
            check=True
        )
        return result.returncode
    except subprocess.CalledProcessError as e:
        print(f"Error running pipeline: {e}")
        return e.returncode
    except Exception as e:
        print(f"Unexpected error: {e}")
        return 1

if __name__ == '__main__':
    sys.exit(main())
