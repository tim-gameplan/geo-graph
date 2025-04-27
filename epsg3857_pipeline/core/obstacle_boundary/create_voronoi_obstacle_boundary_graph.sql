-- Create Voronoi Obstacle Boundary Graph
-- This SQL script creates a graph representation of water obstacles using Voronoi diagrams
-- for connection assignment between terrain and water boundaries.

-- Step 1: Create boundary nodes along water obstacle boundaries
DROP TABLE IF EXISTS obstacle_boundary_nodes;
CREATE TABLE obstacle_boundary_nodes (
    node_id SERIAL PRIMARY KEY,
    water_obstacle_id INTEGER,
    point_order INTEGER,
    geom GEOMETRY(POINT, :storage_srid)
);

-- Extract points along the boundary of water obstacles at regular distance intervals
INSERT INTO obstacle_boundary_nodes (water_obstacle_id, point_order, geom)
SELECT 
    id AS water_obstacle_id,
    (ST_DumpPoints(ST_Segmentize(ST_ExteriorRing(geom), :boundary_node_spacing))).path[1] AS point_order,
    (ST_DumpPoints(ST_Segmentize(ST_ExteriorRing(geom), :boundary_node_spacing))).geom AS geom
FROM 
    water_obstacles;

-- Create spatial index on boundary nodes
CREATE INDEX IF NOT EXISTS obstacle_boundary_nodes_geom_idx ON obstacle_boundary_nodes USING GIST (geom);

-- Step 2: Create edges between adjacent boundary nodes
DROP TABLE IF EXISTS obstacle_boundary_edges;
CREATE TABLE obstacle_boundary_edges (
    edge_id SERIAL PRIMARY KEY,
    source_id INTEGER,
    target_id INTEGER,
    geom GEOMETRY(LINESTRING, :storage_srid),
    cost FLOAT
);

-- Create edges between adjacent boundary nodes
INSERT INTO obstacle_boundary_edges (source_id, target_id, geom, cost)
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
    node_id AS source_id,
    next_node_id AS target_id,
    ST_MakeLine(geom, next_geom) AS geom,
    ST_Length(ST_MakeLine(geom, next_geom)) AS cost
FROM 
    ordered_nodes
WHERE 
    next_node_id IS NOT NULL
UNION ALL
-- Connect last node back to first node to close the loop
SELECT 
    n1.node_id AS source_id,
    n2.node_id AS target_id,
    ST_MakeLine(n1.geom, n2.geom) AS geom,
    ST_Length(ST_MakeLine(n1.geom, n2.geom)) AS cost
FROM 
    ordered_nodes n1
JOIN 
    obstacle_boundary_nodes n2 
    ON n1.water_obstacle_id = n2.water_obstacle_id AND n2.point_order = 1
WHERE 
    n1.point_order = n1.max_order;

-- Create spatial index on boundary edges
CREATE INDEX IF NOT EXISTS obstacle_boundary_edges_geom_idx ON obstacle_boundary_edges USING GIST (geom);

-- Step 3: Create connections between terrain grid points and boundary nodes
DROP TABLE IF EXISTS obstacle_boundary_connection_edges;
CREATE TABLE obstacle_boundary_connection_edges (
    edge_id SERIAL PRIMARY KEY,
    source_id INTEGER,
    target_id INTEGER,
    geom GEOMETRY(LINESTRING, :storage_srid),
    cost FLOAT
);

-- Add diagnostic queries
SELECT 'Number of boundary nodes: ' || COUNT(*) FROM obstacle_boundary_nodes;

-- Create a more efficient approach for finding nearest boundary nodes
-- First, create a temporary table with boundary nodes and their buffers
DROP TABLE IF EXISTS temp_boundary_node_buffers;
CREATE TEMPORARY TABLE temp_boundary_node_buffers AS
SELECT 
    node_id,
    geom,
    ST_Buffer(geom, :voronoi_buffer_distance) AS buffer_geom
FROM 
    obstacle_boundary_nodes;

-- Create spatial index on the buffers
CREATE INDEX IF NOT EXISTS temp_boundary_node_buffers_geom_idx 
ON temp_boundary_node_buffers USING GIST (buffer_geom);

-- Create a temporary table to store the nearest boundary node for each terrain grid point
DROP TABLE IF EXISTS temp_nearest_boundary_nodes;
CREATE TEMPORARY TABLE temp_nearest_boundary_nodes AS
WITH candidate_nodes AS (
    -- Find boundary nodes whose buffer contains the terrain point
    -- This is much faster than calculating distances to all boundary nodes
    SELECT 
        tgp.id AS terrain_id,
        bnb.node_id AS boundary_node_id,
        ST_Distance(tgp.geom, bnb.geom) AS distance
    FROM 
        terrain_grid_points tgp
    JOIN 
        temp_boundary_node_buffers bnb
    ON 
        ST_DWithin(tgp.geom, bnb.geom, :voronoi_max_distance)
        AND ST_Intersects(tgp.geom, bnb.buffer_geom)
    WHERE 
        (tgp.hex_type = 'land' OR tgp.hex_type = 'boundary')
),
ranked_distances AS (
    SELECT 
        terrain_id,
        boundary_node_id,
        distance,
        ROW_NUMBER() OVER (
            PARTITION BY terrain_id 
            ORDER BY distance
        ) AS rank
    FROM 
        candidate_nodes
)
SELECT 
    terrain_id,
    boundary_node_id,
    distance
FROM 
    ranked_distances
WHERE 
    rank <= :voronoi_connection_limit;

-- Create connections between terrain grid points and boundary nodes
INSERT INTO obstacle_boundary_connection_edges (source_id, target_id, geom, cost)
SELECT 
    nbn.terrain_id AS source_id,
    nbn.boundary_node_id AS target_id,
    ST_MakeLine(
        (SELECT geom FROM terrain_grid_points WHERE id = nbn.terrain_id),
        (SELECT geom FROM obstacle_boundary_nodes WHERE node_id = nbn.boundary_node_id)
    ) AS geom,
    nbn.distance AS cost
FROM 
    temp_nearest_boundary_nodes nbn;

-- Create a virtual Voronoi-like assignment for testing purposes
DROP TABLE IF EXISTS voronoi_cells;
CREATE TABLE voronoi_cells (
    node_id INTEGER PRIMARY KEY,
    cell_geom GEOMETRY(POLYGON, :storage_srid)
);

-- For each boundary node, create a smaller buffer that represents its "cell"
INSERT INTO voronoi_cells (node_id, cell_geom)
SELECT 
    node_id,
    ST_Buffer(geom, :voronoi_buffer_distance) AS cell_geom
FROM 
    obstacle_boundary_nodes;

-- Clip the cells to exclude water areas and limit to max distance
UPDATE voronoi_cells
SET cell_geom = ST_Difference(
    ST_Intersection(
        cell_geom,
        ST_Buffer(
            (SELECT geom FROM obstacle_boundary_nodes WHERE node_id = voronoi_cells.node_id),
            :voronoi_max_distance
        )
    ),
    (SELECT ST_Union(geom) FROM water_obstacles)
);

-- Create spatial index on Voronoi cells
CREATE INDEX IF NOT EXISTS voronoi_cells_geom_idx ON voronoi_cells USING GIST (cell_geom);

-- Add diagnostic query
SELECT 'Number of Voronoi cells: ' || COUNT(*) FROM voronoi_cells;

-- Create spatial index on connection edges
CREATE INDEX IF NOT EXISTS obstacle_boundary_connection_edges_geom_idx ON obstacle_boundary_connection_edges USING GIST (geom);

-- Step 5: Create unified graph by combining terrain edges, boundary edges, and connection edges
DROP TABLE IF EXISTS unified_obstacle_edges;
CREATE TABLE unified_obstacle_edges (
    edge_id SERIAL PRIMARY KEY,
    source_id INTEGER,
    target_id INTEGER,
    geom GEOMETRY(LINESTRING, :storage_srid),
    cost FLOAT,
    reverse_cost FLOAT,
    edge_type VARCHAR(20)
);

-- Add terrain edges
INSERT INTO unified_obstacle_edges (source_id, target_id, geom, cost, reverse_cost, edge_type)
SELECT 
    source_id,
    target_id,
    geom,
    cost,
    cost AS reverse_cost,
    'terrain' AS edge_type
FROM 
    terrain_edges;

-- Add boundary edges
INSERT INTO unified_obstacle_edges (source_id, target_id, geom, cost, reverse_cost, edge_type)
SELECT 
    source_id,
    target_id,
    geom,
    cost,
    cost AS reverse_cost,
    'boundary' AS edge_type
FROM 
    obstacle_boundary_edges;

-- Add connection edges
INSERT INTO unified_obstacle_edges (source_id, target_id, geom, cost, reverse_cost, edge_type)
SELECT 
    source_id,
    target_id,
    geom,
    cost,
    cost AS reverse_cost,
    'connection' AS edge_type
FROM 
    obstacle_boundary_connection_edges;

-- Create spatial index on unified edges
CREATE INDEX IF NOT EXISTS unified_obstacle_edges_geom_idx ON unified_obstacle_edges USING GIST (geom);

-- Step 6: Create a unified nodes table for visualization and analysis
DROP TABLE IF EXISTS unified_obstacle_nodes;
CREATE TABLE unified_obstacle_nodes (
    node_id INTEGER PRIMARY KEY,
    geom GEOMETRY(POINT, :storage_srid),
    node_type VARCHAR(20)
);

-- Add terrain nodes
INSERT INTO unified_obstacle_nodes (node_id, geom, node_type)
SELECT 
    id AS node_id,
    geom,
    'terrain' AS node_type
FROM 
    terrain_grid_points
ON CONFLICT (node_id) DO NOTHING;

-- Add boundary nodes
INSERT INTO unified_obstacle_nodes (node_id, geom, node_type)
SELECT 
    node_id,
    geom,
    'boundary' AS node_type
FROM 
    obstacle_boundary_nodes
ON CONFLICT (node_id) DO NOTHING;

-- Create spatial index on unified nodes
CREATE INDEX IF NOT EXISTS unified_obstacle_nodes_geom_idx ON unified_obstacle_nodes USING GIST (geom);

-- Step 7: Verify graph connectivity
-- This query checks if the graph is fully connected
WITH RECURSIVE connected_nodes(node_id) AS (
    -- Start with the first node
    SELECT source_id FROM unified_obstacle_edges LIMIT 1
    UNION
    -- Add all nodes reachable from already connected nodes
    SELECT e.target_id
    FROM connected_nodes c
    JOIN unified_obstacle_edges e ON c.node_id = e.source_id
    WHERE e.target_id NOT IN (SELECT node_id FROM connected_nodes)
)
SELECT
    (SELECT COUNT(DISTINCT source_id) FROM unified_obstacle_edges) AS total_nodes,
    COUNT(*) AS connected_nodes,
    COUNT(*) * 100.0 / (SELECT COUNT(DISTINCT source_id) FROM unified_obstacle_edges) AS connectivity_percentage
FROM
    connected_nodes;
