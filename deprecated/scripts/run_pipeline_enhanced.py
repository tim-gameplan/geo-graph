#!/usr/bin/env python3
"""
Enhanced version of run_pipeline.py with improved cost calculation for isochrone analysis.

This script executes all the SQL scripts in the correct order to:
1. Create road and water tables from OSM data with additional attributes
2. Build water buffers
3. Create a terrain grid
4. Create edge tables
5. Create a unified graph with all attributes preserved
"""

import argparse
import os
import subprocess
import sys
import tempfile
from pathlib import Path

# Default SQL scripts to run in order
DEFAULT_PIPELINE = [
    "derive_road_and_water_fixed.sql",
    "build_water_buffers_simple.sql",
    "create_grid_profile.sql",
    "build_terrain_grid_simple.sql",
    "create_edge_tables_enhanced.sql",
    "add_source_target_columns.sql",
    "refresh_topology_simple.sql",
    "create_unified_edges.sql"
]

# Enhanced pipeline with improved cost calculation
ENHANCED_PIPELINE = [
    "derive_road_and_water_enhanced_fixed.sql",  # Enhanced version with improved cost calculation
    "build_water_buffers_simple.sql",
    "create_grid_profile.sql",
    "build_terrain_grid_simple.sql",
    "create_edge_tables_enhanced.sql",
    "add_source_target_columns.sql",
    "create_unified_edges_enhanced_fixed_v2.sql",  # Enhanced version with additional attributes
    "refresh_topology_fixed_v2.sql"  # Fixed version that ensures all geometries have the same SRID
]

def run_docker_command(cmd, check=True):
    """Run a Docker command and return the result."""
    try:
        result = subprocess.run(cmd, 
                               stdout=subprocess.PIPE, 
                               stderr=subprocess.PIPE, 
                               text=True,
                               check=check)
        return result
    except subprocess.SubprocessError as e:
        print(f"Error executing command: {e}", file=sys.stderr)
        return None

def get_db_container_name():
    """Get the name of the PostgreSQL container."""
    result = run_docker_command(["docker", "compose", "ps", "--services"])
    if not result or result.returncode != 0:
        return None
    
    services = result.stdout.strip().split('\n')
    for service in services:
        if service == 'db':
            # Get the actual container name
            result = run_docker_command(["docker", "compose", "ps", "db", "--format", "{{.Name}}"])
            if result and result.returncode == 0:
                return result.stdout.strip()
    
    return None

def execute_sql_file(container_name, sql_file, database="gis", user="gis"):
    """Execute a SQL file in the PostgreSQL container."""
    cmd = [
        "docker", "exec", container_name,
        "psql", "-U", user, "-d", database, "-f", sql_file
    ]
    
    print(f"Executing SQL file: {sql_file}")
    return run_docker_command(cmd)

def execute_sql(container_name, sql, database="gis", user="gis"):
    """Execute SQL in the PostgreSQL container."""
    # Print the SQL for debugging
    print("Executing SQL:")
    print(sql)
    
    # Create a temporary file with the SQL
    with tempfile.NamedTemporaryFile(mode='w', suffix='.sql', delete=False) as temp:
        temp.write(sql)
        temp_path = temp.name
    
    # Copy the file to the container
    container_path = f"/tmp/{os.path.basename(temp_path)}"
    copy_cmd = ["docker", "compose", "cp", temp_path, f"db:{container_path}"]
    run_docker_command(copy_cmd)
    
    # Execute the SQL file
    result = execute_sql_file(container_name, container_path, database, user)
    
    # Print the result for debugging
    if result:
        print(f"SQL execution result: returncode={result.returncode}")
        if result.stderr:
            print(f"SQL execution stderr: {result.stderr}")
    
    # Clean up
    os.unlink(temp_path)
    
    return result

def run_pipeline_step(container_name, sql_file, sql_dir):
    """Run a single step of the pipeline."""
    # Regular case: copy and execute the SQL file
    sql_path = os.path.join(sql_dir, sql_file)
    if not os.path.exists(sql_path):
        print(f"Error: SQL file {sql_path} does not exist.", file=sys.stderr)
        return None
    
    container_path = f"/tmp/{sql_file}"
    copy_cmd = ["docker", "compose", "cp", sql_path, f"db:{container_path}"]
    run_docker_command(copy_cmd)
    
    return execute_sql_file(container_name, container_path)

def run_pipeline(container_name, sql_dir, steps=None, enhanced=False):
    """Run the complete pipeline."""
    if steps is None:
        steps = ENHANCED_PIPELINE if enhanced else DEFAULT_PIPELINE
    
    for sql_file in steps:
        result = run_pipeline_step(container_name, sql_file, sql_dir)
        if not result or result.returncode != 0:
            print(f"Error executing {sql_file}:", file=sys.stderr)
            print(result.stderr if result else "Unknown error", file=sys.stderr)
            return False
    
    return True

def export_slice(lon, lat, minutes, output_file, enhanced=False):
    """Export a slice of the graph."""
    script = "tools/export_slice_enhanced_fixed.py" if enhanced else "tools/export_slice.py"
    
    if not os.path.exists(script):
        print(f"Error: Script {script} does not exist.", file=sys.stderr)
        if enhanced:
            print("Falling back to tools/export_slice.py", file=sys.stderr)
            script = "tools/export_slice.py"
            if not os.path.exists(script):
                print(f"Error: Script {script} does not exist.", file=sys.stderr)
                return False
    
    cmd = [
        "python", script,
        "--lon", str(lon),
        "--lat", str(lat),
        "--minutes", str(minutes),
        "--outfile", output_file
    ]
    
    print(f"Exporting slice: {' '.join(cmd)}")
    
    try:
        subprocess.run(cmd, check=True)
        print(f"Slice exported to {output_file}")
        return True
    except subprocess.SubprocessError as e:
        print(f"Error exporting slice: {e}", file=sys.stderr)
        return False

def main():
    parser = argparse.ArgumentParser(description="Run the enhanced terrain graph pipeline with improved cost calculation.")
    
    # Pipeline options
    parser.add_argument("--sql-dir", default="sql", help="Directory containing SQL scripts")
    parser.add_argument("--enhanced", action="store_true", default=True,
                       help="Use enhanced pipeline with improved cost calculation (default: True)")
    
    # Export options
    parser.add_argument("--export", action="store_true", help="Export a slice after running the pipeline")
    parser.add_argument("--lon", type=float, help="Longitude for export")
    parser.add_argument("--lat", type=float, help="Latitude for export")
    parser.add_argument("--minutes", type=int, default=60, help="Travel time in minutes for export")
    parser.add_argument("--output", default="isochrone.graphml", help="Output file for export")
    
    args = parser.parse_args()
    
    # Get the PostgreSQL container name
    container_name = get_db_container_name()
    if not container_name:
        print("Error: Could not find PostgreSQL container.", file=sys.stderr)
        return 1
    
    print(f"Using PostgreSQL container: {container_name}")
    
    # Run the pipeline
    if not run_pipeline(container_name, args.sql_dir, enhanced=args.enhanced):
        return 1
    
    # Export a slice if requested
    if args.export:
        if args.lon is None or args.lat is None:
            print("Error: --lon and --lat are required for export.", file=sys.stderr)
            return 1
        
        if not export_slice(args.lon, args.lat, args.minutes, args.output, enhanced=args.enhanced):
            return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
