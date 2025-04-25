/*
 * Water Buffers Creation
 * 
 * This script creates buffers around water features using the typed tables approach.
 * It directly uses water_features_polygon and water_features_line tables for better performance.
 */

-- Create water buffers with EPSG:3857 coordinates
-- Parameters:
-- :storage_srid - SRID for storage (default: 3857)
-- :default_buffer - Default buffer size in meters (default: 50)
-- :lake_buffer - Lake buffer size in meters (default: 100)
-- :river_buffer - River buffer size in meters (default: 75)
-- :stream_buffer - Stream buffer size in meters (default: 30)

-- Create water buffers table
DROP TABLE IF EXISTS water_buffers CASCADE;
CREATE TABLE water_buffers (
    id SERIAL PRIMARY KEY,
    water_feature_id INTEGER,
    feature_type TEXT, -- 'polygon' or 'line'
    buffer_size NUMERIC,
    geom GEOMETRY(GEOMETRY, :storage_srid)
);

-- Create buffers for water polygons
INSERT INTO water_buffers (water_feature_id, feature_type, buffer_size, geom)
SELECT 
    id,
    'polygon',
    CASE
        WHEN type = 'water' THEN :lake_buffer
        ELSE :default_buffer
    END AS buffer_size,
    ST_Buffer(
        geom,
        CASE
            WHEN type = 'water' THEN :lake_buffer
            ELSE :default_buffer
        END
    ) AS geom
FROM 
    water_features_polygon;

-- Create buffers for water lines
INSERT INTO water_buffers (water_feature_id, feature_type, buffer_size, geom)
SELECT 
    id,
    'line',
    CASE
        WHEN type = 'river' THEN :river_buffer
        WHEN type = 'stream' THEN :stream_buffer
        ELSE :default_buffer
    END AS buffer_size,
    ST_Buffer(
        geom,
        CASE
            WHEN type = 'river' THEN :river_buffer
            WHEN type = 'stream' THEN :stream_buffer
            ELSE :default_buffer
        END
    ) AS geom
FROM 
    water_features_line;

-- Create spatial index
CREATE INDEX water_buffers_geom_idx ON water_buffers USING GIST (geom);

-- Log the results
SELECT 'Created ' || COUNT(*) || ' water buffers' FROM water_buffers;
