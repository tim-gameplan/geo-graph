/*
 * Terrain Edges Creation (Including Water Areas)
 * 
 * This script creates edges between terrain grid points, including those in water areas.
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
    is_water_crossing BOOLEAN, -- Flag to indicate if the edge crosses water
    geom GEOMETRY(LINESTRING, :storage_srid)
);

-- Create edges between adjacent grid points
INSERT INTO terrain_edges (source_id, target_id, length, cost, is_water_crossing, geom)
SELECT 
    t1.id AS source_id,
    t2.id AS target_id,
    ST_Length(ST_MakeLine(t1.geom, t2.geom)) AS length,
    CASE
        -- Higher cost for edges that cross water or connect to water points
        WHEN EXISTS (
            SELECT 1
            FROM water_obstacles
            WHERE ST_Intersects(water_obstacles.geom, ST_MakeLine(t1.geom, t2.geom))
        ) OR t1.is_water OR t2.is_water THEN ST_Length(ST_MakeLine(t1.geom, t2.geom)) / 1.0 -- Slower speed in water (1 m/s)
        ELSE ST_Length(ST_MakeLine(t1.geom, t2.geom)) / 5.0 -- Normal speed on land (5 m/s)
    END AS cost,
    EXISTS (
        SELECT 1
        FROM water_obstacles
        WHERE ST_Intersects(water_obstacles.geom, ST_MakeLine(t1.geom, t2.geom))
    ) OR t1.is_water OR t2.is_water AS is_water_crossing,
    ST_MakeLine(t1.geom, t2.geom) AS geom
FROM 
    terrain_grid_points t1
CROSS JOIN 
    terrain_grid_points t2
WHERE 
    t1.id < t2.id AND
    ST_DWithin(t1.geom, t2.geom, :max_edge_length);

-- Create spatial index
CREATE INDEX terrain_edges_geom_idx ON terrain_edges USING GIST (geom);
CREATE INDEX terrain_edges_source_id_idx ON terrain_edges (source_id);
CREATE INDEX terrain_edges_target_id_idx ON terrain_edges (target_id);
CREATE INDEX terrain_edges_is_water_crossing_idx ON terrain_edges (is_water_crossing);

-- Log the results
SELECT 'Created ' || COUNT(*) || ' terrain edges' FROM terrain_edges;
SELECT 'Created ' || COUNT(*) || ' water crossing edges' FROM terrain_edges WHERE is_water_crossing;
SELECT 'Created ' || COUNT(*) || ' land-only edges' FROM terrain_edges WHERE NOT is_water_crossing;
