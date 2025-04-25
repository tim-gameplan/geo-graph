-- 07_create_unified_boundary_graph_3857.sql
-- Create unified graph and verify connectivity for the boundary hexagon layer approach

-- Drop existing tables if they exist
DROP TABLE IF EXISTS unified_boundary_edges CASCADE;
DROP TABLE IF EXISTS unified_boundary_nodes CASCADE;

-- Create a unified nodes table
CREATE TABLE unified_boundary_nodes AS
-- Land nodes (terrain grid points with hex_type = 'land')
SELECT
    id AS node_id,
    'land' AS node_type,
    geom
FROM
    terrain_grid_points
WHERE
    hex_type = 'land'
UNION ALL
-- Boundary nodes
SELECT
    node_id,
    node_type,
    geom
FROM
    boundary_nodes
UNION ALL
-- Water boundary nodes
SELECT
    node_id,
    node_type,
    geom
FROM
    water_boundary_nodes;

-- Create a unified edges table
CREATE TABLE unified_boundary_edges AS
-- Land-to-land edges
SELECT
    source_id,
    target_id,
    length,
    cost,
    edge_type,
    1.0 AS speed_factor,
    FALSE AS is_water,
    geom
FROM
    land_land_edges
UNION ALL
-- Land-to-boundary edges
SELECT
    source_id,
    target_id,
    length,
    cost,
    edge_type,
    1.0 AS speed_factor,
    FALSE AS is_water,
    geom
FROM
    land_boundary_edges
UNION ALL
-- Boundary-to-boundary edges
SELECT
    source_id,
    target_id,
    length,
    cost,
    edge_type,
    1.0 AS speed_factor,
    FALSE AS is_water,
    geom
FROM
    boundary_boundary_edges
UNION ALL
-- Boundary-to-water edges
SELECT
    source_id,
    target_id,
    length,
    cost,
    edge_type,
    :water_speed_factor AS speed_factor,
    TRUE AS is_water,
    geom
FROM
    boundary_water_edges
UNION ALL
-- Water boundary edges
SELECT
    source_id,
    target_id,
    length,
    cost,
    edge_type,
    :water_speed_factor AS speed_factor,
    TRUE AS is_water,
    geom
FROM
    water_boundary_edges;

-- Create spatial indexes
CREATE INDEX unified_boundary_nodes_geom_idx ON unified_boundary_nodes USING GIST (geom);
CREATE INDEX unified_boundary_edges_geom_idx ON unified_boundary_edges USING GIST (geom);

-- Check graph connectivity
WITH RECURSIVE
connected_nodes(node_id) AS (
    -- Start with the first node
    SELECT node_id FROM unified_boundary_nodes LIMIT 1
    UNION
    -- Add all nodes reachable from already connected nodes
    SELECT e.target_id
    FROM connected_nodes c
    JOIN unified_boundary_edges e ON c.node_id = e.source_id
    WHERE e.target_id NOT IN (SELECT node_id FROM connected_nodes)
    UNION
    -- Also add nodes in the reverse direction
    SELECT e.source_id
    FROM connected_nodes c
    JOIN unified_boundary_edges e ON c.node_id = e.target_id
    WHERE e.source_id NOT IN (SELECT node_id FROM connected_nodes)
)
SELECT 
    (SELECT COUNT(*) FROM unified_boundary_nodes) AS total_nodes,
    COUNT(*) AS connected_nodes,
    COUNT(*) * 100.0 / (SELECT COUNT(*) FROM unified_boundary_nodes) AS connectivity_percentage
FROM 
    connected_nodes;

-- Add connectivity edges if needed
DO $$
DECLARE
    connectivity_percentage NUMERIC;
BEGIN
    -- Get the connectivity percentage
    SELECT 
        COUNT(*) * 100.0 / (SELECT COUNT(*) FROM unified_boundary_nodes) INTO connectivity_percentage
    FROM (
        WITH RECURSIVE
        connected_nodes(node_id) AS (
            -- Start with the first node
            SELECT node_id FROM unified_boundary_nodes LIMIT 1
            UNION
            -- Add all nodes reachable from already connected nodes
            SELECT e.target_id
            FROM connected_nodes c
            JOIN unified_boundary_edges e ON c.node_id = e.source_id
            WHERE e.target_id NOT IN (SELECT node_id FROM connected_nodes)
            UNION
            -- Also add nodes in the reverse direction
            SELECT e.source_id
            FROM connected_nodes c
            JOIN unified_boundary_edges e ON c.node_id = e.target_id
            WHERE e.source_id NOT IN (SELECT node_id FROM connected_nodes)
        )
        SELECT node_id FROM connected_nodes
    ) AS connected;
    
    -- If connectivity is less than 100%, add connectivity edges
    IF connectivity_percentage < 100 THEN
        RAISE NOTICE 'Adding connectivity edges to ensure full graph connectivity...';
        
        -- Find disconnected components
        WITH RECURSIVE
        connected_nodes(node_id) AS (
            -- Start with the first node
            SELECT node_id FROM unified_boundary_nodes LIMIT 1
            UNION
            -- Add all nodes reachable from already connected nodes
            SELECT e.target_id
            FROM connected_nodes c
            JOIN unified_boundary_edges e ON c.node_id = e.source_id
            WHERE e.target_id NOT IN (SELECT node_id FROM connected_nodes)
            UNION
            -- Also add nodes in the reverse direction
            SELECT e.source_id
            FROM connected_nodes c
            JOIN unified_boundary_edges e ON c.node_id = e.target_id
            WHERE e.source_id NOT IN (SELECT node_id FROM connected_nodes)
        ),
        disconnected_nodes AS (
            SELECT node_id FROM unified_boundary_nodes
            EXCEPT
            SELECT node_id FROM connected_nodes
        ),
        closest_connections AS (
            SELECT 
                c.node_id AS connected_node_id,
                d.node_id AS disconnected_node_id,
                ST_Distance(c.geom, d.geom) AS distance,
                ROW_NUMBER() OVER (PARTITION BY d.node_id ORDER BY ST_Distance(c.geom, d.geom)) AS rank
            FROM 
                (SELECT node_id, geom FROM unified_boundary_nodes WHERE node_id IN (SELECT node_id FROM connected_nodes)) c
            CROSS JOIN 
                (SELECT node_id, geom FROM unified_boundary_nodes WHERE node_id IN (SELECT node_id FROM disconnected_nodes)) d
        )
        INSERT INTO unified_boundary_edges (source_id, target_id, length, cost, edge_type, speed_factor, is_water, geom)
        SELECT 
            connected_node_id AS source_id,
            disconnected_node_id AS target_id,
            ST_Length(ST_MakeLine(c.geom, d.geom)) AS length,
            ST_Length(ST_MakeLine(c.geom, d.geom)) / (5.0 * :water_speed_factor) AS cost,
            'connectivity' AS edge_type,
            :water_speed_factor AS speed_factor,
            TRUE AS is_water,
            ST_MakeLine(c.geom, d.geom) AS geom
        FROM 
            closest_connections cc
        JOIN 
            unified_boundary_nodes c ON cc.connected_node_id = c.node_id
        JOIN 
            unified_boundary_nodes d ON cc.disconnected_node_id = d.node_id
        WHERE 
            cc.rank = 1;
        
        -- Check connectivity again
        WITH RECURSIVE
        connected_nodes(node_id) AS (
            -- Start with the first node
            SELECT node_id FROM unified_boundary_nodes LIMIT 1
            UNION
            -- Add all nodes reachable from already connected nodes
            SELECT e.target_id
            FROM connected_nodes c
            JOIN unified_boundary_edges e ON c.node_id = e.source_id
            WHERE e.target_id NOT IN (SELECT node_id FROM connected_nodes)
            UNION
            -- Also add nodes in the reverse direction
            SELECT e.source_id
            FROM connected_nodes c
            JOIN unified_boundary_edges e ON c.node_id = e.target_id
            WHERE e.source_id NOT IN (SELECT node_id FROM connected_nodes)
        )
        SELECT 
            (SELECT COUNT(*) FROM unified_boundary_nodes) AS total_nodes,
            COUNT(*) AS connected_nodes,
            COUNT(*) * 100.0 / (SELECT COUNT(*) FROM unified_boundary_nodes) AS connectivity_percentage
        INTO connectivity_percentage
        FROM 
            connected_nodes;
        
        RAISE NOTICE 'Connectivity after adding edges: %', connectivity_percentage;
    END IF;
END $$;

-- Log the results
SELECT 'Created ' || COUNT(*) || ' unified boundary nodes' FROM unified_boundary_nodes;
SELECT 'Created ' || COUNT(*) || ' unified boundary edges' FROM unified_boundary_edges;
SELECT 'Land nodes: ' || COUNT(*) FROM unified_boundary_nodes WHERE node_type = 'land';
SELECT 'Boundary nodes: ' || COUNT(*) FROM unified_boundary_nodes WHERE node_type = 'boundary';
SELECT 'Water boundary nodes: ' || COUNT(*) FROM unified_boundary_nodes WHERE node_type = 'water_boundary';
SELECT 'Land-land edges: ' || COUNT(*) FROM unified_boundary_edges WHERE edge_type = 'land_land';
SELECT 'Land-boundary edges: ' || COUNT(*) FROM unified_boundary_edges WHERE edge_type = 'land_boundary';
SELECT 'Boundary-boundary edges: ' || COUNT(*) FROM unified_boundary_edges WHERE edge_type = 'boundary_boundary';
SELECT 'Boundary-water edges: ' || COUNT(*) FROM unified_boundary_edges WHERE edge_type = 'boundary_water';
SELECT 'Water-boundary edges: ' || COUNT(*) FROM unified_boundary_edges WHERE edge_type = 'water_boundary';
SELECT 'Connectivity edges: ' || COUNT(*) FROM unified_boundary_edges WHERE edge_type = 'connectivity';
