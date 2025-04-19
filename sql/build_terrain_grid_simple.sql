-- build_terrain_grid.sql
-- Using default profile (cell_m = 200)
DO $$
DECLARE
  cell integer := 200; -- Default cell size
BEGIN
  RAISE NOTICE 'Building terrain grid with cell size % m', cell;
  DROP TABLE IF EXISTS terrain_grid CASCADE;
  CREATE TABLE terrain_grid AS
  SELECT (ST_HexagonGrid(cell, (SELECT ST_Extent(geom) FROM water_buf))).geom AS geom
  FROM generate_series(1,1);
  ALTER TABLE terrain_grid ADD COLUMN cost double precision;
  UPDATE terrain_grid
    SET cost = 1.0; -- placeholder for slope cost
  CREATE INDEX ON terrain_grid USING GIST(geom);
END$$;
