#!/usr/bin/env python3
"""
Graph Slice Export Script

This script exports a slice of the terrain graph around a specific coordinate.
"""

import os
import sys
import argparse
import logging
import subprocess
import json
from pathlib import Path
import networkx as nx
from pyproj import Transformer

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('export_slice.log')
    ]
)
logger = logging.getLogger('export_slice')

def run_sql_query(query):
    """Run a SQL query and return the results."""
    logger.info(f"Running SQL query: {query}")
    
    # Use docker exec to run psql inside the container
    cmd = [
        "docker", "exec", "geo-graph-db-1",
        "psql",
        "-U", "gis",
        "-d", "gis",
        "-t",  # Tuple only, no header
        "-A",  # Unaligned output
        "-c", query
    ]
    
    try:
        result = subprocess.run(
            cmd,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        logger.info(f"SQL query executed successfully")
        return result.stdout.strip().split('\n')
    except subprocess.CalledProcessError as e:
        logger.error(f"Error executing SQL query: {e.stderr}")
        return []

def get_graph_slice(lon, lat, minutes, export_srid=4326, storage_srid=3857):
    """Get a slice of the graph around a specific coordinate."""
    # Convert coordinates from WGS84 to Web Mercator
    transformer = Transformer.from_crs(export_srid, storage_srid, always_xy=True)
    x, y = transformer.transform(lon, lat)
    
    # Calculate the maximum distance in meters (assuming 5 m/s speed)
    max_distance = minutes * 60 * 5
    
    # Get vertices within the maximum distance
    vertices_query = f"""
    SELECT id, original_id, elevation, ST_X(geom), ST_Y(geom), 
           ST_X(ST_Transform(geom, {export_srid})), ST_Y(ST_Transform(geom, {export_srid}))
    FROM graph_vertices
    WHERE ST_DWithin(geom, ST_SetSRID(ST_MakePoint({x}, {y}), {storage_srid}), {max_distance})
    """
    
    vertices_rows = run_sql_query(vertices_query)
    
    if not vertices_rows:
        logger.error(f"No vertices found within {max_distance} meters of ({lon}, {lat})")
        return None
    
    # Create a dictionary of vertices
    vertices = {}
    for row in vertices_rows:
        if not row:
            continue
        
        parts = row.split('|')
        if len(parts) < 7:
            continue
        
        vertex_id = int(parts[0])
        original_id = int(parts[1])
        elevation = float(parts[2]) if parts[2] else 0.0
        x_3857 = float(parts[3])
        y_3857 = float(parts[4])
        x_4326 = float(parts[5])
        y_4326 = float(parts[6])
        
        vertices[vertex_id] = {
            'id': vertex_id,
            'original_id': original_id,
            'elevation': elevation,
            'x_3857': x_3857,
            'y_3857': y_3857,
            'x_4326': x_4326,
            'y_4326': y_4326
        }
    
    # Get edges connecting the vertices
    vertex_ids = ', '.join(str(v) for v in vertices.keys())
    edges_query = f"""
    SELECT id, source_id, target_id, length, travel_time, edge_type, conditions, 
           ST_AsText(geom), ST_AsText(ST_Transform(geom, {export_srid}))
    FROM graph_edges
    WHERE source_id IN ({vertex_ids}) AND target_id IN ({vertex_ids})
    """
    
    edges_rows = run_sql_query(edges_query)
    
    if not edges_rows:
        logger.error(f"No edges found connecting vertices within {max_distance} meters of ({lon}, {lat})")
        return None
    
    # Create a list of edges
    edges = []
    for row in edges_rows:
        if not row:
            continue
        
        parts = row.split('|')
        if len(parts) < 9:
            continue
        
        edge_id = int(parts[0])
        source_id = int(parts[1])
        target_id = int(parts[2])
        length = float(parts[3])
        travel_time = float(parts[4])
        edge_type = parts[5]
        conditions = parts[6].strip('{}').split(',') if parts[6] else []
        geom_3857 = parts[7]
        geom_4326 = parts[8]
        
        edges.append({
            'id': edge_id,
            'source_id': source_id,
            'target_id': target_id,
            'length': length,
            'travel_time': travel_time,
            'edge_type': edge_type,
            'conditions': conditions,
            'geom_3857': geom_3857,
            'geom_4326': geom_4326
        })
    
    # Create a NetworkX graph
    G = nx.DiGraph()
    
    # Add vertices
    for vertex_id, vertex in vertices.items():
        G.add_node(
            vertex_id,
            original_id=vertex['original_id'],
            elevation=vertex['elevation'],
            x_3857=vertex['x_3857'],
            y_3857=vertex['y_3857'],
            x_4326=vertex['x_4326'],
            y_4326=vertex['y_4326']
        )
    
    # Add edges
    for edge in edges:
        G.add_edge(
            edge['source_id'],
            edge['target_id'],
            id=edge['id'],
            length=edge['length'],
            travel_time=edge['travel_time'],
            edge_type=edge['edge_type'],
            conditions=edge['conditions'],
            geom_3857=edge['geom_3857'],
            geom_4326=edge['geom_4326']
        )
    
    return G

def export_graphml(G, outfile):
    """Export a graph to GraphML format."""
    logger.info(f"Exporting graph to {outfile}")
    
    # Convert node and edge attributes to strings
    for node, data in G.nodes(data=True):
        for key, value in data.items():
            G.nodes[node][key] = str(value)
    
    for u, v, data in G.edges(data=True):
        for key, value in data.items():
            if isinstance(value, list):
                G.edges[u, v][key] = ','.join(value)
            else:
                G.edges[u, v][key] = str(value)
    
    # Export to GraphML
    nx.write_graphml(G, outfile)
    
    logger.info(f"Graph exported to {outfile}")
    return True

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Export a slice of the terrain graph",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Export a graph slice around a specific coordinate
  python export_slice.py --lon -93.63 --lat 41.99 --minutes 60 --outfile iowa_central_3857.graphml
"""
    )
    
    # Export options
    parser.add_argument(
        "--lon",
        type=float,
        default=-93.63,
        help="Longitude coordinate"
    )
    parser.add_argument(
        "--lat",
        type=float,
        default=41.99,
        help="Latitude coordinate"
    )
    parser.add_argument(
        "--minutes",
        type=int,
        default=60,
        help="Travel time in minutes"
    )
    parser.add_argument(
        "--outfile",
        default="graph_slice.graphml",
        help="Output GraphML file"
    )
    parser.add_argument(
        "--export-srid",
        type=int,
        default=4326,
        help="SRID for export"
    )
    parser.add_argument(
        "--storage-srid",
        type=int,
        default=3857,
        help="SRID for storage"
    )
    
    args = parser.parse_args()
    
    # Get graph slice
    G = get_graph_slice(
        args.lon,
        args.lat,
        args.minutes,
        args.export_srid,
        args.storage_srid
    )
    
    if not G:
        logger.error("Failed to get graph slice")
        return 1
    
    # Export to GraphML
    if not export_graphml(G, args.outfile):
        logger.error("Failed to export graph to GraphML")
        return 1
    
    logger.info(f"Graph slice exported to {args.outfile}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
