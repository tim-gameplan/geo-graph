-- build_water_buffers.sql
-- Usage: psql -f sql/build_water_buffers.sql -v buf_m=50
DO $$
DECLARE
  buf_m integer := COALESCE(:buf_m, 50);
BEGIN
  RAISE NOTICE 'Building water buffers % m', buf_m;
  DROP TABLE IF EXISTS water_buf CASCADE;
  CREATE TABLE water_buf AS
  SELECT id,
         ST_Buffer(geom::geography, buf_m)::geometry(MultiPolygon, 4326) AS geom
  FROM water_polys;
  CREATE INDEX ON water_buf USING GIST(geom);
END$$;
