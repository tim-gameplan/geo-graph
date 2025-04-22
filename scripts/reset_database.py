#!/usr/bin/env python3
"""
Reset the PostGIS database and optionally reimport OSM data.

This script provides options to:
1. Reset the entire database
2. Reset only the derived tables
3. Reimport OSM data from a specified file
"""

import argparse
import os
import subprocess
import sys
import time
from pathlib import Path

# SQL for resetting only the derived tables
RESET_DERIVED_TABLES_SQL = """
-- Original pipeline tables
DROP TABLE IF EXISTS road_edges CASCADE;
DROP TABLE IF EXISTS water_polys CASCADE;
DROP TABLE IF EXISTS water_buf CASCADE;
DROP TABLE IF EXISTS terrain_grid CASCADE;
DROP TABLE IF EXISTS water_edges CASCADE;
DROP TABLE IF EXISTS terrain_edges CASCADE;
DROP TABLE IF EXISTS unified_edges CASCADE;
DROP TABLE IF EXISTS grid_profile CASCADE;

-- Water obstacle pipeline tables
DROP TABLE IF EXISTS water_features CASCADE;
DROP TABLE IF EXISTS water_buf_dissolved CASCADE;
DROP TABLE IF EXISTS environmental_conditions CASCADE;
DROP TABLE IF EXISTS water_edges_original CASCADE;
DROP VIEW IF EXISTS current_environment CASCADE;

-- Water edge comparison tables
DROP TABLE IF EXISTS water_edges_original CASCADE;
DROP TABLE IF EXISTS water_edges_dissolved CASCADE;
"""

# SQL for detecting and dropping any additional derived tables
DETECT_DERIVED_TABLES_SQL = """
SELECT string_agg('DROP TABLE IF EXISTS ' || tablename || ' CASCADE;', E'\n') AS drop_tables_sql
FROM pg_tables
WHERE schemaname = 'public'
  AND tablename NOT IN (
    'spatial_ref_sys', 'geography_columns', 'geometry_columns', 
    'planet_osm_line', 'planet_osm_nodes', 'planet_osm_point', 
    'planet_osm_polygon', 'planet_osm_rels', 'planet_osm_roads', 
    'planet_osm_ways', 'osm2pgsql_properties'
  );
"""

# SQL for detecting and dropping any additional views
DETECT_DERIVED_VIEWS_SQL = """
SELECT string_agg('DROP VIEW IF EXISTS ' || viewname || ' CASCADE;', E'\n') AS drop_views_sql
FROM pg_views
WHERE schemaname = 'public'
  AND viewname NOT IN ('geography_columns', 'geometry_columns');
"""

# SQL for creating extensions
CREATE_EXTENSIONS_SQL = """
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS pgrouting;
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

def execute_sql(container_name, sql, database="gis", user="gis"):
    """Execute SQL in the PostgreSQL container."""
    cmd = [
        "docker", "exec", container_name,
        "psql", "-U", user, "-d", database, "-c", sql
    ]
    
    return run_docker_command(cmd)

def reset_entire_database(container_name):
    """Reset the entire database."""
    print("Resetting entire database...")
    
    # Drop and recreate the database
    execute_sql(container_name, "DROP DATABASE IF EXISTS gis;", database="postgres")
    execute_sql(container_name, "CREATE DATABASE gis;", database="postgres")
    
    # Create extensions
    execute_sql(container_name, CREATE_EXTENSIONS_SQL)
    
    print("Database reset complete.")
    return True

def reset_derived_tables(container_name):
    """Reset only the derived tables."""
    print("Resetting derived tables...")
    
    # First, drop the known derived tables
    execute_sql(container_name, RESET_DERIVED_TABLES_SQL)
    
    # Then, detect and drop any additional derived tables
    result = execute_sql(container_name, DETECT_DERIVED_TABLES_SQL)
    if result and result.returncode == 0:
        # Parse the result to extract the SQL
        lines = result.stdout.strip().split('\n')
        if len(lines) >= 3 and lines[0].strip() == 'drop_tables_sql':
            # Skip header and separator lines
            additional_tables_sql = lines[2].strip()
            if additional_tables_sql and additional_tables_sql != "":
                print("Dropping additional derived tables...")
                execute_sql(container_name, additional_tables_sql)
    
    # Finally, detect and drop any additional views
    result = execute_sql(container_name, DETECT_DERIVED_VIEWS_SQL)
    if result and result.returncode == 0:
        # Parse the result to extract the SQL
        lines = result.stdout.strip().split('\n')
        if len(lines) >= 3 and lines[0].strip() == 'drop_views_sql':
            # Skip header and separator lines
            additional_views_sql = lines[2].strip()
            if additional_views_sql and additional_views_sql != "":
                print("Dropping additional derived views...")
                execute_sql(container_name, additional_views_sql)
    
    print("Derived tables reset complete.")
    return True

def import_osm_data(container_name, osm_file, use_docker=True):
    """Import OSM data using osm2pgsql."""
    if not os.path.exists(osm_file):
        print(f"Error: OSM file {osm_file} does not exist.", file=sys.stderr)
        return False
    
    print(f"Importing OSM data from {osm_file}...")
    
    if use_docker:
        # Get the absolute path of the OSM file
        osm_file_abs = os.path.abspath(osm_file)
        osm_dir = os.path.dirname(osm_file_abs)
        osm_filename = os.path.basename(osm_file_abs)
        
        # Run osm2pgsql in a Docker container
        cmd = [
            "docker", "run", "--rm", "-it",
            "--network", f"container:{container_name}",
            "-v", f"{osm_dir}:/data",
            "osm2pgsql/osm2pgsql:latest",
            "osm2pgsql",
            "--create",
            "--database", "gis",
            "--username", "gis",
            "--host", "localhost",
            "--port", "5432",
            "--password", "gis",
            "--slim", "-G",
            f"/data/{osm_filename}"
        ]
    else:
        # Run osm2pgsql locally
        cmd = [
            "osm2pgsql",
            "--create",
            "--slim", "-G",
            "-d", "gis",
            "-U", "gis",
            "-H", "localhost",
            "-P", "5432",
            # Use PGPASSWORD environment variable to avoid password prompt
            osm_file
        ]
        
        # Set PGPASSWORD environment variable
        env = os.environ.copy()
        env["PGPASSWORD"] = "gis"  # Default password for development
    
    print(f"Executing: {' '.join(cmd)}")
    
    try:
        # For interactive commands, we don't capture stdout/stderr
        if use_docker:
            subprocess.run(cmd, check=True)
        else:
            # Use the environment with PGPASSWORD for local osm2pgsql
            subprocess.run(cmd, env=env, check=True)
        print("OSM data import complete.")
        return True
    except subprocess.SubprocessError as e:
        print(f"Error importing OSM data: {e}", file=sys.stderr)
        return False

def main():
    parser = argparse.ArgumentParser(description="Reset the PostGIS database and optionally reimport OSM data.")
    
    # Reset options
    reset_group = parser.add_mutually_exclusive_group(required=True)
    reset_group.add_argument("--reset-all", action="store_true", help="Reset the entire database")
    reset_group.add_argument("--reset-derived", action="store_true", help="Reset only the derived tables")
    
    # Import options
    parser.add_argument("--import", dest="import_file", help="Import OSM data from the specified file")
    parser.add_argument("--local-osm2pgsql", action="store_true", 
                       help="Use local osm2pgsql instead of Docker container")
    
    args = parser.parse_args()
    
    # Get the PostgreSQL container name
    container_name = get_db_container_name()
    if not container_name:
        print("Error: Could not find PostgreSQL container.", file=sys.stderr)
        return 1
    
    print(f"Using PostgreSQL container: {container_name}")
    
    # Reset the database
    if args.reset_all:
        if not reset_entire_database(container_name):
            return 1
    elif args.reset_derived:
        if not reset_derived_tables(container_name):
            return 1
    
    # Import OSM data if specified
    if args.import_file:
        if not import_osm_data(container_name, args.import_file, not args.local_osm2pgsql):
            return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
