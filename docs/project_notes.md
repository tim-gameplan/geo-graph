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

## Notes

- The OSM data is in SRID 3857 (Web Mercator), but we need to transform it to SRID 4326 (WGS84) for geographic calculations.
- The source and target columns in the edge tables are initially NULL, but we generate them on-the-fly when exporting a graph slice.
- The cost values are based on travel time estimates: 18 m/s (≈ 40 mph) for roads, 1000.0 for water (to discourage crossing), and 1.0 for terrain (placeholder for slope-based cost).
