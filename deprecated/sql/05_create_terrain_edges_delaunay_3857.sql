-- Create terrain edges with Delaunay triangulation using EPSG:3857 coordinates
-- Parameters:
-- :storage_srid - SRID for storage (default: 3857)
-- :connection_dist - Maximum connection distance in meters (default: 500)

-- Create terrain edges table
DROP TABLE IF EXISTS terrain_edges CASCADE;
CREATE TABLE terrain_edges (
    id SERIAL PRIMARY KEY,
    source_id INTEGER,
    target_id INTEGER,
    length NUMERIC,
    geom GEOMETRY(LINESTRING, :storage_srid)
);

-- Create a temporary table to store vertex information
DROP TABLE IF EXISTS delaunay_vertices CASCADE;
CREATE TEMPORARY TABLE delaunay_vertices (
    id SERIAL PRIMARY KEY,
    geom GEOMETRY(POINT, :storage_srid)
);

-- Extract unique vertices from Delaunay edges
INSERT INTO delaunay_vertices (geom)
SELECT DISTINCT start_point AS geom
FROM delaunay_edges
UNION
SELECT DISTINCT end_point AS geom
FROM delaunay_edges;

-- Create spatial index
CREATE INDEX delaunay_vertices_geom_idx ON delaunay_vertices USING GIST (geom);

-- Insert Delaunay edges into terrain edges
INSERT INTO terrain_edges (source_id, target_id, length, geom)
SELECT 
    v1.id AS source_id,
    v2.id AS target_id,
    ST_Length(de.geom) AS length,
    de.geom
FROM 
    delaunay_edges de
JOIN 
    delaunay_vertices v1 ON ST_DWithin(de.start_point, v1.geom, 1)
JOIN 
    delaunay_vertices v2 ON ST_DWithin(de.end_point, v2.geom, 1)
WHERE 
    -- Exclude edges that are too long
    ST_Length(de.geom) <= :connection_dist AND
    -- Exclude edges that intersect with water obstacles
    NOT EXISTS (
        SELECT 1
        FROM water_obstacles
        WHERE ST_Intersects(water_obstacles.geom, de.geom)
    );

-- Create spatial index
CREATE INDEX terrain_edges_geom_idx ON terrain_edges USING GIST (geom);
CREATE INDEX terrain_edges_source_id_idx ON terrain_edges (source_id);
CREATE INDEX terrain_edges_target_id_idx ON terrain_edges (target_id);

-- Log the results
SELECT 'Created ' || COUNT(*) || ' terrain edges from Delaunay triangulation' FROM terrain_edges;

-- Create a table for terrain vertices
DROP TABLE IF EXISTS terrain_vertices CASCADE;
CREATE TABLE terrain_vertices (
    id SERIAL PRIMARY KEY,
    geom GEOMETRY(POINT, :storage_srid)
);

-- Insert vertices from delaunay_vertices
INSERT INTO terrain_vertices (geom)
SELECT geom
FROM delaunay_vertices;

-- Create spatial index
CREATE INDEX terrain_vertices_geom_idx ON terrain_vertices USING GIST (geom);

-- Log the results
SELECT 'Created ' || COUNT(*) || ' terrain vertices' FROM terrain_vertices;

-- Update terrain edges to reference terrain vertices
UPDATE terrain_edges
SET 
    source_id = v1.id,
    target_id = v2.id
FROM 
    terrain_vertices v1,
    terrain_vertices v2,
    delaunay_vertices dv1,
    delaunay_vertices dv2
WHERE 
    terrain_edges.source_id = dv1.id AND
    terrain_edges.target_id = dv2.id AND
    ST_DWithin(v1.geom, dv1.geom, 1) AND
    ST_DWithin(v2.geom, dv2.geom, 1);

-- Add foreign key constraints
ALTER TABLE terrain_edges
ADD CONSTRAINT terrain_edges_source_id_fkey
FOREIGN KEY (source_id) REFERENCES terrain_vertices(id);

ALTER TABLE terrain_edges
ADD CONSTRAINT terrain_edges_target_id_fkey
FOREIGN KEY (target_id) REFERENCES terrain_vertices(id);

-- Log the results
SELECT 'Updated ' || COUNT(*) || ' terrain edges with vertex references' FROM terrain_edges;
