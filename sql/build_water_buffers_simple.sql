-- build_water_buffers_simple.sql
-- Enhanced version with different buffer sizes based on water type
DO $$
BEGIN
  RAISE NOTICE 'Building water buffers with variable sizes based on water type';
  DROP TABLE IF EXISTS water_buf CASCADE;
  CREATE TABLE water_buf AS
  SELECT 
    id,
    feature_type,
    water_type,
    -- Apply different buffer sizes based on water type
    CASE
      -- For polygons
      WHEN feature_type = 'polygon' THEN
        CASE
          WHEN water_type = 'water' AND name ILIKE '%lake%' THEN 100
          WHEN water_type = 'water' AND name ILIKE '%pond%' THEN 50
          WHEN water_type = 'reservoir' THEN 75
          ELSE 50
        END
      -- For lines
      WHEN feature_type = 'line' THEN
        CASE
          -- Use width attribute if available, stripping units
          WHEN width IS NOT NULL THEN regexp_replace(width, '[^0-9.]', '', 'g')::numeric + 10
          WHEN water_type = 'river' THEN 100
          WHEN water_type = 'stream' THEN 30
          WHEN water_type = 'canal' THEN 50
          WHEN water_type = 'drain' THEN 20
          WHEN water_type = 'ditch' THEN 10
          ELSE 50
        END
      ELSE 50
    END AS buffer_size_m,
    -- Apply the buffer with the calculated size
    CASE
      -- For polygons
      WHEN feature_type = 'polygon' THEN
        CASE
          WHEN water_type = 'water' AND name ILIKE '%lake%' THEN 
            ST_Buffer(ST_Transform(geom, 4326)::geography, 100)::geometry(MultiPolygon, 4326)
          WHEN water_type = 'water' AND name ILIKE '%pond%' THEN 
            ST_Buffer(ST_Transform(geom, 4326)::geography, 50)::geometry(MultiPolygon, 4326)
          WHEN water_type = 'reservoir' THEN 
            ST_Buffer(ST_Transform(geom, 4326)::geography, 75)::geometry(MultiPolygon, 4326)
          ELSE 
            ST_Buffer(ST_Transform(geom, 4326)::geography, 50)::geometry(MultiPolygon, 4326)
        END
      -- For lines
      WHEN feature_type = 'line' THEN
        CASE
          -- Use width attribute if available, stripping units
          WHEN width IS NOT NULL THEN 
            ST_Buffer(ST_Transform(geom, 4326)::geography, regexp_replace(width, '[^0-9.]', '', 'g')::numeric + 10)::geometry(MultiPolygon, 4326)
          -- Otherwise use waterway type to estimate width
          WHEN water_type = 'river' THEN 
            ST_Buffer(ST_Transform(geom, 4326)::geography, 100)::geometry(MultiPolygon, 4326)
          WHEN water_type = 'stream' THEN 
            ST_Buffer(ST_Transform(geom, 4326)::geography, 30)::geometry(MultiPolygon, 4326)
          WHEN water_type = 'canal' THEN 
            ST_Buffer(ST_Transform(geom, 4326)::geography, 50)::geometry(MultiPolygon, 4326)
          WHEN water_type = 'drain' THEN 
            ST_Buffer(ST_Transform(geom, 4326)::geography, 20)::geometry(MultiPolygon, 4326)
          WHEN water_type = 'ditch' THEN 
            ST_Buffer(ST_Transform(geom, 4326)::geography, 10)::geometry(MultiPolygon, 4326)
          ELSE 
            ST_Buffer(ST_Transform(geom, 4326)::geography, 50)::geometry(MultiPolygon, 4326)
        END
      ELSE
        ST_Buffer(ST_Transform(geom, 4326)::geography, 50)::geometry(MultiPolygon, 4326)
    END AS geom
  FROM water_polys;
  
  -- Remove NULL geometries
  DELETE FROM water_buf WHERE geom IS NULL;
  
  -- Create spatial index
  CREATE INDEX ON water_buf USING GIST(geom);
  
  -- Log the results
  RAISE NOTICE 'Water buffers created: % features', (SELECT COUNT(*) FROM water_buf);
END$$;
