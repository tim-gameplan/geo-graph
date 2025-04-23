/*
 * Terrain Grid Creation with Hexagonal Grid
 * 
 * This script creates a hexagonal terrain grid that avoids water features.
 * It uses ST_HexagonGrid for more natural terrain representation and movement patterns.
 */

-- Create terrain grid with EPSG:3857 coordinates
-- Parameters:
-- :storage_srid - SRID for storage (default: 3857)
-- :grid_spacing - Grid spacing in meters (default: 200)

-- Create terrain_grid table
DROP TABLE IF EXISTS terrain_grid CASCADE;
CREATE TABLE terrain_grid (
    id SERIAL PRIMARY KEY,
    geom GEOMETRY(POLYGON, :storage_srid),
    cost NUMERIC DEFAULT 1.0 -- Placeholder for terrain-based cost
);

-- Create the terrain grid
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
-- Filter out grid cells that intersect with water obstacles
filtered_grid AS (
    SELECT hg.geom
    FROM hex_grid hg
    WHERE NOT EXISTS (
        SELECT 1 
        FROM water_obstacles wo
        WHERE ST_Intersects(hg.geom, wo.geom)
    )
)
INSERT INTO terrain_grid (geom, cost)
SELECT 
    geom,
    1.0 AS cost -- Placeholder for terrain-based cost
FROM filtered_grid;

-- Create spatial index
CREATE INDEX terrain_grid_geom_idx ON terrain_grid USING GIST(geom);

-- Create terrain grid centroids for connectivity
DROP TABLE IF EXISTS terrain_grid_points CASCADE;
CREATE TABLE terrain_grid_points (
    id SERIAL PRIMARY KEY,
    grid_id INTEGER REFERENCES terrain_grid(id),
    geom GEOMETRY(POINT, :storage_srid)
);

-- Insert centroids
INSERT INTO terrain_grid_points (grid_id, geom)
SELECT 
    id,
    ST_Centroid(geom)
FROM 
    terrain_grid;

-- Create spatial index on points
CREATE INDEX terrain_grid_points_geom_idx ON terrain_grid_points USING GIST(geom);

-- Log the results
SELECT 'Created ' || COUNT(*) || ' terrain grid cells' FROM terrain_grid;
SELECT 'Created ' || COUNT(*) || ' terrain grid points' FROM terrain_grid_points;

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

-- Calculate the percentage of the total area covered by water
WITH 
total_area AS (
    SELECT ST_Area(ST_SetSRID(ST_Envelope(ST_Extent(geom)), :storage_srid)) / 1000000 as area_sq_km
    FROM dissolved_water_buffers
),
water_area AS (
    SELECT SUM(ST_Area(geom)) / 1000000 as area_sq_km
    FROM water_obstacles
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
