-- 04_create_terrain_grid_boundary_3857.sql
-- Create terrain grid with boundary preservation for the boundary hexagon layer approach

-- Drop existing tables if they exist
DROP TABLE IF EXISTS complete_hex_grid CASCADE;
DROP TABLE IF EXISTS classified_hex_grid CASCADE;
DROP TABLE IF EXISTS terrain_grid CASCADE;
DROP TABLE IF EXISTS terrain_grid_points CASCADE;
DROP TABLE IF EXISTS water_obstacles CASCADE;

-- Create water obstacles table from dissolved water buffers
CREATE TABLE water_obstacles AS
SELECT 
    id,
    geom
FROM 
    dissolved_water_buffers;

-- Create a complete hexagonal grid
CREATE TABLE complete_hex_grid AS
SELECT 
    (ST_HexagonGrid(200, ST_Extent(geom))).*
FROM 
    planet_osm_polygon
WHERE 
    ST_IsValid(geom);

-- Classify hexagons as land, boundary, or water
CREATE TABLE classified_hex_grid AS
SELECT
    hg.geom,
    CASE
        WHEN EXISTS (
            SELECT 1
            FROM water_obstacles wo
            WHERE ST_Contains(wo.geom, hg.geom)
        ) THEN 'water'
        WHEN EXISTS (
            SELECT 1
            FROM water_obstacles wo
            WHERE ST_Intersects(wo.geom, hg.geom)
        ) THEN 'boundary'
        ELSE 'land'
    END AS hex_type
FROM 
    complete_hex_grid hg;

-- Create the terrain grid (excluding water hexagons)
CREATE TABLE terrain_grid AS
SELECT 
    ROW_NUMBER() OVER () AS id,
    geom, 
    hex_type
FROM 
    classified_hex_grid
WHERE 
    hex_type IN ('land', 'boundary');

-- Create terrain grid points (centroids of terrain grid cells)
CREATE TABLE terrain_grid_points AS
SELECT
    t.id,
    t.hex_type,
    ST_Centroid(t.geom) AS geom,
    EXISTS (
        SELECT 1
        FROM water_obstacles wo
        WHERE ST_Contains(wo.geom, ST_Centroid(t.geom))
    ) AS is_water
FROM
    terrain_grid t;

-- Create spatial indexes
CREATE INDEX terrain_grid_geom_idx ON terrain_grid USING GIST (geom);
CREATE INDEX terrain_grid_points_geom_idx ON terrain_grid_points USING GIST (geom);
CREATE INDEX water_obstacles_geom_idx ON water_obstacles USING GIST (geom);

-- Log the results
SELECT 'Created ' || COUNT(*) || ' terrain grid cells' FROM terrain_grid;
SELECT 'Created ' || COUNT(*) || ' terrain grid points' FROM terrain_grid_points;
SELECT 'Land hexagons: ' || COUNT(*) FROM terrain_grid WHERE hex_type = 'land';
SELECT 'Boundary hexagons: ' || COUNT(*) FROM terrain_grid WHERE hex_type = 'boundary';
