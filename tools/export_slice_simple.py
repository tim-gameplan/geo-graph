"""Export AOI slice as GraphML."""
import json, typer, os, networkx as nx
import geopandas as gpd
from sqlalchemy import create_engine

def connect():
    return create_engine(os.getenv("PG_URL", "postgresql+psycopg://gis:gis@localhost:5432/gis"))

def main(
    longitude: float = typer.Option(..., "--lon", help="Longitude coordinate"),
    latitude: float = typer.Option(..., "--lat", help="Latitude coordinate"),
    radius_km: float = typer.Option(10, "--radius", help="Radius in kilometers"),
    outfile: str = typer.Option("aoi.graphml", "--outfile", help="Output GraphML file")
):
    """Export sub‑graph around the specified coordinates within radius_km."""
    engine = connect()
    
    # Get edges within radius_km of the point and generate source/target nodes
    edges = gpd.read_postgis(
        f"""
        SELECT 
            id,
            ST_StartPoint(geom) AS start_point,
            ST_EndPoint(geom) AS end_point,
            cost,
            geom
        FROM unified_edges 
        WHERE ST_DWithin(
            ST_Transform(geom, 4326)::geography, 
            ST_SetSRID(ST_MakePoint({longitude}, {latitude}), 4326)::geography, 
            {radius_km * 1000}
        )
        """,
        engine, 
        geom_col='geom'
    )
    
    # Generate source and target IDs based on the start and end points
    edges['source'] = edges.apply(lambda row: f"node_{hash(str(row.start_point))}", axis=1)
    edges['target'] = edges.apply(lambda row: f"node_{hash(str(row.end_point))}", axis=1)
    
    # Create a graph from the edges
    G = nx.from_pandas_edgelist(
        edges, 
        'source', 'target', 
        edge_attr=['id', 'cost'], 
        create_using=nx.DiGraph
    )
    
    # Write the graph to a GraphML file
    nx.write_graphml(G, outfile)
    print(f'GraphML written to {outfile}')

if __name__ == '__main__':
    typer.run(main)
