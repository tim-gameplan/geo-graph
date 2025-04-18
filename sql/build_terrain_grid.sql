-- build_terrain_grid.sql
-- param: profile text (default 'default')
DO $$
DECLARE
  profile text := COALESCE(:profile, 'default');
  cell integer;
BEGIN
  SELECT cell_m INTO cell FROM grid_profile WHERE name = profile;
  IF cell IS NULL THEN
    RAISE EXCEPTION 'Unknown grid profile %', profile;
  END IF;
  RAISE NOTICE 'Building terrain grid profile % (cell % m)', profile, cell;
  DROP TABLE IF EXISTS terrain_grid CASCADE;
  CREATE TABLE terrain_grid AS
  SELECT (ST_HexagonGrid(cell, (SELECT ST_Extent(geom) FROM water_buf))).geom AS geom
  FROM generate_series(1,1);
  ALTER TABLE terrain_grid ADD COLUMN cost double precision;
  UPDATE terrain_grid
    SET cost = 1.0; -- placeholder for slope cost
  CREATE INDEX ON terrain_grid USING GIST(geom);
END$$;
