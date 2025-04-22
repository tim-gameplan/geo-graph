-- 04_create_terrain_grid_3857.sql
-- Create a terrain grid that avoids water features
-- Uses EPSG:3857 (Web Mercator) for all operations
-- Parameters:
-- :cell_size_m - Cell size in meters for the hexagonal grid

-- Create terrain_grid table
DROP TABLE IF EXISTS terrain_grid CASCADE;
CREATE TABLE terrain_grid AS
WITH 
-- Create a hexagonal grid covering the extent of the data
-- Using EPSG:3857 for consistent meter-based operations
hex_grid AS (
    SELECT 
        ST_SetSRID((ST_HexagonGrid(200, (
            SELECT ST_Extent(geom) 
            FROM water_buf_dissolved
        ))).geom, 3857) AS geom
    FROM generate_series(1,1)
),
-- Filter out grid cells that intersect with water buffers
filtered_grid AS (
    SELECT hg.geom
    FROM hex_grid hg
    WHERE NOT EXISTS (
        SELECT 1 
        FROM water_buf_dissolved wb
        WHERE ST_Intersects(hg.geom, wb.geom)
    )
)
SELECT 
    ROW_NUMBER() OVER () AS id,
    geom,
    1.0 AS cost -- Placeholder for slope-based cost
FROM filtered_grid;

-- Create spatial index
CREATE INDEX ON terrain_grid USING GIST(geom);

-- Add SRID metadata to the geometry column
ALTER TABLE terrain_grid 
ALTER COLUMN geom TYPE geometry(Geometry, 3857) 
USING ST_SetSRID(geom, 3857);

-- Log the results
-- Note: Using ST_Area directly on EPSG:3857 geometries (in square meters)
SELECT 
    COUNT(*) as grid_cell_count,
    MIN(ST_Area(geom)) as min_cell_area_sqm,
    MAX(ST_Area(geom)) as max_cell_area_sqm,
    AVG(ST_Area(geom)) as avg_cell_area_sqm,
    SUM(ST_Area(geom)) / 1000000 as total_area_sq_km
FROM terrain_grid;

-- Compare with water buffer area
SELECT 
    'terrain_grid' AS source,
    COUNT(*) as count,
    SUM(ST_Area(geom)) / 1000000 as total_area_sq_km
FROM terrain_grid
UNION ALL
SELECT 
    'water_buf_dissolved' AS source,
    COUNT(*) as count,
    SUM(ST_Area(geom)) / 1000000 as total_area_sq_km
FROM water_buf_dissolved;

-- Calculate the percentage of the total area covered by water
WITH 
total_area AS (
    SELECT ST_Area(ST_SetSRID(ST_Envelope(ST_Extent(geom)), 3857)) / 1000000 as area_sq_km
    FROM water_buf_dissolved
),
water_area AS (
    SELECT SUM(ST_Area(geom)) / 1000000 as area_sq_km
    FROM water_buf_dissolved
),
terrain_area AS (
    SELECT SUM(ST_Area(geom)) / 1000000 as area_sq_km
    FROM terrain_grid
)
SELECT 
    total_area.area_sq_km as total_area_sq_km,
    water_area.area_sq_km as water_area_sq_km,
    terrain_area.area_sq_km as terrain_area_sq_km,
    (water_area.area_sq_km / total_area.area_sq_km) * 100 as water_percentage,
    (terrain_area.area_sq_km / total_area.area_sq_km) * 100 as terrain_percentage
FROM total_area, water_area, terrain_area;
