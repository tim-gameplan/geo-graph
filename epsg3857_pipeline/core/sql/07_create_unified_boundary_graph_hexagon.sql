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
DROP TABLE IF EXISTS unified_boundary_nodes CASCADE;
DROP TABLE IF EXISTS unified_boundary_edges CASCADE;
DROP TABLE IF EXISTS unified_boundary_graph CASCADE;

-- Create unified boundary nodes table
CREATE TABLE unified_boundary_nodes (
    id SERIAL PRIMARY KEY,
    original_id INTEGER,
    node_type VARCHAR(20),
    geom GEOMETRY(POINT, :storage_srid)
);

-- Create unified boundary edges table
CREATE TABLE unified_boundary_edges (
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
CREATE TABLE unified_boundary_graph (
    id SERIAL PRIMARY KEY,
    element_type VARCHAR(10), -- 'node' or 'edge'
    element_id INTEGER,
    element_subtype VARCHAR(20), -- node_type or edge_type
    geom GEOMETRY(GEOMETRY, :storage_srid)
);

-- Insert all nodes into unified_boundary_nodes
INSERT INTO unified_boundary_nodes (original_id, node_type, geom)
-- Terrain grid points (land and boundary hexagons)
SELECT 
    id AS original_id,
    hex_type AS node_type,
    geom
FROM 
    terrain_grid_points
WHERE 
    hex_type IN ('land', 'boundary')
UNION ALL
-- Boundary nodes
SELECT 
    id AS original_id,
    node_type,
    geom
FROM 
    boundary_nodes
UNION ALL
-- Water boundary nodes
SELECT 
    id AS original_id,
    node_type,
    geom
FROM 
    water_boundary_nodes
UNION ALL
-- Land portion nodes
SELECT 
    id AS original_id,
    node_type,
    geom
FROM 
    land_portion_nodes;

-- Insert all edges into unified_boundary_edges
-- Terrain edges
INSERT INTO unified_boundary_edges (start_node_id, end_node_id, start_node_type, end_node_type, geom, length, cost)
SELECT 
    start_node_id,
    end_node_id,
    'terrain' AS start_node_type,
    'terrain' AS end_node_type,
    geom,
    length,
    cost
FROM 
    terrain_edges
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
    all_boundary_edges;

-- Insert all nodes and edges into unified_boundary_graph
-- Nodes
INSERT INTO unified_boundary_graph (element_type, element_id, element_subtype, geom)
SELECT 
    'node' AS element_type,
    id AS element_id,
    node_type AS element_subtype,
    geom
FROM 
    unified_boundary_nodes;

-- Edges
INSERT INTO unified_boundary_graph (element_type, element_id, element_subtype, geom)
SELECT 
    'edge' AS element_type,
    id AS element_id,
    start_node_type || '-' || end_node_type AS element_subtype,
    geom
FROM 
    unified_boundary_edges;

-- Create spatial indexes
CREATE INDEX unified_boundary_nodes_geom_idx ON unified_boundary_nodes USING GIST (geom);
CREATE INDEX unified_boundary_edges_geom_idx ON unified_boundary_edges USING GIST (geom);
CREATE INDEX unified_boundary_graph_geom_idx ON unified_boundary_graph USING GIST (geom);

-- Log the results
SELECT 'Created ' || COUNT(*) || ' unified boundary nodes' FROM unified_boundary_nodes;
SELECT 'Created ' || COUNT(*) || ' unified boundary edges' FROM unified_boundary_edges;
SELECT 'Created ' || COUNT(*) || ' unified boundary graph elements' FROM unified_boundary_graph;
SELECT 'Node types: ' || string_agg(DISTINCT node_type, ', ') FROM unified_boundary_nodes;
SELECT 'Edge types: ' || string_agg(DISTINCT element_subtype, ', ') FROM unified_boundary_graph WHERE element_type = 'edge';
SELECT 'Terrain nodes: ' || COUNT(*) FROM unified_boundary_nodes WHERE node_type IN ('land', 'boundary');
SELECT 'Terrain edges: ' || COUNT(*) FROM unified_boundary_edges WHERE start_node_type = 'terrain' AND end_node_type = 'terrain';
SELECT 'Boundary connection edges: ' || COUNT(*) FROM unified_boundary_edges WHERE start_node_type != 'terrain' OR end_node_type != 'terrain';
