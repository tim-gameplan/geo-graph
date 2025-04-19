-- build_water_buffers.sql
-- Usage: psql -f sql/build_water_buffers.sql -v buf_m=50
DO $$
BEGIN
  RAISE NOTICE 'Building water buffers 50 m';
  DROP TABLE IF EXISTS water_buf CASCADE;
  CREATE TABLE water_buf AS
  SELECT id,
         ST_Buffer(ST_Transform(geom, 4326)::geography, 50)::geometry(MultiPolygon, 4326) AS geom
  FROM water_polys;
  CREATE INDEX ON water_buf USING GIST(geom);
END$$;
