-- 06_create_boundary_edges_3857.sql
-- Create edges between different node types for the boundary hexagon layer approach

-- Drop existing tables if they exist
DROP TABLE IF EXISTS land_land_edges CASCADE;
DROP TABLE IF EXISTS land_boundary_edges CASCADE;
DROP TABLE IF EXISTS boundary_boundary_edges CASCADE;
DROP TABLE IF EXISTS boundary_water_edges CASCADE;
DROP TABLE IF EXISTS water_boundary_edges CASCADE;

-- Create land-to-land edges (similar to standard approach)
CREATE TABLE land_land_edges AS
SELECT
    t1.id AS source_id,
    t2.id AS target_id,
    ST_Length(ST_MakeLine(t1.geom, t2.geom)) AS length,
    ST_Length(ST_MakeLine(t1.geom, t2.geom)) / 5.0 AS cost, -- Normal speed on land (5 m/s)
    'land_land' AS edge_type,
    ST_MakeLine(t1.geom, t2.geom) AS geom
FROM
    terrain_grid_points t1
JOIN
    terrain_grid_points t2 ON ST_DWithin(t1.geom, t2.geom, :max_edge_length)
WHERE
    t1.id < t2.id
    AND t1.hex_type = 'land'
    AND t2.hex_type = 'land'
    AND NOT EXISTS (
        SELECT 1
        FROM water_obstacles
        WHERE ST_Intersects(water_obstacles.geom, ST_MakeLine(t1.geom, t2.geom))
    );

-- Create land-to-boundary edges
CREATE TABLE land_boundary_edges AS
SELECT
    t.id AS source_id,
    b.node_id AS target_id,
    ST_Length(ST_MakeLine(t.geom, b.geom)) AS length,
    ST_Length(ST_MakeLine(t.geom, b.geom)) / 5.0 AS cost, -- Normal speed on land (5 m/s)
    'land_boundary' AS edge_type,
    ST_MakeLine(t.geom, b.geom) AS geom
FROM
    terrain_grid_points t
JOIN
    boundary_nodes b ON ST_DWithin(t.geom, b.geom, :max_edge_length)
WHERE
    t.hex_type = 'land'
    AND NOT EXISTS (
        SELECT 1
        FROM water_obstacles
        WHERE ST_Intersects(water_obstacles.geom, ST_MakeLine(t.geom, b.geom))
    );

-- Create boundary-to-boundary edges
CREATE TABLE boundary_boundary_edges AS
SELECT
    b1.node_id AS source_id,
    b2.node_id AS target_id,
    ST_Length(ST_MakeLine(b1.geom, b2.geom)) AS length,
    ST_Length(ST_MakeLine(b1.geom, b2.geom)) / 5.0 AS cost, -- Normal speed on land (5 m/s)
    'boundary_boundary' AS edge_type,
    ST_MakeLine(b1.geom, b2.geom) AS geom
FROM
    boundary_nodes b1
JOIN
    boundary_nodes b2 ON ST_DWithin(b1.geom, b2.geom, :max_edge_length)
WHERE
    b1.node_id < b2.node_id
    AND NOT EXISTS (
        SELECT 1
        FROM water_obstacles
        WHERE ST_Intersects(water_obstacles.geom, ST_MakeLine(b1.geom, b2.geom))
    );

-- Create boundary-to-water edges
CREATE TABLE boundary_water_edges AS
SELECT
    b.node_id AS source_id,
    w.node_id AS target_id,
    ST_Length(ST_MakeLine(b.geom, w.geom)) AS length,
    ST_Length(ST_MakeLine(b.geom, w.geom)) / (5.0 * :water_speed_factor) AS cost, -- Slower speed for water boundary
    'boundary_water' AS edge_type,
    ST_MakeLine(b.geom, w.geom) AS geom
FROM
    boundary_nodes b
JOIN
    water_boundary_nodes w ON ST_DWithin(b.geom, w.geom, :max_edge_length)
WHERE
    NOT EXISTS (
        SELECT 1
        FROM water_obstacles
        WHERE ST_Contains(water_obstacles.geom, b.geom)
    );

-- Create water boundary edges
CREATE TABLE water_boundary_edges AS
WITH ordered_nodes AS (
    SELECT
        node_id,
        water_obstacle_id,
        geom,
        ST_Azimuth(geom, ST_Centroid(
            (SELECT geom FROM water_obstacles WHERE id = water_obstacle_id)
        )) AS azimuth
    FROM
        water_boundary_nodes
)
SELECT
    n1.node_id AS source_id,
    n2.node_id AS target_id,
    ST_Length(ST_MakeLine(n1.geom, n2.geom)) AS length,
    ST_Length(ST_MakeLine(n1.geom, n2.geom)) / (5.0 * :water_speed_factor) AS cost, -- Slower speed along water boundaries
    'water_boundary' AS edge_type,
    ST_MakeLine(n1.geom, n2.geom) AS geom
FROM
    ordered_nodes n1
JOIN
    ordered_nodes n2 ON n1.water_obstacle_id = n2.water_obstacle_id
    AND ST_DWithin(n1.geom, n2.geom, :boundary_edge_max_length)
WHERE
    n1.node_id < n2.node_id
    AND ABS(n1.azimuth - n2.azimuth) < 0.5; -- Only connect nodes with similar azimuth (nearby on the boundary)

-- Create spatial indexes
CREATE INDEX land_land_edges_geom_idx ON land_land_edges USING GIST (geom);
CREATE INDEX land_boundary_edges_geom_idx ON land_boundary_edges USING GIST (geom);
CREATE INDEX boundary_boundary_edges_geom_idx ON boundary_boundary_edges USING GIST (geom);
CREATE INDEX boundary_water_edges_geom_idx ON boundary_water_edges USING GIST (geom);
CREATE INDEX water_boundary_edges_geom_idx ON water_boundary_edges USING GIST (geom);

-- Log the results
SELECT 'Created ' || COUNT(*) || ' land-land edges' FROM land_land_edges;
SELECT 'Created ' || COUNT(*) || ' land-boundary edges' FROM land_boundary_edges;
SELECT 'Created ' || COUNT(*) || ' boundary-boundary edges' FROM boundary_boundary_edges;
SELECT 'Created ' || COUNT(*) || ' boundary-water edges' FROM boundary_water_edges;
SELECT 'Created ' || COUNT(*) || ' water-boundary edges' FROM water_boundary_edges;
