"""Export AOI slice as GraphML or Valhalla tiles."""
import json, typer, subprocess, os, tempfile, uuid, networkx as nx
import geopandas as gpd
from sqlalchemy import create_engine

app = typer.Typer()

def connect():
    return create_engine(os.getenv("PG_URL", "postgresql+psycopg://gis:gis@localhost:5432/gis"))

@app.command()
def slice(lon: float, lat: float, minutes: int = 60,
          outfile: str = "aoi.graphml",
          profile: str = "default",
          valhalla: bool = False):
    """Export reachable sub‑graph around (lon,lat) within `minutes`."""
    engine = connect()
    start_vid = engine.execute(
        "SELECT id FROM vertices ORDER BY geom <-> ST_SetSRID(ST_Point(:lon,:lat),4326) LIMIT 1",
        {'lon': lon, 'lat': lat}
    ).scalar()
    poly = gpd.read_postgis(
        "SELECT (isochrone).geom FROM pgr_isochrone( $$SELECT id, source, target, cost FROM unified_edges$$, :vid, ARRAY[:sec]) AS (isochrone geometry, agg_cost float)",
        engine, params={'vid': start_vid, 'sec': minutes*60}
    ).iloc[0].geom

    edges = gpd.read_postgis(
        "SELECT * FROM unified_edges WHERE ST_Intersects(geom, ST_Buffer(ST_GeomFromText(:wkt,4326),0.01))",
        engine, params={'wkt': poly.wkt}, geom_col='geom'
    )
    if valhalla:
        tmp_dir = tempfile.mkdtemp()
        csv_path = os.path.join(tmp_dir, 'edges.csv')
        edges[['id','source','target']].to_csv(csv_path, index=False)
        subprocess.check_call(['docker','run','--rm',
                               '-v',f'{tmp_dir}:/data',
                               'valhalla/valhalla:latest',
                               'valhalla_build_tiles','-i','/data/edges.csv','-o','/data/tiles'])
        subprocess.check_call(['zip','-r', outfile, 'tiles'], cwd=tmp_dir)
        print(f'Valhalla tiles written to {outfile}')
    else:
        G = nx.from_pandas_edgelist(edges, 'source','target', edge_attr=True, create_using=nx.DiGraph)
        nx.write_graphml(G, outfile)
        print(f'GraphML written to {outfile}')

if __name__ == '__main__':
    app()
