-- Dissolve water buffers with EPSG:3857 coordinates
-- Parameters:
-- :storage_srid - SRID for storage (default: 3857)
-- :simplify_tolerance - Simplification tolerance in meters (default: 5)

-- Set work_mem to a higher value for better performance
SET work_mem = '256MB';

-- Create dissolved water buffers table
DROP TABLE IF EXISTS dissolved_water_buffers CASCADE;
CREATE TABLE dissolved_water_buffers (
    id SERIAL PRIMARY KEY,
    geom GEOMETRY(GEOMETRY, :storage_srid)
);

-- Dissolve overlapping water buffers
INSERT INTO dissolved_water_buffers (geom)
SELECT 
    ST_Simplify(
        ST_Union(geom),
        :simplify_tolerance
    ) AS geom
FROM 
    water_buffers;

-- Create spatial index
CREATE INDEX dissolved_water_buffers_geom_idx ON dissolved_water_buffers USING GIST (geom);

-- Log the results
SELECT 'Created ' || COUNT(*) || ' dissolved water buffers' FROM dissolved_water_buffers;

-- Create a table for water obstacles
DROP TABLE IF EXISTS water_obstacles CASCADE;
CREATE TABLE water_obstacles (
    id SERIAL PRIMARY KEY,
    geom GEOMETRY(GEOMETRY, :storage_srid)
);

-- Extract individual polygons from the dissolved water buffers
INSERT INTO water_obstacles (geom)
SELECT 
    (ST_Dump(geom)).geom AS geom
FROM 
    dissolved_water_buffers;

-- Create spatial index
CREATE INDEX water_obstacles_geom_idx ON water_obstacles USING GIST (geom);

-- Log the results
SELECT 'Created ' || COUNT(*) || ' water obstacles' FROM water_obstacles;

-- Reset work_mem to default value
RESET work_mem;
