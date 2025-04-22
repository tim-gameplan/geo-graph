-- build_water_buffers.sql
-- Builds water_buf table with type-specific buffer sizes based on default_config.json
DO $$
BEGIN
  RAISE NOTICE 'Building water buffers from water_polys using geometry and type-specific sizes';
  DROP TABLE IF EXISTS water_buf CASCADE;
  CREATE TABLE water_buf AS
  SELECT id,
         ST_Multi(ST_Buffer(geom,
            CASE
                -- Match line types from config
                WHEN feature_type = 'line' AND waterway = 'river' THEN 50
                WHEN feature_type = 'line' AND waterway = 'stream' THEN 20
                WHEN feature_type = 'line' AND waterway = 'canal' THEN 30
                WHEN feature_type = 'line' AND waterway = 'drain' THEN 5
                WHEN feature_type = 'line' AND waterway = 'ditch' THEN 5
                -- Match polygon types from config (using water_type derived earlier)
                WHEN feature_type = 'polygon' AND water_type = 'lake' THEN 50 -- Assuming water_type catches 'water=lake' etc.
                WHEN feature_type = 'polygon' AND water_type = 'pond' THEN 20 -- Assuming water_type catches 'water=pond'
                WHEN feature_type = 'polygon' AND water_type = 'reservoir' THEN 50
                -- Fallback to default buffer size
                ELSE 50
            END
         )) AS geom
  FROM water_polys;

  CREATE INDEX ON water_buf USING GIST(geom);
END$$;
