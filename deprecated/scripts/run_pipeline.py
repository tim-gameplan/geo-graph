#!/usr/bin/env python3
"""
Run the complete terrain graph pipeline.

This script executes all the SQL scripts in the correct order to:
1. Create road and water tables from OSM data
2. Build water buffers
3. Create a terrain grid
4. Create edge tables
5. Create a unified graph
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
    "create_edge_tables.sql",
    "add_source_target_columns.sql",
    "refresh_topology_simple.sql",
    "create_unified_edges.sql"
]

# Enhanced version of derive_road_and_water.sql that preserves OSM attributes
ENHANCED_DERIVE_ROAD_WATER_SQL = """
-- roads: keep all highway=* with additional attributes
DROP TABLE IF EXISTS road_edges;
CREATE TABLE road_edges AS
SELECT
    osm_id AS id,
    way AS geom,
    ST_Length(ST_Transform(way, 4326)::geography) / 18 AS cost,   -- rough 18 m/s ≈ 40 mph
    name,
    highway,
    ref,
    oneway,
    surface,
    bridge,
    tunnel,
    layer,
    access,
    service,
    junction
FROM planet_osm_line
WHERE highway IS NOT NULL;

CREATE INDEX ON road_edges USING GIST(geom);

-- water polygons: rivers, lakes, etc. with additional attributes
DROP TABLE IF EXISTS water_polys;
CREATE TABLE water_polys AS
SELECT
    osm_id AS id,
    way AS geom,
    name,
    water,
    "natural",
    waterway,
    landuse,
    CASE
        WHEN water IS NOT NULL THEN 'water'
        WHEN "natural" = 'water' THEN 'natural'
        WHEN landuse = 'reservoir' THEN 'reservoir'
        ELSE NULL
    END AS water_type
FROM planet_osm_polygon
WHERE water IS NOT NULL
   OR "natural" = 'water'
   OR landuse = 'reservoir';

CREATE INDEX ON water_polys USING GIST(geom);
"""

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

def run_pipeline_step(container_name, sql_file, sql_dir, preserve_attributes=False):
    """Run a single step of the pipeline."""
    # Special case for derive_road_and_water_fixed.sql when preserving attributes
    print(f"Processing step: {sql_file}, preserve_attributes={preserve_attributes}")
    if sql_file == "derive_road_and_water_fixed.sql" and preserve_attributes:
        print("Using enhanced version of derive_road_and_water.sql with preserved attributes")
        return execute_sql(container_name, ENHANCED_DERIVE_ROAD_WATER_SQL)
    
    # Special case for create_unified_edges.sql when preserving attributes
    if sql_file == "create_unified_edges.sql" and preserve_attributes:
        print("Using enhanced version of create_unified_edges.sql with preserved attributes")
        sql_path = os.path.join(sql_dir, "create_unified_edges_with_attributes.sql")
        if not os.path.exists(sql_path):
            print(f"Error: SQL file {sql_path} does not exist.", file=sys.stderr)
            return None
        
        container_path = f"/tmp/create_unified_edges_with_attributes.sql"
        copy_cmd = ["docker", "compose", "cp", sql_path, f"db:{container_path}"]
        run_docker_command(copy_cmd)
        
        return execute_sql_file(container_name, container_path)
    
    # Regular case: copy and execute the SQL file
    sql_path = os.path.join(sql_dir, sql_file)
    if not os.path.exists(sql_path):
        print(f"Error: SQL file {sql_path} does not exist.", file=sys.stderr)
        return None
    
    container_path = f"/tmp/{sql_file}"
    copy_cmd = ["docker", "compose", "cp", sql_path, f"db:{container_path}"]
    run_docker_command(copy_cmd)
    
    return execute_sql_file(container_name, container_path)

def run_pipeline(container_name, sql_dir, steps=None, preserve_attributes=False):
    """Run the complete pipeline."""
    if steps is None:
        steps = DEFAULT_PIPELINE
    
    for sql_file in steps:
        result = run_pipeline_step(container_name, sql_file, sql_dir, preserve_attributes)
        if not result or result.returncode != 0:
            print(f"Error executing {sql_file}:", file=sys.stderr)
            print(result.stderr if result else "Unknown error", file=sys.stderr)
            return False
    
    return True

def export_slice(lon, lat, radius_km, output_file):
    """Export a slice of the graph."""
    cmd = [
        "python", "tools/export_slice_simple.py",
        "--lon", str(lon),
        "--lat", str(lat),
        "--radius", str(radius_km),
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
    parser = argparse.ArgumentParser(description="Run the complete terrain graph pipeline.")
    
    # Pipeline options
    parser.add_argument("--sql-dir", default="sql", help="Directory containing SQL scripts")
    parser.add_argument("--preserve-attributes", action="store_true", 
                       help="Preserve OSM attributes in the road and water tables")
    
    # Export options
    parser.add_argument("--export", action="store_true", help="Export a slice after running the pipeline")
    parser.add_argument("--lon", type=float, help="Longitude for export")
    parser.add_argument("--lat", type=float, help="Latitude for export")
    parser.add_argument("--radius", type=float, default=5.0, help="Radius in kilometers for export")
    parser.add_argument("--output", default="slice.graphml", help="Output file for export")
    
    args = parser.parse_args()
    
    # Get the PostgreSQL container name
    container_name = get_db_container_name()
    if not container_name:
        print("Error: Could not find PostgreSQL container.", file=sys.stderr)
        return 1
    
    print(f"Using PostgreSQL container: {container_name}")
    
    # Run the pipeline
    if not run_pipeline(container_name, args.sql_dir, preserve_attributes=args.preserve_attributes):
        return 1
    
    # Export a slice if requested
    if args.export:
        if args.lon is None or args.lat is None:
            print("Error: --lon and --lat are required for export.", file=sys.stderr)
            return 1
        
        if not export_slice(args.lon, args.lat, args.radius, args.output):
            return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
