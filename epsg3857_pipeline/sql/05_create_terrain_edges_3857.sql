/*
 * Terrain Edges Creation
 * 
 * This script creates edges between terrain grid points.
 * It uses the centroids of the hexagonal grid cells as nodes.
 */

-- Create terrain edges with EPSG:3857 coordinates
-- Parameters:
-- :storage_srid - SRID for storage (default: 3857)
-- :max_edge_length - Maximum edge length in meters (default: 500)

-- Create terrain edges table
DROP TABLE IF EXISTS terrain_edges CASCADE;
CREATE TABLE terrain_edges (
    id SERIAL PRIMARY KEY,
    source_id INTEGER REFERENCES terrain_grid_points(id),
    target_id INTEGER REFERENCES terrain_grid_points(id),
    length NUMERIC,
    cost NUMERIC, -- Travel time cost
    geom GEOMETRY(LINESTRING, :storage_srid)
);

-- Create edges between adjacent grid points
INSERT INTO terrain_edges (source_id, target_id, length, cost, geom)
SELECT 
    t1.id AS source_id,
    t2.id AS target_id,
    ST_Length(ST_MakeLine(t1.geom, t2.geom)) AS length,
    ST_Length(ST_MakeLine(t1.geom, t2.geom)) / 5.0 AS cost, -- Assuming 5 m/s average speed
    ST_MakeLine(t1.geom, t2.geom) AS geom
FROM 
    terrain_grid_points t1
CROSS JOIN 
    terrain_grid_points t2
WHERE 
    t1.id < t2.id AND
    ST_DWithin(t1.geom, t2.geom, :max_edge_length) AND
    -- Exclude edges that intersect with water obstacles
    NOT EXISTS (
        SELECT 1
        FROM water_obstacles
        WHERE ST_Intersects(water_obstacles.geom, ST_MakeLine(t1.geom, t2.geom))
    );

-- Create spatial index
CREATE INDEX terrain_edges_geom_idx ON terrain_edges USING GIST (geom);
CREATE INDEX terrain_edges_source_id_idx ON terrain_edges (source_id);
CREATE INDEX terrain_edges_target_id_idx ON terrain_edges (target_id);

-- Log the results
SELECT 'Created ' || COUNT(*) || ' terrain edges' FROM terrain_edges;
