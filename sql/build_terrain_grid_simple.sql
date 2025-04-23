-- build_terrain_grid.sql
-- Using default profile (cell_m = 200)
DO $$
DECLARE
  cell integer := 200; -- Default cell size (meters)
  extent_4326 geometry;
  extent_3857 geometry;
BEGIN
  RAISE NOTICE 'Building terrain grid with cell size % m (EPSG:3857)', cell;
  
  -- Get extent of water buffers in EPSG:4326
  SELECT ST_Extent(geom) INTO extent_4326 FROM water_buf;
  
  IF extent_4326 IS NULL THEN
    RAISE EXCEPTION 'Could not determine extent from water_buf table.';
  END IF;

  -- Transform extent to EPSG:3857 for meter-based grid generation
  extent_3857 := ST_Transform(extent_4326, 3857);

  DROP TABLE IF EXISTS terrain_grid CASCADE;
  CREATE TABLE terrain_grid AS
  SELECT (ST_HexagonGrid(cell, extent_3857)).geom AS geom; -- Use transformed extent

  -- Ensure the geometry column has the correct SRID
  PERFORM UpdateGeometrySRID('public', 'terrain_grid', 'geom', 3857);

  ALTER TABLE terrain_grid ADD COLUMN cost double precision;
  UPDATE terrain_grid
    SET cost = 1.0; -- placeholder for slope cost
  
  CREATE INDEX ON terrain_grid USING GIST(geom);
END$$;
