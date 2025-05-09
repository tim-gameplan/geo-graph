/*
 * 04a_create_terrain_edges_hexagon.sql
 * 
 * Create terrain edges for the boundary hexagon layer approach
 * This script creates edges between terrain grid points (land and boundary hexagons)
 */

-- Drop existing tables if they exist
DROP TABLE IF EXISTS s04a_edges_terrain CASCADE;

-- Create terrain edges table
CREATE TABLE s04a_edges_terrain (
    id SERIAL PRIMARY KEY,
    start_node_id INTEGER,
    end_node_id INTEGER,
    geom GEOMETRY(LINESTRING, :storage_srid),
    length DOUBLE PRECISION,
    cost DOUBLE PRECISION
);

-- Create edges between terrain grid points
-- Connect each point to its neighbors within a certain distance
INSERT INTO s04a_edges_terrain (start_node_id, end_node_id, geom, length, cost)
SELECT 
    t1.id AS start_node_id,
    t2.id AS end_node_id,
    ST_MakeLine(t1.geom, t2.geom) AS geom,
    ST_Length(ST_MakeLine(t1.geom, t2.geom)) AS length,
    ST_Length(ST_MakeLine(t1.geom, t2.geom)) AS cost
FROM 
    s04_grid_terrain_points t1
JOIN 
    s04_grid_terrain_points t2 ON t1.id < t2.id
WHERE 
    -- Only connect land and boundary hexagons
    t1.hex_type IN ('land', 'boundary')
    AND t2.hex_type IN ('land', 'boundary')
    -- Only connect points that are within the maximum edge length
    AND ST_DWithin(t1.geom, t2.geom, :max_edge_length)
    -- Ensure the edge doesn't cross through water obstacles
    AND NOT EXISTS (
        SELECT 1
        FROM s03_water_obstacles wo
        WHERE ST_Intersects(ST_MakeLine(t1.geom, t2.geom), wo.geom)
            AND NOT ST_Intersects(ST_Buffer(t1.geom, 1), wo.geom)
            AND NOT ST_Intersects(ST_Buffer(t2.geom, 1), wo.geom)
    );

-- Create spatial index
CREATE INDEX s04a_edges_terrain_geom_idx ON s04a_edges_terrain USING GIST (geom);

-- Log the results
SELECT 'Created ' || COUNT(*) || ' terrain edges' FROM s04a_edges_terrain;
