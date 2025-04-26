/*
 * Hexagon Obstacle Boundary Graph Creation
 * 
 * This script creates a graph that combines:
 * - Hexagonal terrain grid
 * - Water obstacle boundaries
 * - Connections between terrain grid and water boundaries
 * 
 * This approach preserves the exact shape of water obstacles while using a hexagonal grid
 * for better terrain representation.
 */

-- Parameters:
-- :storage_srid - SRID for storage (default: 3857)
-- :max_connection_distance - Maximum distance for connecting terrain points to boundary nodes (default: 1000)
-- :water_speed_factor - Speed factor for water edges (default: 0.2)
-- :max_connections_per_boundary_node - Maximum number of connections per boundary node (default: 5)
-- :max_connections_per_terrain_point - Maximum number of connections per terrain point (default: 2)
-- :grid_spacing - Grid spacing for the hexagonal grid (default: 200)

-- Create obstacle boundary nodes table
DROP TABLE IF EXISTS obstacle_boundary_nodes CASCADE;
CREATE TABLE obstacle_boundary_nodes (
    node_id SERIAL PRIMARY KEY,
    water_obstacle_id INTEGER,
    point_order INTEGER,
    geom geometry(POINT)
);

-- Create obstacle boundary edges table
DROP TABLE IF EXISTS obstacle_boundary_edges CASCADE;
CREATE TABLE obstacle_boundary_edges (
    edge_id SERIAL PRIMARY KEY,
    source_node_id INTEGER,
    target_node_id INTEGER,
    water_obstacle_id INTEGER,
    length NUMERIC,
    geom geometry(LINESTRING)
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

-- Create obstacle boundary connection edges table
DROP TABLE IF EXISTS obstacle_boundary_connection_edges CASCADE;
CREATE TABLE obstacle_boundary_connection_edges (
    edge_id SERIAL PRIMARY KEY,
    terrain_node_id INTEGER,
    boundary_node_id INTEGER,
    water_obstacle_id INTEGER,
    length NUMERIC,
    geom geometry(LINESTRING)
);

-- Create a dedicated terrain edges table
DROP TABLE IF EXISTS terrain_edges CASCADE;
CREATE TABLE terrain_edges (
    edge_id SERIAL PRIMARY KEY,
    source_id INTEGER,
    target_id INTEGER,
    source_type TEXT,
    target_type TEXT,
    length NUMERIC,
    geom geometry(LINESTRING)
);

-- Create terrain edges between adjacent hexagons
-- This approach directly uses terrain_grid_points without temporary tables
INSERT INTO terrain_edges (source_id, target_id, source_type, target_type, length, geom)
SELECT 
    t1.id AS source_id,
    t2.id AS target_id,
    t1.hex_type AS source_type,
    t2.hex_type AS target_type,
    ST_Distance(t1.geom, t2.geom) AS length,
    ST_MakeLine(t1.geom, t2.geom) AS geom
FROM 
    terrain_grid_points t1
JOIN 
    terrain_grid_points t2
    ON t1.id < t2.id -- Avoid duplicate edges
    AND ST_DWithin(t1.geom, t2.geom, 500) -- Use a fixed distance of 500m for better connectivity
WHERE 
    -- Don't connect any water hexagons at all
    t1.hex_type != 'water' AND t2.hex_type != 'water'
    -- Ensure the edge doesn't cross any water obstacles
    AND NOT EXISTS (
        SELECT 1
        FROM water_obstacles wo
        WHERE ST_Crosses(ST_MakeLine(t1.geom, t2.geom), wo.geom)
    );
    -- Note: We've added a water obstacle crossing check to ensure terrain edges don't cross water

-- Create spatial index on terrain edges
CREATE INDEX terrain_edges_geom_idx ON terrain_edges USING GIST (geom);
CREATE INDEX terrain_edges_source_id_idx ON terrain_edges (source_id);
CREATE INDEX terrain_edges_target_id_idx ON terrain_edges (target_id);

-- Connect terrain grid points to obstacle boundary nodes
-- Only connect land and boundary hexagons, not water hexagons
-- Limit the number of connections per boundary node and per terrain point
INSERT INTO obstacle_boundary_connection_edges (terrain_node_id, boundary_node_id, water_obstacle_id, length, geom)
WITH potential_connections AS (
    -- For each terrain point that is not a water hexagon, find all nearby boundary nodes
    SELECT 
        tgp.id AS terrain_node_id,
        obn.node_id AS boundary_node_id,
        obn.water_obstacle_id,
        ST_Distance(tgp.geom, obn.geom) AS distance,
        ST_MakeLine(tgp.geom, obn.geom) AS geom,
        -- Rank connections by distance for each terrain point
        ROW_NUMBER() OVER (PARTITION BY tgp.id ORDER BY ST_Distance(tgp.geom, obn.geom)) AS terrain_rank,
        -- Rank connections by distance for each boundary node
        ROW_NUMBER() OVER (PARTITION BY obn.node_id ORDER BY ST_Distance(tgp.geom, obn.geom)) AS boundary_rank
    FROM 
        terrain_grid_points tgp
    CROSS JOIN 
        obstacle_boundary_nodes obn
    WHERE 
        ST_DWithin(tgp.geom, obn.geom, :max_connection_distance)
        -- Only connect terrain points that are not water hexagons
        AND tgp.hex_type != 'water'
        -- Prioritize boundary hexagons over land hexagons
        AND (tgp.hex_type = 'boundary' OR NOT EXISTS (
            SELECT 1 FROM terrain_grid_points tgp2
            WHERE tgp2.hex_type = 'boundary'
            AND ST_DWithin(tgp2.geom, obn.geom, :max_connection_distance)
        ))
        -- Ensure the connection line doesn't cross through the water obstacle
        AND NOT EXISTS (
            SELECT 1
            FROM water_obstacles wo
            WHERE wo.id = obn.water_obstacle_id
            AND ST_Crosses(ST_MakeLine(tgp.geom, obn.geom), wo.geom)
        )
)
SELECT 
    terrain_node_id,
    boundary_node_id,
    water_obstacle_id,
    distance AS length,
    geom
FROM 
    potential_connections
WHERE 
    -- Limit the number of connections per terrain point
    terrain_rank <= :max_connections_per_terrain_point
    -- Limit the number of connections per boundary node
    AND boundary_rank <= :max_connections_per_boundary_node;

-- Create a unified edges table
DROP TABLE IF EXISTS unified_obstacle_edges CASCADE;
CREATE TABLE unified_obstacle_edges (
    edge_id SERIAL PRIMARY KEY,
    source_id INTEGER,
    target_id INTEGER,
    length NUMERIC,
    cost NUMERIC, -- Travel time cost
    edge_type TEXT, -- 'terrain', 'boundary', or 'connection'
    speed_factor NUMERIC,
    is_water BOOLEAN,
    geom geometry(LINESTRING)
);

-- Insert terrain edges from the dedicated terrain_edges table
INSERT INTO unified_obstacle_edges (source_id, target_id, length, cost, edge_type, speed_factor, is_water, geom)
SELECT 
    source_id,
    target_id,
    length,
    CASE
        -- Higher cost for water-boundary connections
        WHEN source_type = 'water' OR target_type = 'water' THEN length / (5.0 * :water_speed_factor)
        -- Medium cost for boundary-boundary connections
        WHEN source_type = 'boundary' AND target_type = 'boundary' THEN length / (5.0 * 0.8)
        -- Normal cost for land connections
        ELSE length / 5.0
    END AS cost,
    'terrain' AS edge_type,
    CASE
        WHEN source_type = 'water' OR target_type = 'water' THEN :water_speed_factor
        WHEN source_type = 'boundary' AND target_type = 'boundary' THEN 0.8
        ELSE 1.0
    END AS speed_factor,
    source_type = 'water' OR target_type = 'water' AS is_water,
    geom
FROM 
    terrain_edges;

-- Insert obstacle boundary edges
INSERT INTO unified_obstacle_edges (source_id, target_id, length, cost, edge_type, speed_factor, is_water, geom)
SELECT 
    source_node_id AS source_id,
    target_node_id AS target_id,
    length,
    length / (5.0 * :water_speed_factor) AS cost, -- Slower speed along water boundaries
    'boundary' AS edge_type,
    :water_speed_factor AS speed_factor,
    TRUE AS is_water,
    geom
FROM 
    obstacle_boundary_edges;

-- Insert connection edges
INSERT INTO unified_obstacle_edges (source_id, target_id, length, cost, edge_type, speed_factor, is_water, geom)
SELECT 
    terrain_node_id AS source_id,
    boundary_node_id AS target_id,
    length,
    length / 5.0 AS cost, -- Normal speed for connections
    'connection' AS edge_type,
    1.0 AS speed_factor,
    FALSE AS is_water,
    geom
FROM 
    obstacle_boundary_connection_edges;

-- Create spatial indexes
CREATE INDEX obstacle_boundary_nodes_geom_idx ON obstacle_boundary_nodes USING GIST (geom);
CREATE INDEX obstacle_boundary_edges_geom_idx ON obstacle_boundary_edges USING GIST (geom);
CREATE INDEX obstacle_boundary_connection_edges_geom_idx ON obstacle_boundary_connection_edges USING GIST (geom);
CREATE INDEX unified_obstacle_edges_geom_idx ON unified_obstacle_edges USING GIST (geom);
CREATE INDEX unified_obstacle_edges_source_id_idx ON unified_obstacle_edges (source_id);
CREATE INDEX unified_obstacle_edges_target_id_idx ON unified_obstacle_edges (target_id);
CREATE INDEX unified_obstacle_edges_edge_type_idx ON unified_obstacle_edges (edge_type);
CREATE INDEX unified_obstacle_edges_is_water_idx ON unified_obstacle_edges (is_water);

-- Log the results
SELECT 'Created ' || COUNT(*) || ' obstacle boundary nodes' FROM obstacle_boundary_nodes;
SELECT 'Created ' || COUNT(*) || ' obstacle boundary edges' FROM obstacle_boundary_edges;
SELECT 'Created ' || COUNT(*) || ' obstacle boundary connection edges' FROM obstacle_boundary_connection_edges;
SELECT 'Created ' || COUNT(*) || ' unified obstacle edges' FROM unified_obstacle_edges;
SELECT edge_type, COUNT(*) FROM unified_obstacle_edges GROUP BY edge_type ORDER BY edge_type;

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

-- Check graph connectivity
SELECT 
    COUNT(DISTINCT source_id) AS total_nodes,
    COUNT(DISTINCT target_id) AS total_targets,
    COUNT(*) AS total_edges
FROM 
    unified_obstacle_edges;
