-- 04_create_terrain_grid.sql
-- Create a terrain grid that avoids water features
-- Parameters:
-- :cell_size - Cell size in meters for the hexagonal grid

-- Create terrain_grid table
DROP TABLE IF EXISTS terrain_grid CASCADE;
CREATE TABLE terrain_grid AS
WITH 
-- Create a hexagonal grid covering the extent of the data
hex_grid AS (
    SELECT 
        ST_SetSRID((ST_HexagonGrid(:cell_size, (
            SELECT ST_Extent(geom) 
            FROM water_buf_dissolved
        ))).geom, 4326) AS geom
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

-- Log the results
SELECT 
    COUNT(*) as grid_cell_count,
    MIN(ST_Area(geom::geography)) as min_cell_area_sqm,
    MAX(ST_Area(geom::geography)) as max_cell_area_sqm,
    AVG(ST_Area(geom::geography)) as avg_cell_area_sqm,
    SUM(ST_Area(geom::geography)) / 1000000 as total_area_sq_km
FROM terrain_grid;

-- Compare with water buffer area
SELECT 
    'terrain_grid' AS source,
    COUNT(*) as count,
    SUM(ST_Area(geom::geography)) / 1000000 as total_area_sq_km
FROM terrain_grid
UNION ALL
SELECT 
    'water_buf_dissolved' AS source,
    COUNT(*) as count,
    SUM(ST_Area(geom::geography)) / 1000000 as total_area_sq_km
FROM water_buf_dissolved;

-- Calculate the percentage of the total area covered by water
WITH 
total_area AS (
    SELECT ST_Area(ST_SetSRID(ST_Envelope(ST_Extent(geom)), 4326)::geography) / 1000000 as area_sq_km
    FROM water_buf_dissolved
),
water_area AS (
    SELECT SUM(ST_Area(geom::geography)) / 1000000 as area_sq_km
    FROM water_buf_dissolved
),
terrain_area AS (
    SELECT SUM(ST_Area(geom::geography)) / 1000000 as area_sq_km
    FROM terrain_grid
)
SELECT 
    total_area.area_sq_km as total_area_sq_km,
    water_area.area_sq_km as water_area_sq_km,
    terrain_area.area_sq_km as terrain_area_sq_km,
    (water_area.area_sq_km / total_area.area_sq_km) * 100 as water_percentage,
    (terrain_area.area_sq_km / total_area.area_sq_km) * 100 as terrain_percentage
FROM total_area, water_area, terrain_area;
