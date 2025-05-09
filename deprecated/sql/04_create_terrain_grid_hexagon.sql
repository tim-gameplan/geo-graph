/*
 * Terrain Grid Creation with Hexagonal Grid for Obstacle Boundary Pipeline
 * 
 * This script creates a hexagonal terrain grid that includes water boundaries.
 * It marks hexagons that intersect with water obstacles as "boundary" hexagons
 * but keeps them in the grid for better connectivity.
 */

-- Create terrain grid with EPSG:3857 coordinates
-- Parameters:
-- :storage_srid - SRID for storage (default: 3857)
-- :grid_spacing - Grid spacing in meters (default: 200)

-- Create water obstacles table from dissolved water buffers if it doesn't exist
CREATE TABLE IF NOT EXISTS water_obstacles AS
SELECT 
    id,
    ST_MakeValid(geom) AS geom
FROM 
    dissolved_water_buffers;

-- Create terrain_grid table
DROP TABLE IF EXISTS terrain_grid CASCADE;
CREATE TABLE terrain_grid (
    id SERIAL PRIMARY KEY,
    geom GEOMETRY(POLYGON, :storage_srid),
    hex_type VARCHAR(10), -- 'land', 'boundary', or 'water'
    cost NUMERIC DEFAULT 1.0 -- Placeholder for terrain-based cost
);

-- Create the complete hexagonal grid
WITH 
-- Create a hexagonal grid covering the extent of the data
hex_grid AS (
    SELECT 
        ST_SetSRID((ST_HexagonGrid(:grid_spacing, (
            SELECT ST_Extent(geom) 
            FROM dissolved_water_buffers
        ))).geom, :storage_srid) AS geom
    FROM generate_series(1,1)
),
-- Classify hexagons as land, boundary, or water
classified_grid AS (
    SELECT
        hg.geom,
        CASE
            WHEN EXISTS (
                SELECT 1
                FROM water_obstacles wo
                WHERE ST_Contains(wo.geom, ST_Centroid(hg.geom))
            ) THEN 'water'
            WHEN EXISTS (
                SELECT 1
                FROM water_obstacles wo
                WHERE ST_Intersects(wo.geom, hg.geom)
            ) THEN 'boundary'
            ELSE 'land'
        END AS hex_type
    FROM hex_grid hg
)
INSERT INTO terrain_grid (geom, hex_type, cost)
SELECT 
    geom,
    hex_type,
    CASE
        WHEN hex_type = 'water' THEN 5.0 -- Higher cost for water
        WHEN hex_type = 'boundary' THEN 2.0 -- Medium cost for boundary
        ELSE 1.0 -- Normal cost for land
    END AS cost
FROM classified_grid;

-- Create spatial index
CREATE INDEX terrain_grid_geom_idx ON terrain_grid USING GIST(geom);
CREATE INDEX terrain_grid_hex_type_idx ON terrain_grid(hex_type);

-- Create terrain grid points table
DROP TABLE IF EXISTS terrain_grid_points CASCADE;
CREATE TABLE terrain_grid_points (
    id SERIAL PRIMARY KEY,
    grid_id INTEGER REFERENCES terrain_grid(id),
    hex_type VARCHAR(10),
    geom GEOMETRY(POINT, :storage_srid),
    is_water BOOLEAN
);

-- Insert centroids for all hexagons
INSERT INTO terrain_grid_points (grid_id, hex_type, geom, is_water)
SELECT 
    id,
    hex_type,
    ST_Centroid(geom),
    hex_type = 'water'
FROM 
    terrain_grid;

-- Create spatial index on points
CREATE INDEX terrain_grid_points_geom_idx ON terrain_grid_points USING GIST(geom);
CREATE INDEX terrain_grid_points_hex_type_idx ON terrain_grid_points(hex_type);
CREATE INDEX terrain_grid_points_is_water_idx ON terrain_grid_points(is_water);

-- Log the results
SELECT 'Created ' || COUNT(*) || ' terrain grid cells' FROM terrain_grid;
SELECT 'Created ' || COUNT(*) || ' terrain grid points' FROM terrain_grid_points;
SELECT 'Land hexagons: ' || COUNT(*) FROM terrain_grid WHERE hex_type = 'land';
SELECT 'Boundary hexagons: ' || COUNT(*) FROM terrain_grid WHERE hex_type = 'boundary';
SELECT 'Water hexagons: ' || COUNT(*) FROM terrain_grid WHERE hex_type = 'water';

-- Compare with water obstacle area
SELECT 
    'terrain_grid' AS source,
    COUNT(*) as count,
    SUM(ST_Area(geom)) / 1000000 as total_area_sq_km
FROM terrain_grid
UNION ALL
SELECT 
    'water_obstacles' AS source,
    COUNT(*) as count,
    SUM(ST_Area(geom)) / 1000000 as total_area_sq_km
FROM water_obstacles;
