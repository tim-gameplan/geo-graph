-- Voronoi Connection Strategies Test Script
-- This script demonstrates and compares different connection strategies
-- for connecting terrain grid points to water obstacle boundaries.

-- Setup: Create test tables
DROP TABLE IF EXISTS test_water_obstacles;
DROP TABLE IF EXISTS test_terrain_points;
DROP TABLE IF EXISTS test_boundary_nodes;
DROP TABLE IF EXISTS test_connections_nearest;
DROP TABLE IF EXISTS test_connections_line_to_point;
DROP TABLE IF EXISTS test_connections_voronoi;
DROP TABLE IF EXISTS test_connections_reversed_voronoi;
DROP TABLE IF EXISTS test_voronoi_cells;
DROP TABLE IF EXISTS test_reversed_voronoi_cells;

-- Create a simple water obstacle (a lake)
CREATE TABLE test_water_obstacles (
    id SERIAL PRIMARY KEY,
    name TEXT,
    geom GEOMETRY(POLYGON, 3857)
);

-- Insert a simple lake
INSERT INTO test_water_obstacles (name, geom)
VALUES (
    'Test Lake',
    ST_Buffer(
        ST_SetSRID(ST_MakePoint(0, 0), 3857),
        1000
    )
);

-- Create terrain grid points around the lake
CREATE TABLE test_terrain_points (
    id SERIAL PRIMARY KEY,
    hex_type TEXT,
    geom GEOMETRY(POINT, 3857)
);

-- Insert terrain points in a grid pattern around the lake
-- First, create a grid of points
WITH grid AS (
    SELECT 
        generate_series(-1500, 1500, 300) AS x,
        generate_series(-1500, 1500, 300) AS y
)
INSERT INTO test_terrain_points (hex_type, geom)
SELECT
    CASE
        WHEN ST_Contains(
            (SELECT geom FROM test_water_obstacles WHERE id = 1),
            ST_SetSRID(ST_MakePoint(x, y), 3857)
        ) THEN 'water'
        WHEN ST_DWithin(
            (SELECT geom FROM test_water_obstacles WHERE id = 1),
            ST_SetSRID(ST_MakePoint(x, y), 3857),
            300
        ) THEN 'boundary'
        ELSE 'land'
    END AS hex_type,
    ST_SetSRID(ST_MakePoint(x, y), 3857) AS geom
FROM grid
WHERE NOT ST_Contains(
    (SELECT geom FROM test_water_obstacles WHERE id = 1),
    ST_SetSRID(ST_MakePoint(x, y), 3857)
);

-- Create boundary nodes along the water obstacle boundary
CREATE TABLE test_boundary_nodes (
    node_id SERIAL PRIMARY KEY,
    water_obstacle_id INTEGER,
    geom GEOMETRY(POINT, 3857)
);

-- Insert boundary nodes at regular intervals along the lake boundary
INSERT INTO test_boundary_nodes (water_obstacle_id, geom)
SELECT 
    1 AS water_obstacle_id,
    (ST_DumpPoints(ST_Segmentize(ST_ExteriorRing(geom), 200))).geom AS geom
FROM 
    test_water_obstacles
WHERE 
    id = 1;

-- 1. Simple Nearest Neighbor Strategy
-- Connect each boundary terrain point to the nearest boundary node
CREATE TABLE test_connections_nearest (
    id SERIAL PRIMARY KEY,
    terrain_point_id INTEGER,
    boundary_node_id INTEGER,
    distance FLOAT,
    geom GEOMETRY(LINESTRING, 3857)
);

INSERT INTO test_connections_nearest (terrain_point_id, boundary_node_id, distance, geom)
WITH nearest_nodes AS (
    SELECT 
        tp.id AS terrain_point_id,
        bn.node_id AS boundary_node_id,
        ST_Distance(tp.geom, bn.geom) AS distance,
        ROW_NUMBER() OVER (
            PARTITION BY tp.id 
            ORDER BY ST_Distance(tp.geom, bn.geom)
        ) AS rank
    FROM 
        test_terrain_points tp
    CROSS JOIN 
        test_boundary_nodes bn
    WHERE 
        tp.hex_type = 'boundary'
)
SELECT 
    terrain_point_id,
    boundary_node_id,
    distance,
    ST_MakeLine(
        (SELECT geom FROM test_terrain_points WHERE id = terrain_point_id),
        (SELECT geom FROM test_boundary_nodes WHERE node_id = boundary_node_id)
    ) AS geom
FROM 
    nearest_nodes
WHERE 
    rank = 1;

-- 2. Line-to-Point Connection Strategy
-- Connect each boundary terrain point to the closest point on the water obstacle boundary
CREATE TABLE test_connections_line_to_point (
    id SERIAL PRIMARY KEY,
    terrain_point_id INTEGER,
    closest_point GEOMETRY(POINT, 3857),
    distance FLOAT,
    geom GEOMETRY(LINESTRING, 3857)
);

INSERT INTO test_connections_line_to_point (terrain_point_id, closest_point, distance, geom)
SELECT 
    tp.id AS terrain_point_id,
    ST_ClosestPoint(wo.geom, tp.geom) AS closest_point,
    ST_Distance(tp.geom, wo.geom) AS distance,
    ST_MakeLine(tp.geom, ST_ClosestPoint(wo.geom, tp.geom)) AS geom
FROM 
    test_terrain_points tp
CROSS JOIN 
    test_water_obstacles wo
WHERE 
    tp.hex_type = 'boundary'
    AND wo.id = 1;

-- 3. Standard Voronoi Connection Strategy
-- Create Voronoi cells for boundary nodes and connect terrain points to the node whose cell they fall within
CREATE TABLE test_voronoi_cells (
    boundary_node_id INTEGER PRIMARY KEY,
    cell_geom GEOMETRY(POLYGON, 3857)
);

-- Create Voronoi cells for boundary nodes
WITH voronoi_polygons AS (
    SELECT ST_VoronoiPolygons(ST_Collect(geom)) AS geom
    FROM test_boundary_nodes
),
voronoi_dump AS (
    SELECT (ST_Dump(geom)).geom AS cell_geom
    FROM voronoi_polygons
)
INSERT INTO test_voronoi_cells (boundary_node_id, cell_geom)
SELECT 
    bn.node_id AS boundary_node_id,
    vd.cell_geom
FROM 
    voronoi_dump vd
JOIN 
    test_boundary_nodes bn
    ON ST_Contains(vd.cell_geom, bn.geom);

-- Connect terrain points to the boundary node whose Voronoi cell they fall within
CREATE TABLE test_connections_voronoi (
    id SERIAL PRIMARY KEY,
    terrain_point_id INTEGER,
    boundary_node_id INTEGER,
    distance FLOAT,
    geom GEOMETRY(LINESTRING, 3857)
);

INSERT INTO test_connections_voronoi (terrain_point_id, boundary_node_id, distance, geom)
SELECT 
    tp.id AS terrain_point_id,
    vc.boundary_node_id,
    ST_Distance(
        tp.geom,
        (SELECT geom FROM test_boundary_nodes WHERE node_id = vc.boundary_node_id)
    ) AS distance,
    ST_MakeLine(
        tp.geom,
        (SELECT geom FROM test_boundary_nodes WHERE node_id = vc.boundary_node_id)
    ) AS geom
FROM 
    test_terrain_points tp
JOIN 
    test_voronoi_cells vc ON ST_Intersects(vc.cell_geom, tp.geom)
WHERE 
    tp.hex_type = 'boundary';

-- 4. Reversed Voronoi Connection Strategy
-- Create Voronoi cells for boundary terrain points and connect them to boundary nodes that fall within their cells
CREATE TABLE test_reversed_voronoi_cells (
    terrain_point_id INTEGER PRIMARY KEY,
    cell_geom GEOMETRY(POLYGON, 3857)
);

-- Create Voronoi cells for boundary terrain points
WITH boundary_terrain_points AS (
    SELECT id, geom
    FROM test_terrain_points
    WHERE hex_type = 'boundary'
),
voronoi_polygons AS (
    SELECT ST_VoronoiPolygons(ST_Collect(geom)) AS geom
    FROM boundary_terrain_points
),
voronoi_dump AS (
    SELECT (ST_Dump(geom)).geom AS cell_geom
    FROM voronoi_polygons
)
INSERT INTO test_reversed_voronoi_cells (terrain_point_id, cell_geom)
SELECT 
    btp.id AS terrain_point_id,
    vd.cell_geom
FROM 
    voronoi_dump vd
JOIN 
    boundary_terrain_points btp
    ON ST_Contains(vd.cell_geom, btp.geom);

-- Connect boundary terrain points to boundary nodes that fall within their Voronoi cells
CREATE TABLE test_connections_reversed_voronoi (
    id SERIAL PRIMARY KEY,
    terrain_point_id INTEGER,
    boundary_node_id INTEGER,
    distance FLOAT,
    geom GEOMETRY(LINESTRING, 3857)
);

INSERT INTO test_connections_reversed_voronoi (terrain_point_id, boundary_node_id, distance, geom)
SELECT 
    vc.terrain_point_id,
    bn.node_id AS boundary_node_id,
    ST_Distance(
        (SELECT geom FROM test_terrain_points WHERE id = vc.terrain_point_id),
        bn.geom
    ) AS distance,
    ST_MakeLine(
        (SELECT geom FROM test_terrain_points WHERE id = vc.terrain_point_id),
        bn.geom
    ) AS geom
FROM 
    test_reversed_voronoi_cells vc
JOIN 
    test_boundary_nodes bn ON ST_Intersects(vc.cell_geom, bn.geom);

-- Analysis: Compare the different connection strategies

-- Count the number of connections for each strategy
SELECT 'Nearest Neighbor' AS strategy, COUNT(*) AS connection_count FROM test_connections_nearest
UNION ALL
SELECT 'Line-to-Point' AS strategy, COUNT(*) AS connection_count FROM test_connections_line_to_point
UNION ALL
SELECT 'Voronoi' AS strategy, COUNT(*) AS connection_count FROM test_connections_voronoi
UNION ALL
SELECT 'Reversed Voronoi' AS strategy, COUNT(*) AS connection_count FROM test_connections_reversed_voronoi;

-- Calculate average distance for each strategy
SELECT 'Nearest Neighbor' AS strategy, AVG(distance) AS avg_distance FROM test_connections_nearest
UNION ALL
SELECT 'Line-to-Point' AS strategy, AVG(distance) AS avg_distance FROM test_connections_line_to_point
UNION ALL
SELECT 'Voronoi' AS strategy, AVG(distance) AS avg_distance FROM test_connections_voronoi
UNION ALL
SELECT 'Reversed Voronoi' AS strategy, AVG(distance) AS avg_distance FROM test_connections_reversed_voronoi;

-- Count how many boundary nodes are connected for each strategy
SELECT 'Nearest Neighbor' AS strategy, COUNT(DISTINCT boundary_node_id) AS connected_nodes FROM test_connections_nearest
UNION ALL
SELECT 'Voronoi' AS strategy, COUNT(DISTINCT boundary_node_id) AS connected_nodes FROM test_connections_voronoi
UNION ALL
SELECT 'Reversed Voronoi' AS strategy, COUNT(DISTINCT boundary_node_id) AS connected_nodes FROM test_connections_reversed_voronoi;

-- Count how many terrain points are connected for each strategy
SELECT 'Nearest Neighbor' AS strategy, COUNT(DISTINCT terrain_point_id) AS connected_terrain_points FROM test_connections_nearest
UNION ALL
SELECT 'Line-to-Point' AS strategy, COUNT(DISTINCT terrain_point_id) AS connected_terrain_points FROM test_connections_line_to_point
UNION ALL
SELECT 'Voronoi' AS strategy, COUNT(DISTINCT terrain_point_id) AS connected_terrain_points FROM test_connections_voronoi
UNION ALL
SELECT 'Reversed Voronoi' AS strategy, COUNT(DISTINCT terrain_point_id) AS connected_terrain_points FROM test_connections_reversed_voronoi;

-- Analyze connection distribution for boundary nodes
SELECT 'Nearest Neighbor' AS strategy, boundary_node_id, COUNT(*) AS connection_count
FROM test_connections_nearest
GROUP BY boundary_node_id
ORDER BY connection_count DESC
LIMIT 5;

SELECT 'Voronoi' AS strategy, boundary_node_id, COUNT(*) AS connection_count
FROM test_connections_voronoi
GROUP BY boundary_node_id
ORDER BY connection_count DESC
LIMIT 5;

SELECT 'Reversed Voronoi' AS strategy, boundary_node_id, COUNT(*) AS connection_count
FROM test_connections_reversed_voronoi
GROUP BY boundary_node_id
ORDER BY connection_count DESC
LIMIT 5;

-- Create a view for visualization
CREATE OR REPLACE VIEW test_visualization AS
SELECT 
    'Water Obstacle' AS layer,
    id::TEXT AS id,
    geom
FROM 
    test_water_obstacles
UNION ALL
SELECT 
    'Terrain Points' AS layer,
    id::TEXT AS id,
    geom
FROM 
    test_terrain_points
UNION ALL
SELECT 
    'Boundary Nodes' AS layer,
    node_id::TEXT AS id,
    geom
FROM 
    test_boundary_nodes
UNION ALL
SELECT 
    'Nearest Neighbor Connections' AS layer,
    id::TEXT AS id,
    geom
FROM 
    test_connections_nearest
UNION ALL
SELECT 
    'Line-to-Point Connections' AS layer,
    id::TEXT AS id,
    geom
FROM 
    test_connections_line_to_point
UNION ALL
SELECT 
    'Voronoi Connections' AS layer,
    id::TEXT AS id,
    geom
FROM 
    test_connections_voronoi
UNION ALL
SELECT 
    'Reversed Voronoi Connections' AS layer,
    id::TEXT AS id,
    geom
FROM 
    test_connections_reversed_voronoi
UNION ALL
SELECT 
    'Voronoi Cells' AS layer,
    boundary_node_id::TEXT AS id,
    cell_geom AS geom
FROM 
    test_voronoi_cells
UNION ALL
SELECT 
    'Reversed Voronoi Cells' AS layer,
    terrain_point_id::TEXT AS id,
    cell_geom AS geom
FROM 
    test_reversed_voronoi_cells;

-- Instructions for visualization:
-- 1. Use QGIS or another GIS tool to connect to the database
-- 2. Add the test_visualization view as a layer
-- 3. Style the layers by the 'layer' attribute to see the different components
-- 4. Compare the different connection strategies visually

-- Cleanup (uncomment to remove test tables)
-- DROP TABLE IF EXISTS test_water_obstacles;
-- DROP TABLE IF EXISTS test_terrain_points;
-- DROP TABLE IF EXISTS test_boundary_nodes;
-- DROP TABLE IF EXISTS test_connections_nearest;
-- DROP TABLE IF EXISTS test_connections_line_to_point;
-- DROP TABLE IF EXISTS test_connections_voronoi;
-- DROP TABLE IF EXISTS test_connections_reversed_voronoi;
-- DROP TABLE IF EXISTS test_voronoi_cells;
-- DROP TABLE IF EXISTS test_reversed_voronoi_cells;
-- DROP VIEW IF EXISTS test_visualization;
