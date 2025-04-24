/*
 * Direct Water Obstacle Boundary Conversion
 * 
 * This script directly converts water obstacle polygons to graph elements:
 * - Extracts vertices from water obstacles as graph nodes
 * - Creates edges between adjacent vertices
 * 
 * This approach preserves the exact shape of water obstacles and creates
 * a clean representation of water boundaries for navigation.
 */

-- Parameters:
-- :storage_srid - SRID for storage (default: 3857)

-- Create obstacle boundary nodes table
DROP TABLE IF EXISTS obstacle_boundary_nodes CASCADE;
CREATE TABLE obstacle_boundary_nodes (
    node_id SERIAL PRIMARY KEY,
    water_obstacle_id INTEGER,
    point_order INTEGER,
    geom GEOMETRY(POINT, :storage_srid)
);

-- Create obstacle boundary edges table
DROP TABLE IF EXISTS obstacle_boundary_edges CASCADE;
CREATE TABLE obstacle_boundary_edges (
    edge_id SERIAL PRIMARY KEY,
    source_node_id INTEGER,
    target_node_id INTEGER,
    water_obstacle_id INTEGER,
    length NUMERIC,
    geom GEOMETRY(LINESTRING, :storage_srid)
);

-- Extract boundary nodes from water obstacles
INSERT INTO obstacle_boundary_nodes (water_obstacle_id, point_order, geom)
SELECT 
    id AS water_obstacle_id,
    (ST_DumpPoints(ST_ExteriorRing(geom))).path[1] AS point_order,
    (ST_DumpPoints(ST_ExteriorRing(geom))).geom AS geom
FROM 
    water_obstacles;

-- Create edges between adjacent boundary nodes
INSERT INTO obstacle_boundary_edges (source_node_id, target_node_id, water_obstacle_id, length, geom)
WITH ordered_nodes AS (
    SELECT 
        node_id,
        water_obstacle_id,
        point_order,
        geom,
        LEAD(node_id) OVER (PARTITION BY water_obstacle_id ORDER BY point_order) AS next_node_id,
        LEAD(geom) OVER (PARTITION BY water_obstacle_id ORDER BY point_order) AS next_geom,
        MAX(point_order) OVER (PARTITION BY water_obstacle_id) AS max_order
    FROM 
        obstacle_boundary_nodes
)
-- Connect consecutive nodes
SELECT 
    node_id AS source_node_id,
    next_node_id AS target_node_id,
    water_obstacle_id,
    ST_Length(ST_MakeLine(geom, next_geom)) AS length,
    ST_MakeLine(geom, next_geom) AS geom
FROM 
    ordered_nodes
WHERE 
    next_node_id IS NOT NULL
UNION ALL
-- Connect last node back to first node to close the loop
SELECT 
    n1.node_id AS source_node_id,
    n2.node_id AS target_node_id,
    n1.water_obstacle_id,
    ST_Length(ST_MakeLine(n1.geom, n2.geom)) AS length,
    ST_MakeLine(n1.geom, n2.geom) AS geom
FROM 
    ordered_nodes n1
JOIN 
    obstacle_boundary_nodes n2 
    ON n1.water_obstacle_id = n2.water_obstacle_id AND n2.point_order = 1
WHERE 
    n1.point_order = n1.max_order;

-- Create spatial indexes
CREATE INDEX obstacle_boundary_nodes_geom_idx ON obstacle_boundary_nodes USING GIST (geom);
CREATE INDEX obstacle_boundary_edges_geom_idx ON obstacle_boundary_edges USING GIST (geom);

-- Log the results
SELECT 'Created ' || COUNT(*) || ' obstacle boundary nodes' FROM obstacle_boundary_nodes;
SELECT 'Created ' || COUNT(*) || ' obstacle boundary edges' FROM obstacle_boundary_edges;

-- Count nodes and edges per water obstacle
SELECT 
    water_obstacle_id, 
    COUNT(*) AS node_count
FROM 
    obstacle_boundary_nodes
GROUP BY 
    water_obstacle_id
ORDER BY 
    node_count DESC
LIMIT 10;

SELECT 
    water_obstacle_id, 
    COUNT(*) AS edge_count
FROM 
    obstacle_boundary_edges
GROUP BY 
    water_obstacle_id
ORDER BY 
    edge_count DESC
LIMIT 10;
