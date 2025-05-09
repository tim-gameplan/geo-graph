-- Dissolve water buffers with EPSG:3857 coordinates
-- Parameters:
-- :storage_srid - SRID for storage (default: 3857)
-- :simplify_tolerance - Simplification tolerance in meters (default: 5)

-- Set work_mem to a higher value for better performance
SET work_mem = '256MB';

-- Create dissolved water buffers table
DROP TABLE IF EXISTS s03_water_buffers_dissolved CASCADE;
CREATE TABLE s03_water_buffers_dissolved (
    id SERIAL PRIMARY KEY,
    geom GEOMETRY(GEOMETRY, :storage_srid)
);

-- Dissolve overlapping water buffers
INSERT INTO s03_water_buffers_dissolved (geom)
SELECT 
    ST_Simplify(
        ST_Union(geom),
        :simplify_tolerance
    ) AS geom
FROM 
    s02_water_buffers;

-- Create spatial index
CREATE INDEX s03_water_buffers_dissolved_geom_idx ON s03_water_buffers_dissolved USING GIST (geom);

-- Log the results
SELECT 'Created ' || COUNT(*) || ' dissolved water buffers' FROM s03_water_buffers_dissolved;

-- Create a table for water obstacles
DROP TABLE IF EXISTS s03_water_obstacles CASCADE;
CREATE TABLE s03_water_obstacles (
    id SERIAL PRIMARY KEY,
    geom GEOMETRY(GEOMETRY, :storage_srid)
);

-- Extract individual polygons from the dissolved water buffers
INSERT INTO s03_water_obstacles (geom)
SELECT 
    (ST_Dump(geom)).geom AS geom
FROM 
    s03_water_buffers_dissolved;

-- Create spatial index
CREATE INDEX s03_water_obstacles_geom_idx ON s03_water_obstacles USING GIST (geom);

-- Log the results
SELECT 'Created ' || COUNT(*) || ' water obstacles' FROM s03_water_obstacles;

-- Reset work_mem to default value
RESET work_mem;
