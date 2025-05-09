#!/usr/bin/env python3
"""
Run Latest Pipeline

This script runs the most recent pipeline to create derived tables in PostGIS from the loaded OSM data.
It currently uses the renamed tables pipeline, which implements the Pipeline Stage Prefixing naming convention.
"""

import os
import sys
import argparse
from pathlib import Path

def main():
    """
    Main function to parse arguments and run the pipeline.
    """
    parser = argparse.ArgumentParser(description='Run the most recent pipeline to create derived tables in PostGIS from the loaded OSM data')
    parser.add_argument('--verbose', action='store_true',
                        help='Print verbose output')
    parser.add_argument('--no-compatibility-views', action='store_true',
                        help='Do not create backward compatibility views')
    parser.add_argument('--container', type=str, default='db',
                        help='Name of the Docker container')
    
    args = parser.parse_args()
    
    # Get the directory of this script
    script_dir = Path(__file__).parent.resolve()
    
    # Path to the renamed tables pipeline script
    pipeline_script = script_dir / "run_renamed_tables_pipeline.py"
    
    # Build the command
    cmd = [sys.executable, str(pipeline_script)]
    
    if args.verbose:
        cmd.append('--verbose')
    
    if args.no_compatibility_views:
        cmd.append('--no-compatibility-views')
    
    if args.container != 'db':
        cmd.extend(['--container', args.container])
    
    # Execute the pipeline script with the arguments
    print(f"Running the latest pipeline: {' '.join(cmd)}")
    os.execv(sys.executable, cmd)

if __name__ == '__main__':
    main()