-- Create terrain grid with EPSG:3857 coordinates
-- Parameters:
-- :storage_srid - SRID for storage (default: 3857)
-- :grid_spacing - Grid spacing in meters (default: 200)

-- Create terrain grid table
DROP TABLE IF EXISTS terrain_grid CASCADE;
CREATE TABLE terrain_grid (
    id SERIAL PRIMARY KEY,
    row INTEGER,
    col INTEGER,
    geom GEOMETRY(POINT, :storage_srid)
);

-- Get the extent of the data
WITH extent AS (
    SELECT 
        ST_Extent(geom) AS bbox
    FROM 
        water_features
)
-- Create a grid of points
INSERT INTO terrain_grid (row, col, geom)
SELECT 
    row_num,
    col_num,
    ST_SetSRID(ST_MakePoint(
        ST_XMin(bbox) + col_num * :grid_spacing,
        ST_YMin(bbox) + row_num * :grid_spacing
    ), :storage_srid) AS geom
FROM 
    extent,
    generate_series(0, (ST_XMax(bbox) - ST_XMin(bbox)) / :grid_spacing, 1) AS col_num,
    generate_series(0, (ST_YMax(bbox) - ST_YMin(bbox)) / :grid_spacing, 1) AS row_num
WHERE 
    -- Exclude points that are inside water obstacles
    NOT EXISTS (
        SELECT 1
        FROM water_obstacles
        WHERE ST_Contains(water_obstacles.geom, ST_SetSRID(ST_MakePoint(
            ST_XMin(bbox) + col_num * :grid_spacing,
            ST_YMin(bbox) + row_num * :grid_spacing
        ), :storage_srid))
    );

-- Create spatial index
CREATE INDEX terrain_grid_geom_idx ON terrain_grid USING GIST (geom);

-- Log the results
SELECT 'Created ' || COUNT(*) || ' terrain grid points' FROM terrain_grid;
