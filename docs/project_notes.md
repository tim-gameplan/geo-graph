# Terrain System Project Notes

## Overview

This project creates a terrain graph system for routing and analysis. It loads OpenStreetMap (OSM) data into a PostGIS database, processes it to create road and water features, builds a terrain grid, and creates a unified graph that can be exported for analysis.

## Data Loading Process

1. **Load OSM Data**: Use osm2pgsql to load OSM data into PostGIS
   ```bash
   osm2pgsql \
       --create \
       --slim -G \
       -d gis \
       -U gis \
       -H localhost \
       -P 5432 \
       -W \
       data/iowa-latest.osm.pbf
   ```

2. **Create Road and Water Tables**: Extract road and water features from the OSM data
   ```sql
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
   ```

3. **Build Water Buffers**: Create buffers around water features
   ```sql
   -- Build water buffers with 50m buffer
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
   ```

4. **Build Terrain Grid**: Create a hexagonal grid covering the area
   ```sql
   -- Build terrain grid with 200m cell size
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
   ```

5. **Create Edge Tables**: Create edge tables for the unified graph
   ```sql
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
   ```

6. **Create Unified Edges Table**: Combine all edge tables into a unified graph
   ```sql
   -- Create unified_edges table
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
   ```

7. **Export Graph Slice**: Export a subgraph around a specific coordinate
   ```bash
   python tools/export_slice_simple.py --lon -93.6 --lat 41.6 --radius 5 --outfile iowa_slice.graphml
   ```

## Database Reset and Pipeline Rerun

To reset the database and rerun the pipeline, you can use the following scripts:

### Reset Database

The `reset_database.py` script provides options for resetting the database:

```bash
# Reset the entire database (drops and recreates the database)
python scripts/reset_database.py --reset-all

# Reset only the derived tables (preserves the OSM data)
python scripts/reset_database.py --reset-derived

# Reset and reimport OSM data
python scripts/reset_database.py --reset-all --import data/iowa-latest.osm.pbf
```

The script performs the following steps:
1. Terminates all connections to the database
2. Drops the database (if --reset-all is specified)
3. Creates a new database
4. Creates the necessary extensions (postgis and pgrouting)
5. Imports OSM data (if --import is specified)

### Run Pipeline

The `run_pipeline.py` script runs the complete pipeline:

```bash
# Run the complete pipeline
python scripts/run_pipeline.py

# Run the pipeline with preserved OSM attributes
python scripts/run_pipeline.py --preserve-attributes

# Run the pipeline and export a slice
python scripts/run_pipeline.py --export --lon -93.63 --lat 41.99 --radius 5 --output test_slice.graphml
```

The script executes the following SQL scripts in sequence:
1. derive_road_and_water_fixed.sql - Extract road and water features from OSM data
2. build_water_buffers_simple.sql - Create buffers around water features
3. create_grid_profile.sql - Create grid profile table
4. build_terrain_grid_simple.sql - Create a hexagonal grid covering the area
5. create_edge_tables.sql - Create edge tables for the unified graph
6. add_source_target_columns.sql - Add source and target columns to edge tables
7. refresh_topology_simple.sql - Create topology for the unified graph
8. create_unified_edges.sql - Combine all edge tables into a unified graph

## Notes

- The OSM data is in SRID 3857 (Web Mercator), but we need to transform it to SRID 4326 (WGS84) for geographic calculations.
- The source and target columns in the edge tables are initially NULL, but we generate them on-the-fly when exporting a graph slice.
- The cost values are based on travel time estimates: 18 m/s (≈ 40 mph) for roads, 1000.0 for water (to discourage crossing), and 1.0 for terrain (placeholder for slope-based cost).
- When resetting the database, make sure there are no active connections to the database. You can terminate all connections with:
  ```sql
  SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = 'gis' AND pid <> pg_backend_pid();
  ```
