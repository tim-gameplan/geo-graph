# Quick Start Guide

This guide will help you get up and running with the Terrain Graph Pipeline quickly.

## Prerequisites

- Docker and Docker Compose
- Python 3.9+ with pip
- OSM PBF data file (sample provided in data/iowa-latest.osm.pbf)
- 8GB+ RAM recommended for development (64GB for production)

## 1. Start Docker Containers

```bash
# Start PostgreSQL/PostGIS and pgAdmin containers
docker compose up -d

# Verify containers are running
docker compose ps
```

pgAdmin is available at http://localhost:5050 (user: admin@example.com, password: admin)

## 2. Set Up Python Environment

```bash
# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

## 3. Load OSM Data

```bash
# Load OSM PBF data into PostGIS using local osm2pgsql
osm2pgsql \
    --create \
    --slim -G \
    -d gis \
    -U gis \
    -H localhost \
    -P 5432 \
    -W \
    data/iowa-latest.osm.pbf

# Alternatively, if using Docker for osm2pgsql:
docker run --rm -it \
  --network container:geo-graph-db-1 \
  -v $(pwd)/data:/data \
  osm2pgsql/osm2pgsql:latest \
  osm2pgsql \
      --create \
      --database gis \
      --username gis \
      --host localhost \
      --port 5432 \
      --password gis \
      --slim -G \
      /data/iowa-latest.osm.pbf
```

## 4. Create Road and Water Tables

```bash
# Create a fixed version of the derive_road_and_water.sql script
cat > sql/derive_road_and_water_fixed.sql << 'EOF'
-- roads: keep all highway=*
DROP TABLE IF EXISTS road_edges;
CREATE TABLE road_edges AS
SELECT
    osm_id AS id,
    way   AS geom,
    ST_Length(ST_Transform(way, 4326)::geography) / 18 AS cost   -- rough 18 m/s ≈ 40 mph
FROM planet_osm_line
WHERE highway IS NOT NULL;

CREATE INDEX ON road_edges USING GIST(geom);

-- water polygons: rivers, lakes, etc.
DROP TABLE IF EXISTS water_polys;
CREATE TABLE water_polys AS
SELECT
    osm_id AS id,
    way    AS geom
FROM planet_osm_polygon
WHERE water IS NOT NULL
   OR "natural" = 'water'
   OR landuse   = 'reservoir';

CREATE INDEX ON water_polys USING GIST(geom);
EOF

# Copy the script to the Docker container and run it
docker compose cp sql/derive_road_and_water_fixed.sql db:/tmp/derive_road_and_water_fixed.sql
docker compose exec db psql -U gis -d gis -f /tmp/derive_road_and_water_fixed.sql
```

## 5. Build Water Buffers

```bash
# Create a simplified water buffers script
cat > sql/build_water_buffers_simple.sql << 'EOF'
-- build_water_buffers.sql
DO $$
BEGIN
  RAISE NOTICE 'Building water buffers 50 m';
  DROP TABLE IF EXISTS water_buf CASCADE;
  CREATE TABLE water_buf AS
  SELECT id,
         ST_Buffer(ST_Transform(geom, 4326)::geography, 50)::geometry(MultiPolygon, 4326) AS geom
  FROM water_polys;
  CREATE INDEX ON water_buf USING GIST(geom);
END$$;
EOF

# Copy the script to the Docker container and run it
docker compose cp sql/build_water_buffers_simple.sql db:/tmp/build_water_buffers_simple.sql
docker compose exec db psql -U gis -d gis -f /tmp/build_water_buffers_simple.sql
```

## 6. Build Terrain Grid

```bash
# Create grid profile table
cat > sql/create_grid_profile.sql << 'EOF'
-- Create grid_profile table
CREATE TABLE IF NOT EXISTS grid_profile (
  name text PRIMARY KEY,
  cell_m integer  -- hexagon diameter in metres
);

-- Insert default profiles
INSERT INTO grid_profile VALUES
  ('coarse', 400),
  ('default', 200),
  ('fine', 100)
ON CONFLICT (name) DO NOTHING;
EOF

# Create a simplified terrain grid script
cat > sql/build_terrain_grid_simple.sql << 'EOF'
-- build_terrain_grid.sql
-- Using default profile (cell_m = 200)
DO $$
DECLARE
  cell integer := 200; -- Default cell size
BEGIN
  RAISE NOTICE 'Building terrain grid with cell size % m', cell;
  DROP TABLE IF EXISTS terrain_grid CASCADE;
  CREATE TABLE terrain_grid AS
  SELECT (ST_HexagonGrid(cell, (SELECT ST_Extent(geom) FROM water_buf))).geom AS geom
  FROM generate_series(1,1);
  ALTER TABLE terrain_grid ADD COLUMN cost double precision;
  UPDATE terrain_grid
    SET cost = 1.0; -- placeholder for slope cost
  CREATE INDEX ON terrain_grid USING GIST(geom);
END$$;
EOF

# Copy the scripts to the Docker container and run them
docker compose cp sql/create_grid_profile.sql db:/tmp/create_grid_profile.sql
docker compose exec db psql -U gis -d gis -f /tmp/create_grid_profile.sql

docker compose cp sql/build_terrain_grid_simple.sql db:/tmp/build_terrain_grid_simple.sql
docker compose exec db psql -U gis -d gis -f /tmp/build_terrain_grid_simple.sql
```

## 7. Create Edge Tables

```bash
# Create edge tables script
cat > sql/create_edge_tables.sql << 'EOF'
-- Create water_edges table from water_buf
DROP TABLE IF EXISTS water_edges CASCADE;
CREATE TABLE water_edges AS
SELECT 
    id,
    NULL::bigint AS source,
    NULL::bigint AS target,
    1000.0 AS cost, -- High cost to discourage crossing water
    ST_Boundary(geom) AS geom
FROM water_buf;

-- Create terrain_edges table from terrain_grid
DROP TABLE IF EXISTS terrain_edges CASCADE;
CREATE TABLE terrain_edges AS
WITH 
points AS (
    SELECT 
        ROW_NUMBER() OVER () AS id,
        ST_Centroid(geom) AS geom,
        cost
    FROM terrain_grid
),
edges AS (
    SELECT 
        ROW_NUMBER() OVER () AS id,
        a.id AS source_id,
        b.id AS target_id,
        (a.cost + b.cost) / 2 AS cost,
        ST_MakeLine(a.geom, b.geom) AS geom
    FROM points a
    JOIN points b ON ST_DWithin(a.geom, b.geom, 300) -- Connect points within 300m
    WHERE a.id < b.id -- Avoid duplicate edges
)
SELECT 
    id,
    NULL::bigint AS source,
    NULL::bigint AS target,
    cost,
    geom
FROM edges;

-- Create indexes
CREATE INDEX ON water_edges USING GIST(geom);
CREATE INDEX ON terrain_edges USING GIST(geom);
EOF

# Copy the script to the Docker container and run it
docker compose cp sql/create_edge_tables.sql db:/tmp/create_edge_tables.sql
docker compose exec db psql -U gis -d gis -f /tmp/create_edge_tables.sql
```

## 8. Create Unified Edges Table

```bash
# Create unified edges script
cat > sql/create_unified_edges.sql << 'EOF'
-- Create unified_edges table without topology
BEGIN;
DROP TABLE IF EXISTS unified_edges CASCADE;
CREATE TABLE unified_edges AS
SELECT id, source, target, cost, geom FROM road_edges
UNION ALL
SELECT id, source, target, cost, geom FROM water_edges
UNION ALL
SELECT id, source, target, cost, geom FROM terrain_edges;

-- Create index on geometry
CREATE INDEX ON unified_edges USING GIST(geom);
COMMIT;
EOF

# Copy the script to the Docker container and run it
docker compose cp sql/create_unified_edges.sql db:/tmp/create_unified_edges.sql
docker compose exec db psql -U gis -d gis -f /tmp/create_unified_edges.sql
```

## 9. Export an AOI Slice

```bash
# Create a simplified export script
cat > tools/export_slice_simple.py << 'EOF'
"""Export AOI slice as GraphML."""
import json typer os networkx as nx
import geopandas as gpd
from sqlalchemy import create_engine

def connect():
    return create_engine(os.getenv("PG_URL" "postgresql+psycopg://gis:gis@localhost:5432/gis"))

def main(
    longitude: float = typer.Option(... "--lon" help="Longitude coordinate")
    latitude: float = typer.Option(... "--lat" help="Latitude coordinate")
    radius_km: float = typer.Option(10 "--radius" help="Radius in kilometers")
    outfile: str = typer.Option("aoi.graphml" "--outfile" help="Output GraphML file")
):
    """Export sub‑graph around the specified coordinates within radius_km."""
    engine = connect()

    # Get edges within radius_km of the point and generate source/target nodes
    edges = gpd.read_postgis(
        f"""
        SELECT
            id
            ST_StartPoint(geom) AS start_point
            ST_EndPoint(geom) AS end_point
            cost
            geom
        FROM unified_edges
        WHERE ST_DWithin(
            ST_Transform(geom 4326)::geography
            ST_SetSRID(ST_MakePoint({longitude} {latitude}) 4326)::geography
            {radius_km * 1000}
        )
        """
        engine
        geom_col='geom'
    )

    # Generate source and target IDs based on the start and end points
    edges['source'] = edges.apply(lambda row: f"node_{hash(str(row.start_point))}" axis=1)
    edges['target'] = edges.apply(lambda row: f"node_{hash(str(row.end_point))}" axis=1)

    # Create a graph from the edges
    G = nx.from_pandas_edgelist(
        edges
        'source' 'target'
        edge_attr=['id' 'cost']
        create_using=nx.DiGraph
    )

    # Write the graph to a GraphML file
    nx.write_graphml(G outfile)
    print(f'GraphML written to {outfile}')

if __name__ == '__main__':
    typer.run(main)
EOF

# Export a slice around Des Moines Iowa
python tools/export_slice_simple.py --lon -93.6 --lat 41.6 --radius 5 --outfile iowa_slice.graphml
```

## 10. Resetting the Database and Rerunning the Pipeline

If you need to clear out the database and rerun the pipeline (for example, to test changes or to start fresh), you can use the `reset_database.py` script:

```bash
# Reset the entire database (drops and recreates the database)
python scripts/reset_database.py --reset-all

# Alternatively, reset only the derived tables (preserves the OSM data)
python scripts/reset_database.py --reset-derived

# Reset and reimport OSM data
python scripts/reset_database.py --reset-all --import data/iowa-latest.osm.pbf

# If you encounter issues with Docker-based osm2pgsql, use the local version
python scripts/reset_database.py --reset-all --import data/iowa-latest.osm.pbf --local-osm2pgsql
```

After resetting the database, you can rerun the pipeline using the `run_pipeline.py` script:

```bash
# Run the complete pipeline
python scripts/run_pipeline.py

# Run the pipeline and export a slice
python scripts/run_pipeline.py --export --lon -93.63 --lat 41.99 --radius 5 --output test_slice.graphml
```

## 11. Preserving OSM Attributes (Optional)

If you want to preserve OSM attributes like highway type, names, and surface in the exported graph, you can use the `--preserve-attributes` flag with the `run_pipeline.py` script:

```bash
# Run the pipeline with preserved OSM attributes
python scripts/run_pipeline.py --preserve-attributes
```

Then, use the `export_slice_with_attributes.py` script to export a graph slice with all OSM attributes preserved:

```bash
# Export a slice with OSM attributes
python scripts/export_slice_with_attributes.py --lon -93.63 --lat 41.99 --radius 5 --outfile data/iowa_central_with_attributes.graphml
```

For more details on preserving OSM attributes, see [OSM Attributes Guide](osm_attributes.md).

## 12. Using the Enhanced Pipeline (Optional)

The enhanced pipeline adds support for isochrone-based graph slicing and preserves OSM attributes in the exported graph. To use the enhanced pipeline:

```bash
# Run the enhanced pipeline
python scripts/run_pipeline_enhanced.py

# Export an isochrone-based slice
python tools/export_slice_enhanced_fixed.py --lon -93.63 --lat 41.99 --minutes 60 --outfile isochrone_enhanced.graphml

# Visualize the exported graph
python visualize_graph.py isochrone_enhanced.graphml
```

For more details on the enhanced pipeline, see [Enhanced Pipeline](enhanced_pipeline.md).

## 13. Verify Results

```bash
# Check the number of nodes and edges in the exported graph
python -c "import networkx as nx; G = nx.read_graphml('iowa_slice.graphml'); print(f'Nodes: {len(G.nodes)}, Edges: {len(G.edges)}')"

# Check the enhanced graph
python -c "import networkx as nx; G = nx.read_graphml('isochrone_enhanced.graphml'); print(f'Nodes: {len(G.nodes)}, Edges: {len(G.edges)}')"
```

## Troubleshooting

- If you encounter errors when resetting the database, it might be because there are active connections to the database. You can terminate all connections with:
  ```sql
  SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = 'gis' AND pid <> pg_backend_pid();
  ```

- If the pgrouting extension is missing, you can install it in the Docker container with:
  ```bash
  docker exec -it geo-graph-db-1 bash -c "apt-get update && apt-get install -y postgresql-16-pgrouting"
  ```

- If osm2pgsql fails with "File does not exist: default", remove the `--style default` parameter
- If you get connection errors, verify the container name with `docker compose ps`
- For Python connection issues, set the environment variable:
  ```bash
  export PG_URL="postgresql+psycopg://gis:gis@localhost:5432/gis"
  ```
- If you encounter "Only lon/lat coordinate systems are supported in geography" errors, make sure to transform geometries to SRID 4326 before casting to geography
- If you see "None cannot be a node" errors when creating a graph, ensure that source and target columns have valid values
- For more detailed documentation, see [Project Notes](project_notes.md)

## Next Steps

- Try different buffer sizes for water features
- Try different grid densities for the terrain grid
- Explore the database using pgAdmin at http://localhost:5050
