#!/usr/bin/env python3
"""
Enhanced version of export_slice.py for isochrone analysis.

This script:
1. Uses pgRouting's pgr_isochrone function to calculate areas reachable within a certain time
2. Extracts edges that intersect with the isochrone polygon
3. Preserves all OSM attributes in the exported GraphML file
4. Supports export to GraphML or Valhalla tiles
"""

import json
import typer
import subprocess
import os
import tempfile
import uuid
import networkx as nx
import geopandas as gpd
from sqlalchemy import create_engine
from pathlib import Path

app = typer.Typer()

def connect():
    """Connect to the PostgreSQL database."""
    return create_engine(os.getenv("PG_URL", "postgresql+psycopg://gis:gis@localhost:5432/gis"))

@app.command()
def slice(
    lon: float = typer.Option(..., "--lon", help="Longitude coordinate"),
    lat: float = typer.Option(..., "--lat", help="Latitude coordinate"),
    minutes: int = typer.Option(60, "--minutes", help="Travel time in minutes"),
    outfile: str = typer.Option("isochrone.graphml", "--outfile", help="Output file"),
    profile: str = typer.Option("default", "--profile", help="Grid profile (coarse, default, fine)"),
    valhalla: bool = typer.Option(False, "--valhalla", help="Export as Valhalla tiles"),
    include_geometry: bool = typer.Option(False, "--include-geometry", help="Include geometry in GraphML")
):
    """Export reachable sub‑graph around (lon,lat) within specified travel time in minutes."""
    engine = connect()
    
    # Find the nearest vertex to the specified coordinates
    start_vid = engine.execute(
        "SELECT id FROM vertices ORDER BY geom <-> ST_SetSRID(ST_Point(:lon,:lat),4326) LIMIT 1",
        {'lon': lon, 'lat': lat}
    ).scalar()
    
    if not start_vid:
        print(f"Error: No vertex found near coordinates ({lon}, {lat})")
        return
    
    print(f"Using start vertex ID: {start_vid}")
    
    # Calculate isochrone polygon using pgRouting
    print(f"Calculating isochrone for {minutes} minutes travel time...")
    isochrone_query = """
    SELECT (isochrone).geom 
    FROM pgr_isochrone(
        $$SELECT id, source, target, cost FROM unified_edges$$, 
        :vid, 
        ARRAY[:sec]
    ) AS (isochrone geometry, agg_cost float)
    """
    
    isochrone_gdf = gpd.read_postgis(
        isochrone_query,
        engine, 
        params={'vid': start_vid, 'sec': minutes*60}
    )
    
    if isochrone_gdf.empty:
        print(f"Error: No isochrone polygon generated for vertex {start_vid}")
        return
    
    poly = isochrone_gdf.iloc[0].geom
    print(f"Isochrone polygon generated with area: {poly.area:.6f} square degrees")
    
    # Get all columns from the unified_edges table
    columns_query = """
    SELECT column_name
    FROM information_schema.columns
    WHERE table_name = 'unified_edges'
    ORDER BY ordinal_position;
    """
    
    import pandas as pd
    columns_df = pd.read_sql(columns_query, engine)
    columns = columns_df["column_name"].tolist()
    
    # Remove geometry column from the list (we'll handle it separately)
    if "geom" in columns:
        columns.remove("geom")
    
    # Build the column list for the SQL query
    column_list = ", ".join([f'"{col}"' for col in columns])
    
    # Extract edges that intersect with the isochrone polygon
    print("Extracting edges within the isochrone polygon...")
    edges_query = f"""
    SELECT 
        {column_list},
        ST_AsText(ST_StartPoint(geom)) AS start_point_wkt,
        ST_AsText(ST_EndPoint(geom)) AS end_point_wkt
        {', ST_AsText(geom) AS geom_wkt' if include_geometry else ''}
    FROM unified_edges 
    WHERE ST_Intersects(geom, ST_Buffer(ST_GeomFromText(:wkt, 4326), 0.001))
    """
    
    edges = pd.read_sql(edges_query, engine, params={'wkt': poly.wkt})
    
    if edges.empty:
        print(f"Error: No edges found within the isochrone polygon")
        return
    
    print(f"Found {len(edges)} edges within the isochrone")
    
    if valhalla:
        # Export as Valhalla tiles
        print("Exporting as Valhalla tiles...")
        tmp_dir = tempfile.mkdtemp()
        csv_path = os.path.join(tmp_dir, 'edges.csv')
        edges[['id', 'source', 'target']].to_csv(csv_path, index=False)
        
        subprocess.check_call([
            'docker', 'run', '--rm',
            '-v', f'{tmp_dir}:/data',
            'valhalla/valhalla:latest',
            'valhalla_build_tiles', '-i', '/data/edges.csv', '-o', '/data/tiles'
        ])
        
        subprocess.check_call(['zip', '-r', outfile, 'tiles'], cwd=tmp_dir)
        print(f'Valhalla tiles written to {outfile}')
    else:
        # Export as GraphML
        print("Creating NetworkX graph...")
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
            
            # Use source and target IDs from the unified_edges table if available
            source_id = f"node_{row.source}" if 'source' in row and not pd.isna(row.source) else f"node_{hash(start_wkt)}"
            target_id = f"node_{row.target}" if 'target' in row and not pd.isna(row.target) else f"node_{hash(end_wkt)}"
            
            # Add nodes if they don't exist
            if source_id not in nodes:
                nodes[source_id] = (start_x, start_y)
            
            if target_id not in nodes:
                nodes[target_id] = (end_x, end_y)
        
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
                
            # Use source and target IDs from the unified_edges table if available
            source_id = f"node_{row.source}" if 'source' in row and not pd.isna(row.source) else f"node_{hash(start_wkt)}"
            target_id = f"node_{row.target}" if 'target' in row and not pd.isna(row.target) else f"node_{hash(end_wkt)}"
            
            # Convert row to dictionary and remove unnecessary columns
            edge_attrs = row.to_dict()
            for col in ['start_point_wkt', 'end_point_wkt', 'source', 'target']:
                if col in edge_attrs:
                    edge_attrs[col] = str(edge_attrs[col])  # Convert to string for GraphML compatibility
            
            # Convert None values to empty strings for GraphML compatibility
            for key, value in edge_attrs.items():
                if value is None:
                    edge_attrs[key] = ""
            
            G.add_edge(source_id, target_id, **edge_attrs)
        
        # Write the graph to a GraphML file
        print(f"Writing GraphML to {outfile}")
        nx.write_graphml(G, outfile)
        
        # Print some statistics
        print(f"Graph statistics:")
        print(f"  Nodes: {len(G.nodes)}")
        print(f"  Edges: {len(G.edges)}")
        print(f"  Edge attributes: {list(next(iter(G.edges(data=True)))[2].keys() if G.edges else [])}")
        
        print(f"GraphML written to {outfile}")

if __name__ == "__main__":
    app()
