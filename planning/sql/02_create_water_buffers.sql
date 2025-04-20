-- 02_create_water_buffers.sql
-- Create intelligent water buffers based on water type and attributes
-- Parameters:
-- :buffer_default - Default buffer size in meters
-- :buffer_river - Buffer size for rivers
-- :buffer_stream - Buffer size for streams
-- :buffer_canal - Buffer size for canals
-- :buffer_drain - Buffer size for drains
-- :buffer_ditch - Buffer size for ditches
-- :buffer_lake - Buffer size for lakes
-- :buffer_pond - Buffer size for ponds
-- :buffer_reservoir - Buffer size for reservoirs
-- :cross_default - Default crossability score
-- :cross_river - Crossability score for rivers
-- :cross_stream - Crossability score for streams
-- :cross_canal - Crossability score for canals
-- :cross_drain - Crossability score for drains
-- :cross_ditch - Crossability score for ditches
-- :cross_lake - Crossability score for lakes
-- :cross_pond - Crossability score for ponds
-- :cross_reservoir - Crossability score for reservoirs
-- :cross_intermittent_multiplier - Multiplier for intermittent water features

-- Create water_buf table
DROP TABLE IF EXISTS water_buf;
CREATE TABLE water_buf AS
SELECT
    id,
    feature_type,
    water_type,
    name,
    width,
    intermittent,
    -- Add buffer size tracking
    CASE
        -- For polygons
        WHEN feature_type = 'polygon' THEN
            CASE
                WHEN water_type = 'water' AND name ILIKE '%lake%' THEN :buffer_lake
                WHEN water_type = 'water' AND name ILIKE '%pond%' THEN :buffer_pond
                WHEN water_type = 'reservoir' THEN :buffer_reservoir
                ELSE :buffer_default
            END
        -- For lines
        WHEN feature_type = 'line' THEN
            CASE
                WHEN width IS NOT NULL THEN width::numeric + 10
                WHEN water_type = 'river' THEN :buffer_river
                WHEN water_type = 'stream' THEN :buffer_stream
                WHEN water_type = 'canal' THEN :buffer_canal
                WHEN water_type = 'drain' THEN :buffer_drain
                WHEN water_type = 'ditch' THEN :buffer_ditch
                ELSE :buffer_default
            END
    END AS buffer_size_m,
    
    -- Add buffer rule tracking
    CASE
        -- For polygons
        WHEN feature_type = 'polygon' THEN
            CASE
                WHEN water_type = 'water' AND name ILIKE '%lake%' THEN 'lake_name'
                WHEN water_type = 'water' AND name ILIKE '%pond%' THEN 'pond_name'
                WHEN water_type = 'reservoir' THEN 'reservoir_type'
                ELSE 'polygon_default'
            END
        -- For lines
        WHEN feature_type = 'line' THEN
            CASE
                WHEN width IS NOT NULL THEN 'width_attribute'
                WHEN water_type = 'river' THEN 'river_type'
                WHEN water_type = 'stream' THEN 'stream_type'
                WHEN water_type = 'canal' THEN 'canal_type'
                WHEN water_type = 'drain' THEN 'drain_type'
                WHEN water_type = 'ditch' THEN 'ditch_type'
                ELSE 'line_default'
            END
    END AS buffer_rule_applied,
    
    -- Add crossability rule tracking
    CASE
        WHEN intermittent = 'yes' THEN 
            CASE
                WHEN water_type = 'river' THEN 'intermittent_river'
                WHEN water_type = 'stream' THEN 'intermittent_stream'
                WHEN water_type = 'canal' THEN 'intermittent_canal'
                WHEN water_type = 'drain' THEN 'intermittent_drain'
                WHEN water_type = 'ditch' THEN 'intermittent_ditch'
                WHEN feature_type = 'polygon' AND name ILIKE '%lake%' THEN 'intermittent_lake'
                WHEN feature_type = 'polygon' AND name ILIKE '%pond%' THEN 'intermittent_pond'
                WHEN water_type = 'reservoir' THEN 'intermittent_reservoir'
                ELSE 'intermittent_default'
            END
        ELSE
            CASE
                WHEN water_type = 'river' THEN 'permanent_river'
                WHEN water_type = 'stream' THEN 'permanent_stream'
                WHEN water_type = 'canal' THEN 'permanent_canal'
                WHEN water_type = 'drain' THEN 'permanent_drain'
                WHEN water_type = 'ditch' THEN 'permanent_ditch'
                WHEN feature_type = 'polygon' AND name ILIKE '%lake%' THEN 'permanent_lake'
                WHEN feature_type = 'polygon' AND name ILIKE '%pond%' THEN 'permanent_pond'
                WHEN water_type = 'reservoir' THEN 'permanent_reservoir'
                ELSE 'permanent_default'
            END
    END AS crossability_rule_applied,
    
    -- Dynamic buffer size based on water type and attributes
    CASE
        -- For polygons
        WHEN feature_type = 'polygon' THEN
            CASE
                WHEN water_type = 'water' AND name ILIKE '%lake%' THEN 
                    ST_Buffer(ST_Transform(geom, 4326)::geography, :buffer_lake)::geometry(MultiPolygon, 4326)
                WHEN water_type = 'water' AND name ILIKE '%pond%' THEN 
                    ST_Buffer(ST_Transform(geom, 4326)::geography, :buffer_pond)::geometry(MultiPolygon, 4326)
                WHEN water_type = 'reservoir' THEN 
                    ST_Buffer(ST_Transform(geom, 4326)::geography, :buffer_reservoir)::geometry(MultiPolygon, 4326)
                ELSE 
                    ST_Buffer(ST_Transform(geom, 4326)::geography, :buffer_default)::geometry(MultiPolygon, 4326)
            END
        -- For lines
        WHEN feature_type = 'line' THEN
            CASE
                -- Use width attribute if available
                WHEN width IS NOT NULL THEN 
                    ST_Buffer(ST_Transform(geom, 4326)::geography, width::numeric + 10)::geometry(MultiPolygon, 4326)
                -- Otherwise use waterway type to estimate width
                WHEN water_type = 'river' THEN 
                    ST_Buffer(ST_Transform(geom, 4326)::geography, :buffer_river)::geometry(MultiPolygon, 4326)
                WHEN water_type = 'stream' THEN 
                    ST_Buffer(ST_Transform(geom, 4326)::geography, :buffer_stream)::geometry(MultiPolygon, 4326)
                WHEN water_type = 'canal' THEN 
                    ST_Buffer(ST_Transform(geom, 4326)::geography, :buffer_canal)::geometry(MultiPolygon, 4326)
                WHEN water_type = 'drain' THEN 
                    ST_Buffer(ST_Transform(geom, 4326)::geography, :buffer_drain)::geometry(MultiPolygon, 4326)
                WHEN water_type = 'ditch' THEN 
                    ST_Buffer(ST_Transform(geom, 4326)::geography, :buffer_ditch)::geometry(MultiPolygon, 4326)
                ELSE 
                    ST_Buffer(ST_Transform(geom, 4326)::geography, :buffer_default)::geometry(MultiPolygon, 4326)
            END
    END AS geom,
    -- Crossability score (0-100, where 0 is impassable, 100 is easily crossable)
    CASE
        -- Intermittent water features are more crossable
        WHEN intermittent = 'yes' THEN 
            CASE
                WHEN water_type = 'river' THEN :cross_river * :cross_intermittent_multiplier
                WHEN water_type = 'stream' THEN :cross_stream * :cross_intermittent_multiplier
                WHEN water_type = 'canal' THEN :cross_canal * :cross_intermittent_multiplier
                WHEN water_type = 'drain' THEN :cross_drain * :cross_intermittent_multiplier
                WHEN water_type = 'ditch' THEN :cross_ditch * :cross_intermittent_multiplier
                WHEN feature_type = 'polygon' AND name ILIKE '%lake%' THEN :cross_lake * :cross_intermittent_multiplier
                WHEN feature_type = 'polygon' AND name ILIKE '%pond%' THEN :cross_pond * :cross_intermittent_multiplier
                WHEN water_type = 'reservoir' THEN :cross_reservoir * :cross_intermittent_multiplier
                ELSE :cross_default * :cross_intermittent_multiplier
            END
        -- Regular water features
        ELSE
            CASE
                WHEN water_type = 'river' THEN :cross_river
                WHEN water_type = 'stream' THEN :cross_stream
                WHEN water_type = 'canal' THEN :cross_canal
                WHEN water_type = 'drain' THEN :cross_drain
                WHEN water_type = 'ditch' THEN :cross_ditch
                WHEN feature_type = 'polygon' AND name ILIKE '%lake%' THEN :cross_lake
                WHEN feature_type = 'polygon' AND name ILIKE '%pond%' THEN :cross_pond
                WHEN water_type = 'reservoir' THEN :cross_reservoir
                ELSE :cross_default
            END
    END AS crossability
FROM water_features;

-- Remove NULL geometries
DELETE FROM water_buf WHERE geom IS NULL;

-- Create spatial index
CREATE INDEX ON water_buf USING GIST(geom);

-- Log the results
SELECT 
    feature_type, 
    water_type, 
    buffer_rule_applied,
    crossability_rule_applied,
    COUNT(*) as count,
    AVG(buffer_size_m) as avg_buffer_size,
    AVG(crossability) as avg_crossability,
    MIN(crossability) as min_crossability,
    MAX(crossability) as max_crossability
FROM water_buf 
GROUP BY feature_type, water_type, buffer_rule_applied, crossability_rule_applied
ORDER BY feature_type, water_type;
