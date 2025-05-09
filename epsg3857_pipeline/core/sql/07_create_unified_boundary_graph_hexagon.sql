/*
 * 07_create_unified_boundary_graph_hexagon.sql
 * 
 * Create unified boundary graph for the boundary hexagon layer approach
 * This script combines all nodes and edges into a unified graph, including:
 * 1. Terrain grid nodes and edges
 * 2. Boundary nodes and edges
 * 3. Water boundary nodes and edges
 * 4. Land portion nodes and edges
 */

-- Drop existing tables if they exist
DROP TABLE IF EXISTS s07_graph_unified_nodes CASCADE;
DROP TABLE IF EXISTS s07_graph_unified_edges CASCADE;
DROP TABLE IF EXISTS s07_graph_unified CASCADE;

-- Create unified boundary nodes table
CREATE TABLE s07_graph_unified_nodes (
    id SERIAL PRIMARY KEY,
    original_id INTEGER,
    node_type VARCHAR(20),
    geom GEOMETRY(POINT, :storage_srid)
);

-- Create unified boundary edges table
CREATE TABLE s07_graph_unified_edges (
    id SERIAL PRIMARY KEY,
    start_node_id INTEGER,
    end_node_id INTEGER,
    start_node_type VARCHAR(20),
    end_node_type VARCHAR(20),
    geom GEOMETRY(LINESTRING, :storage_srid),
    length DOUBLE PRECISION,
    cost DOUBLE PRECISION
);

-- Create unified boundary graph table
CREATE TABLE s07_graph_unified (
    id SERIAL PRIMARY KEY,
    element_type VARCHAR(10), -- 'node' or 'edge'
    element_id INTEGER,
    element_subtype VARCHAR(20), -- node_type or edge_type
    geom GEOMETRY(GEOMETRY, :storage_srid)
);

-- Check if required tables exist and have data
DO $$
DECLARE
    terrain_points_count INTEGER;
    boundary_nodes_count INTEGER;
    water_boundary_nodes_count INTEGER;
    land_portion_nodes_count INTEGER;
    terrain_edges_count INTEGER;
    boundary_edges_count INTEGER;
BEGIN
    -- Check if tables exist
    IF NOT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 's04_grid_terrain_points') THEN
        RAISE EXCEPTION 'Table s04_grid_terrain_points does not exist';
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 's05_nodes_boundary') THEN
        RAISE EXCEPTION 'Table s05_nodes_boundary does not exist';
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 's05_nodes_water_boundary') THEN
        RAISE EXCEPTION 'Table s05_nodes_water_boundary does not exist';
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 's05_nodes_land_portion') THEN
        RAISE EXCEPTION 'Table s05_nodes_land_portion does not exist';
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 's04a_edges_terrain') THEN
        RAISE EXCEPTION 'Table s04a_edges_terrain does not exist';
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 's06_edges_all_boundary') THEN
        RAISE EXCEPTION 'Table s06_edges_all_boundary does not exist';
    END IF;
    
    -- Check if tables have data
    SELECT COUNT(*) INTO terrain_points_count FROM s04_grid_terrain_points WHERE hex_type IN ('land', 'boundary');
    IF terrain_points_count = 0 THEN
        RAISE WARNING 'Table s04_grid_terrain_points has no land or boundary points';
    END IF;
    
    SELECT COUNT(*) INTO boundary_nodes_count FROM s05_nodes_boundary;
    IF boundary_nodes_count = 0 THEN
        RAISE WARNING 'Table s05_nodes_boundary is empty';
    END IF;
    
    SELECT COUNT(*) INTO water_boundary_nodes_count FROM s05_nodes_water_boundary;
    IF water_boundary_nodes_count = 0 THEN
        RAISE WARNING 'Table s05_nodes_water_boundary is empty';
    END IF;
    
    SELECT COUNT(*) INTO land_portion_nodes_count FROM s05_nodes_land_portion;
    IF land_portion_nodes_count = 0 THEN
        RAISE WARNING 'Table s05_nodes_land_portion is empty';
    END IF;
    
    SELECT COUNT(*) INTO terrain_edges_count FROM s04a_edges_terrain;
    IF terrain_edges_count = 0 THEN
        RAISE WARNING 'Table s04a_edges_terrain is empty';
    END IF;
    
    SELECT COUNT(*) INTO boundary_edges_count FROM s06_edges_all_boundary;
    IF boundary_edges_count = 0 THEN
        RAISE WARNING 'Table s06_edges_all_boundary is empty';
    END IF;
    
    -- Log the counts
    RAISE NOTICE 'Table counts: terrain_points=%, boundary_nodes=%, water_boundary_nodes=%, land_portion_nodes=%, terrain_edges=%, boundary_edges=%',
        terrain_points_count, boundary_nodes_count, water_boundary_nodes_count, land_portion_nodes_count, terrain_edges_count, boundary_edges_count;
END $$;

-- Insert all nodes into unified_boundary_nodes
INSERT INTO s07_graph_unified_nodes (original_id, node_type, geom)
-- Terrain grid points (land and boundary hexagons)
SELECT
    id AS original_id,
    hex_type AS node_type,
    geom
FROM
    s04_grid_terrain_points
WHERE
    hex_type IN ('land', 'boundary')
UNION ALL
-- Boundary nodes
SELECT
    id AS original_id,
    node_type,
    geom
FROM
    s05_nodes_boundary
UNION ALL
-- Water boundary nodes
SELECT
    id AS original_id,
    node_type,
    geom
FROM
    s05_nodes_water_boundary
UNION ALL
-- Land portion nodes
SELECT
    id AS original_id,
    node_type,
    geom
FROM
    s05_nodes_land_portion;

-- Insert all edges into unified_boundary_edges
-- Terrain edges
INSERT INTO s07_graph_unified_edges (start_node_id, end_node_id, start_node_type, end_node_type, geom, length, cost)
SELECT 
    start_node_id,
    end_node_id,
    'terrain' AS start_node_type,
    'terrain' AS end_node_type,
    geom,
    length,
    cost
FROM 
    s04a_edges_terrain
UNION ALL
-- Boundary edges
SELECT 
    start_node_id,
    end_node_id,
    start_node_type,
    end_node_type,
    geom,
    length,
    cost
FROM 
    s06_edges_all_boundary;

-- Insert all nodes and edges into unified_boundary_graph
-- Nodes
INSERT INTO s07_graph_unified (element_type, element_id, element_subtype, geom)
SELECT 
    'node' AS element_type,
    id AS element_id,
    node_type AS element_subtype,
    geom
FROM 
    s07_graph_unified_nodes;

-- Edges
INSERT INTO s07_graph_unified (element_type, element_id, element_subtype, geom)
SELECT 
    'edge' AS element_type,
    id AS element_id,
    start_node_type || '-' || end_node_type AS element_subtype,
    geom
FROM 
    s07_graph_unified_edges;

-- Create spatial indexes
CREATE INDEX s07_graph_unified_nodes_geom_idx ON s07_graph_unified_nodes USING GIST (geom);
CREATE INDEX s07_graph_unified_edges_geom_idx ON s07_graph_unified_edges USING GIST (geom);
CREATE INDEX s07_graph_unified_geom_idx ON s07_graph_unified USING GIST (geom);

-- Log the results
SELECT 'Created ' || COUNT(*) || ' unified boundary nodes' FROM s07_graph_unified_nodes;
SELECT 'Created ' || COUNT(*) || ' unified boundary edges' FROM s07_graph_unified_edges;
SELECT 'Created ' || COUNT(*) || ' unified boundary graph elements' FROM s07_graph_unified;
SELECT 'Node types: ' || string_agg(DISTINCT node_type, ', ') FROM s07_graph_unified_nodes;
SELECT 'Edge types: ' || string_agg(DISTINCT element_subtype, ', ') FROM s07_graph_unified WHERE element_type = 'edge';
SELECT 'Terrain nodes: ' || COUNT(*) FROM s07_graph_unified_nodes WHERE node_type IN ('land', 'boundary');
SELECT 'Terrain edges: ' || COUNT(*) FROM s07_graph_unified_edges WHERE start_node_type = 'terrain' AND end_node_type = 'terrain';
SELECT 'Boundary connection edges: ' || COUNT(*) FROM s07_graph_unified_edges WHERE start_node_type != 'terrain' OR end_node_type != 'terrain';
