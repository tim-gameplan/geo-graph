-- 04_create_terrain_grid_boundary_3857.sql
-- Create terrain grid with boundary preservation for the boundary hexagon layer approach

-- Drop existing tables if they exist
DROP TABLE IF EXISTS complete_hex_grid CASCADE;
DROP TABLE IF EXISTS classified_hex_grid CASCADE;
DROP TABLE IF EXISTS adjacent_water_hexagons CASCADE;
DROP TABLE IF EXISTS water_hex_land_portions CASCADE;
DROP TABLE IF EXISTS terrain_grid CASCADE;
DROP TABLE IF EXISTS terrain_grid_points CASCADE;
DROP TABLE IF EXISTS water_obstacles CASCADE;

-- Create water obstacles table from dissolved water buffers
CREATE TABLE water_obstacles AS
SELECT 
    id,
    ST_MakeValid(geom) AS geom
FROM 
    dissolved_water_buffers;

-- Create a complete hexagonal grid
CREATE TABLE complete_hex_grid AS
SELECT 
    (ST_HexagonGrid(:grid_spacing, ST_Transform(ST_SetSRID(ST_Extent(way), 4326), 3857))).*
FROM 
    planet_osm_polygon
WHERE 
    ST_IsValid(way);

-- Classify hexagons as land, boundary, boundary_extension, or water
CREATE TABLE classified_hex_grid AS
SELECT
    hg.geom,
    CASE
        WHEN EXISTS (
            SELECT 1
            FROM water_obstacles wo
            WHERE ST_Contains(wo.geom, ST_Buffer(hg.geom, -1))
        ) THEN 'water'
        WHEN EXISTS (
            SELECT 1
            FROM water_obstacles wo
            WHERE ST_Intersects(wo.geom, hg.geom)
        ) THEN 'boundary'
        WHEN EXISTS (
            SELECT 1
            FROM water_obstacles wo
            JOIN complete_hex_grid chg ON ST_Intersects(wo.geom, chg.geom)
            WHERE ST_DWithin(hg.geom, chg.geom, :boundary_extension_distance)
            AND ST_Touches(hg.geom, chg.geom)
        ) THEN 'boundary_extension'  -- New classification
        ELSE 'land'
    END AS hex_type
FROM 
    complete_hex_grid hg;

-- Identify water hexagons that are adjacent to land or boundary hexagons
CREATE TABLE adjacent_water_hexagons AS
SELECT
    wh.geom AS water_hex_geom,
    array_agg(lh.hex_type) AS adjacent_types
FROM
    classified_hex_grid wh
JOIN
    classified_hex_grid lh ON ST_Touches(wh.geom, lh.geom)
WHERE
    wh.hex_type = 'water'
    AND lh.hex_type IN ('land', 'boundary', 'boundary_extension')
GROUP BY
    wh.geom;

-- Create a new table to store potential land portions within water hexagons
CREATE TABLE water_hex_land_portions AS
SELECT
    wh.water_hex_geom,
    ST_Difference(wh.water_hex_geom, ST_Union(wo.geom)) AS land_portion
FROM
    adjacent_water_hexagons wh
JOIN
    water_obstacles wo ON ST_Intersects(wh.water_hex_geom, wo.geom)
GROUP BY
    wh.water_hex_geom
HAVING
    ST_Area(ST_Difference(wh.water_hex_geom, ST_Union(wo.geom))) > 0;

-- Create the terrain grid (including boundary_extension and water_with_land hexagons)
CREATE TABLE terrain_grid AS
SELECT 
    ROW_NUMBER() OVER () AS id,
    geom, 
    hex_type
FROM 
    classified_hex_grid
WHERE 
    hex_type IN ('land', 'boundary', 'boundary_extension')
UNION ALL
SELECT
    ROW_NUMBER() OVER () + (SELECT COUNT(*) FROM classified_hex_grid WHERE hex_type IN ('land', 'boundary', 'boundary_extension')) AS id,
    water_hex_geom AS geom,
    'water_with_land' AS hex_type
FROM
    water_hex_land_portions;

-- Create terrain grid points (centroids of terrain grid cells)
CREATE TABLE terrain_grid_points AS
SELECT
    t.id,
    t.hex_type,
    ST_Centroid(t.geom) AS geom,
    EXISTS (
        SELECT 1
        FROM water_obstacles wo
        WHERE ST_Intersects(wo.geom, ST_Centroid(t.geom))
    ) AS is_water
FROM
    terrain_grid t;

-- Create spatial indexes
CREATE INDEX terrain_grid_geom_idx ON terrain_grid USING GIST (geom);
CREATE INDEX terrain_grid_points_geom_idx ON terrain_grid_points USING GIST (geom);
CREATE INDEX water_obstacles_geom_idx ON water_obstacles USING GIST (geom);
CREATE INDEX adjacent_water_hexagons_geom_idx ON adjacent_water_hexagons USING GIST (water_hex_geom);
CREATE INDEX water_hex_land_portions_geom_idx ON water_hex_land_portions USING GIST (water_hex_geom);

-- Log the results
SELECT 'Created ' || COUNT(*) || ' terrain grid cells' FROM terrain_grid;
SELECT 'Created ' || COUNT(*) || ' terrain grid points' FROM terrain_grid_points;
SELECT 'Land hexagons: ' || COUNT(*) FROM terrain_grid WHERE hex_type = 'land';
SELECT 'Boundary hexagons: ' || COUNT(*) FROM terrain_grid WHERE hex_type = 'boundary';
SELECT 'Boundary extension hexagons: ' || COUNT(*) FROM terrain_grid WHERE hex_type = 'boundary_extension';
SELECT 'Water with land hexagons: ' || COUNT(*) FROM terrain_grid WHERE hex_type = 'water_with_land';
SELECT 'Adjacent water hexagons: ' || COUNT(*) FROM adjacent_water_hexagons;
SELECT 'Water hex land portions: ' || COUNT(*) FROM water_hex_land_portions;
