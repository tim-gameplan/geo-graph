#!/usr/bin/env python3
"""
Export AOI slice as GraphML with preserved OSM attributes.

This script is an enhanced version of export_slice_simple.py that preserves
all OSM attributes in the exported GraphML file.
"""

import json
import typer
import os
import networkx as nx
import geopandas as gpd
from sqlalchemy import create_engine
from pathlib import Path

def connect():
    """Connect to the PostgreSQL database."""
    return create_engine(os.getenv("PG_URL", "postgresql+psycopg://gis:gis@localhost:5432/gis"))

def main(
    longitude: float = typer.Option(..., "--lon", help="Longitude coordinate"),
    latitude: float = typer.Option(..., "--lat", help="Latitude coordinate"),
    radius_km: float = typer.Option(10, "--radius", help="Radius in kilometers"),
    outfile: str = typer.Option("aoi_with_attributes.graphml", "--outfile", help="Output GraphML file"),
    edge_table: str = typer.Option("unified_edges", "--edge-table", help="Edge table to query"),
    include_geometry: bool = typer.Option(False, "--include-geometry", help="Include geometry in the GraphML file")
):
    """Export sub‑graph around the specified coordinates within radius_km, preserving all attributes."""
    engine = connect()
    
    # Get all columns from the edge table
    columns_query = f"""
    SELECT column_name
    FROM information_schema.columns
    WHERE table_name = '{edge_table}'
    ORDER BY ordinal_position;
    """
    
    # Use pandas instead of geopandas since this query doesn't have geometry
    import pandas as pd
    columns_df = pd.read_sql(columns_query, engine)
    columns = columns_df["column_name"].tolist()
    
    # Remove geometry column from the list (we'll handle it separately)
    if "geom" in columns:
        columns.remove("geom")
    
    # Build the column list for the SQL query
    column_list = ", ".join([f'"{col}"' for col in columns])
    
    # Add geometry columns
    if include_geometry:
        geom_columns = """
        , ST_AsText(geom) AS geom_wkt,
        ST_AsGeoJSON(geom) AS geom_json,
        ST_StartPoint(geom) AS start_point,
        ST_EndPoint(geom) AS end_point
        """
    else:
        geom_columns = """
        , ST_StartPoint(geom) AS start_point,
        ST_EndPoint(geom) AS end_point
        """
    
    # Get edges within radius_km of the point
    query = f"""
    SELECT 
        {column_list},
        ST_AsText(ST_StartPoint(geom)) AS start_point_wkt,
        ST_AsText(ST_EndPoint(geom)) AS end_point_wkt
    FROM {edge_table} 
    WHERE ST_DWithin(
        ST_Transform(geom, 4326)::geography, 
        ST_SetSRID(ST_MakePoint({longitude}, {latitude}), 4326)::geography, 
        {radius_km * 1000}
    )
    """
    
    print(f"Executing query:\n{query}")
    # Use pandas instead of geopandas since we're handling the geometry as WKT
    edges = pd.read_sql(query, engine)
    
    if edges.empty:
        print(f"No edges found within {radius_km} km of ({longitude}, {latitude})")
        return
    
    print(f"Found {len(edges)} edges")
    
    # Generate source and target IDs based on the start and end points
    edges['source'] = edges.apply(lambda row: f"node_{hash(str(row.start_point_wkt))}", axis=1)
    edges['target'] = edges.apply(lambda row: f"node_{hash(str(row.end_point_wkt))}", axis=1)
    
    # Create a graph from the edges
    G = nx.DiGraph()
    
    # Add nodes with positions
    nodes = {}
    for _, row in edges.iterrows():
        # Skip edges with None values for start_point_wkt or end_point_wkt
        if pd.isna(row.start_point_wkt) or pd.isna(row.end_point_wkt):
            continue
            
        # Extract coordinates from start point
        start_wkt = str(row.start_point_wkt)
        if not start_wkt.startswith('POINT('):
            continue
        start_coords = start_wkt.replace("POINT(", "").replace(")", "").split()
        start_x, start_y = float(start_coords[0]), float(start_coords[1])
        
        # Extract coordinates from end point
        end_wkt = str(row.end_point_wkt)
        if not end_wkt.startswith('POINT('):
            continue
        end_coords = end_wkt.replace("POINT(", "").replace(")", "").split()
        end_x, end_y = float(end_coords[0]), float(end_coords[1])
        
        # Add nodes if they don't exist
        if row.source not in nodes:
            nodes[row.source] = (start_x, start_y)
        
        if row.target not in nodes:
            nodes[row.target] = (end_x, end_y)
    
    # Add nodes to the graph with positions
    for node_id, pos in nodes.items():
        G.add_node(node_id, x=pos[0], y=pos[1])
    
    # Add edges with all attributes
    for _, row in edges.iterrows():
        # Skip edges with None values for start_point_wkt or end_point_wkt
        if pd.isna(row.start_point_wkt) or pd.isna(row.end_point_wkt):
            continue
            
        # Skip edges with invalid start or end points
        start_wkt = str(row.start_point_wkt)
        end_wkt = str(row.end_point_wkt)
        if not start_wkt.startswith('POINT(') or not end_wkt.startswith('POINT('):
            continue
            
        # Convert row to dictionary and remove unnecessary columns
        edge_attrs = row.to_dict()
        for col in ['start_point_wkt', 'end_point_wkt', 'source', 'target']:
            if col in edge_attrs:
                del edge_attrs[col]
        
        # Convert None values to empty strings for GraphML compatibility
        for key, value in edge_attrs.items():
            if value is None:
                edge_attrs[key] = ""
        
        G.add_edge(row.source, row.target, **edge_attrs)
    
    # Write the graph to a GraphML file
    print(f"Writing GraphML to {outfile}")
    nx.write_graphml(G, outfile)
    
    # Print some statistics
    print(f"Graph statistics:")
    print(f"  Nodes: {len(G.nodes)}")
    print(f"  Edges: {len(G.edges)}")
    print(f"  Edge attributes: {list(next(iter(G.edges(data=True)))[2].keys() if G.edges else [])}")
    
    # Create output directory for the file if it doesn't exist
    output_dir = os.path.dirname(os.path.abspath(outfile))
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    print(f"GraphML written to {outfile}")

if __name__ == "__main__":
    typer.run(main)
