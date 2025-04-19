#!/usr/bin/env python3
"""
Run SQL queries from a file in the PostgreSQL container.

This script copies a SQL file to the Docker container and executes it.
It can also execute a single query specified on the command line.
"""

import argparse
import os
import subprocess
import sys
import tempfile

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
    # Copy the file to the container
    container_path = f"/tmp/{os.path.basename(sql_file)}"
    copy_cmd = ["docker", "compose", "cp", sql_file, f"db:{container_path}"]
    copy_result = run_docker_command(copy_cmd)
    if not copy_result or copy_result.returncode != 0:
        print(f"Error copying SQL file to container: {copy_result.stderr if copy_result else 'Unknown error'}", file=sys.stderr)
        return None
    
    # Execute the SQL file
    cmd = [
        "docker", "exec", container_name,
        "psql", "-U", user, "-d", database, "-f", container_path
    ]
    
    print(f"Executing SQL file: {sql_file}")
    result = run_docker_command(cmd, check=False)
    
    if result:
        print(result.stdout)
        if result.stderr:
            print(result.stderr, file=sys.stderr)
    
    return result

def execute_sql_query(container_name, query, database="gis", user="gis"):
    """Execute a SQL query in the PostgreSQL container."""
    cmd = [
        "docker", "exec", container_name,
        "psql", "-U", user, "-d", database, "-c", query
    ]
    
    print(f"Executing SQL query: {query}")
    result = run_docker_command(cmd, check=False)
    
    if result:
        print(result.stdout)
        if result.stderr:
            print(result.stderr, file=sys.stderr)
    
    return result

def main():
    parser = argparse.ArgumentParser(description="Run SQL queries from a file in the PostgreSQL container.")
    
    # SQL options
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--file", "-f", help="SQL file to execute")
    group.add_argument("--query", "-q", help="SQL query to execute")
    group.add_argument("--query-number", "-n", type=int, help="Query number from query_osm_attributes.sql to execute")
    
    # Database options
    parser.add_argument("--database", "-d", default="gis", help="Database name")
    parser.add_argument("--user", "-u", default="gis", help="Database user")
    
    args = parser.parse_args()
    
    # Get the PostgreSQL container name
    container_name = get_db_container_name()
    if not container_name:
        print("Error: Could not find PostgreSQL container.", file=sys.stderr)
        return 1
    
    print(f"Using PostgreSQL container: {container_name}")
    
    # Execute SQL
    if args.file:
        if not os.path.exists(args.file):
            print(f"Error: SQL file {args.file} does not exist.", file=sys.stderr)
            return 1
        
        result = execute_sql_file(container_name, args.file, args.database, args.user)
        return 0 if result and result.returncode == 0 else 1
    
    elif args.query:
        result = execute_sql_query(container_name, args.query, args.database, args.user)
        return 0 if result and result.returncode == 0 else 1
    
    elif args.query_number:
        # Find the query in query_osm_attributes.sql
        query_file = os.path.join(os.path.dirname(__file__), "query_osm_attributes.sql")
        if not os.path.exists(query_file):
            print(f"Error: Query file {query_file} does not exist.", file=sys.stderr)
            return 1
        
        with open(query_file, "r") as f:
            content = f.read()
        
        # Split the file by query markers (e.g., "-- 1. ", "-- 2. ", etc.)
        import re
        queries = re.split(r"--\s+\d+\.\s+", content)
        
        # Remove the first element (it's empty or contains the file header)
        if not queries[0].strip() or "Query OSM Attributes" in queries[0]:
            queries = queries[1:]
        
        if args.query_number < 1 or args.query_number > len(queries):
            print(f"Error: Query number {args.query_number} is out of range. Valid range is 1-{len(queries)}.", file=sys.stderr)
            return 1
        
        # Get the query
        query = queries[args.query_number - 1].strip()
        
        # Execute the query
        result = execute_sql_query(container_name, query, args.database, args.user)
        return 0 if result and result.returncode == 0 else 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
