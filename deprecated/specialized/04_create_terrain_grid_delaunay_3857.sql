-- 04_create_terrain_grid_delaunay_3857.sql
-- Create a terrain grid using Delaunay triangulation
-- Uses EPSG:3857 (Web Mercator) for all operations
-- Parameters:
-- :grid_spacing - Cell size in meters for the point grid (used instead of cell_size_m)
-- :boundary_point_spacing - Spacing for points along boundaries

-- Create terrain_grid table
DROP TABLE IF EXISTS terrain_grid CASCADE;
DROP TABLE IF EXISTS terrain_triangulation CASCADE;

-- First, create a temporary table with a regular grid of points
CREATE TEMP TABLE temp_grid_points AS
WITH 
-- Create a regular grid of points covering the extent of the data
-- Using EPSG:3857 for consistent meter-based operations
grid_extent AS (
    SELECT ST_Extent(geom) AS extent
    FROM water_buf_dissolved
),
grid_points AS (
    SELECT 
        ST_SetSRID(
            ST_MakePoint(
                ST_XMin(extent) + (x * :grid_spacing),
                ST_YMin(extent) + (y * :grid_spacing)
            ),
            3857
        ) AS geom
    FROM grid_extent,
         generate_series(0, ceil((ST_XMax(extent) - ST_XMin(extent)) / :grid_spacing)::integer) AS x,
         generate_series(0, ceil((ST_YMax(extent) - ST_YMin(extent)) / :grid_spacing)::integer) AS y
)
-- Filter out points that intersect with water buffers
SELECT gp.geom
FROM grid_points gp
WHERE NOT EXISTS (
    SELECT 1 
    FROM water_buf_dissolved wb
    WHERE ST_Intersects(gp.geom, wb.geom)
);

-- Add points along water buffer boundaries for better edge representation
INSERT INTO temp_grid_points
WITH boundary_points AS (
    SELECT 
        geom,
        ST_Boundary(geom) AS boundary,
        ST_NPoints(ST_Boundary(geom)) AS num_points,
        ST_Length(ST_Boundary(geom)) AS boundary_length,
        -- Calculate step size (approximately every :boundary_point_spacing meters)
        GREATEST(1, ST_NPoints(ST_Boundary(geom)) / GREATEST(1, ST_Length(ST_Boundary(geom)) / :boundary_point_spacing)) AS step
    FROM water_buf_dissolved
)
SELECT 
    ST_PointN(boundary, n) AS geom
FROM boundary_points,
     generate_series(1, num_points, step::integer) AS n;

-- Remove duplicate points that might have been created
CREATE TEMP TABLE unique_grid_points AS
SELECT DISTINCT ON (ST_AsText(geom)) geom
FROM temp_grid_points;

-- Create the Delaunay triangulation
CREATE TABLE terrain_triangulation AS
SELECT 
    (ST_Dump(ST_DelaunayTriangles(ST_Collect(geom), 0.001, 0))).geom AS geom
FROM unique_grid_points;

-- Create spatial index on triangulation
CREATE INDEX ON terrain_triangulation USING GIST(geom);

-- Add SRID metadata to the geometry column
ALTER TABLE terrain_triangulation 
ALTER COLUMN geom TYPE geometry(Polygon, 3857) 
USING ST_SetSRID(geom, 3857);

-- Create terrain grid from triangulation centroids
CREATE TABLE terrain_grid AS
SELECT 
    ROW_NUMBER() OVER () AS id,
    ST_Centroid(geom) AS geom,
    1.0 AS cost -- Placeholder for slope-based cost
FROM terrain_triangulation
WHERE NOT EXISTS (
    SELECT 1 
    FROM water_buf_dissolved wb
    WHERE ST_Intersects(ST_Centroid(terrain_triangulation.geom), wb.geom)
);

-- Create spatial index
CREATE INDEX ON terrain_grid USING GIST(geom);

-- Add SRID metadata to the geometry column
ALTER TABLE terrain_grid 
ALTER COLUMN geom TYPE geometry(Point, 3857) 
USING ST_SetSRID(geom, 3857);

-- Log the results
SELECT 
    COUNT(*) as grid_cell_count,
    COUNT(*) * (:grid_spacing * :grid_spacing) / 1000000 as approx_area_sq_km
FROM terrain_grid;

-- Compare with water buffer area
SELECT 
    'terrain_grid' AS source,
    COUNT(*) as count,
    COUNT(*) * (:grid_spacing * :grid_spacing) / 1000000 as approx_area_sq_km
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
    SELECT COUNT(*) * (:grid_spacing * :grid_spacing) / 1000000 as area_sq_km
    FROM terrain_grid
)
SELECT 
    total_area.area_sq_km as total_area_sq_km,
    water_area.area_sq_km as water_area_sq_km,
    terrain_area.area_sq_km as terrain_area_sq_km,
    (water_area.area_sq_km / total_area.area_sq_km) * 100 as water_percentage,
    (terrain_area.area_sq_km / total_area.area_sq_km) * 100 as terrain_percentage
FROM total_area, water_area, terrain_area;
