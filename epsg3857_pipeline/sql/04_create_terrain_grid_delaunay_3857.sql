-- Create terrain grid with Delaunay triangulation using EPSG:3857 coordinates
-- Parameters:
-- :storage_srid - SRID for storage (default: 3857)
-- :grid_spacing - Grid spacing in meters (default: 200)
-- :boundary_point_spacing - Boundary point spacing in meters (default: 100)
-- :simplify_tolerance - Simplification tolerance in meters (default: 5)

-- Create terrain grid table
DROP TABLE IF EXISTS terrain_grid CASCADE;
CREATE TABLE terrain_grid (
    id SERIAL PRIMARY KEY,
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
INSERT INTO terrain_grid (geom)
SELECT 
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

-- Create boundary points along water obstacle boundaries
WITH boundary_lines AS (
    -- Extract boundary lines from water obstacles
    SELECT 
        ST_Boundary(geom) AS geom
    FROM 
        water_obstacles
)
INSERT INTO terrain_grid (geom)
SELECT 
    (ST_DumpPoints(
        ST_Segmentize(
            geom, 
            :boundary_point_spacing
        )
    )).geom AS geom
FROM 
    boundary_lines;

-- Remove duplicate points
DELETE FROM terrain_grid
WHERE id IN (
    SELECT t1.id
    FROM terrain_grid t1
    JOIN terrain_grid t2 ON ST_DWithin(t1.geom, t2.geom, 1)
    WHERE t1.id > t2.id
);

-- Create spatial index
CREATE INDEX terrain_grid_geom_idx ON terrain_grid USING GIST (geom);

-- Log the results
SELECT 'Created ' || COUNT(*) || ' terrain grid points for Delaunay triangulation' FROM terrain_grid;

-- Create Delaunay triangulation
DROP TABLE IF EXISTS delaunay_triangles CASCADE;
CREATE TABLE delaunay_triangles (
    id SERIAL PRIMARY KEY,
    geom GEOMETRY(POLYGON, :storage_srid)
);

-- Create Delaunay triangulation
INSERT INTO delaunay_triangles (geom)
SELECT 
    (ST_Dump(
        ST_DelaunayTriangles(
            ST_Collect(geom),
            :simplify_tolerance,
            0
        )
    )).geom AS geom
FROM 
    terrain_grid;

-- Remove triangles that intersect with water obstacles
DELETE FROM delaunay_triangles
WHERE EXISTS (
    SELECT 1
    FROM water_obstacles
    WHERE ST_Intersects(water_obstacles.geom, delaunay_triangles.geom)
);

-- Create spatial index
CREATE INDEX delaunay_triangles_geom_idx ON delaunay_triangles USING GIST (geom);

-- Log the results
SELECT 'Created ' || COUNT(*) || ' Delaunay triangles' FROM delaunay_triangles;

-- Create Delaunay edges
DROP TABLE IF EXISTS delaunay_edges CASCADE;
CREATE TABLE delaunay_edges (
    id SERIAL PRIMARY KEY,
    start_point GEOMETRY(POINT, :storage_srid),
    end_point GEOMETRY(POINT, :storage_srid),
    geom GEOMETRY(LINESTRING, :storage_srid)
);

-- Extract edges from Delaunay triangles
INSERT INTO delaunay_edges (start_point, end_point, geom)
WITH edges AS (
    SELECT 
        (ST_DumpSegments(ST_Boundary(geom))).geom AS geom
    FROM 
        delaunay_triangles
)
SELECT 
    ST_StartPoint(geom) AS start_point,
    ST_EndPoint(geom) AS end_point,
    geom
FROM 
    edges;

-- Remove duplicate edges
DELETE FROM delaunay_edges
WHERE id IN (
    SELECT e1.id
    FROM delaunay_edges e1
    JOIN delaunay_edges e2 ON 
        (ST_DWithin(e1.start_point, e2.start_point, 1) AND ST_DWithin(e1.end_point, e2.end_point, 1)) OR
        (ST_DWithin(e1.start_point, e2.end_point, 1) AND ST_DWithin(e1.end_point, e2.start_point, 1))
    WHERE e1.id > e2.id
);

-- Create spatial index
CREATE INDEX delaunay_edges_geom_idx ON delaunay_edges USING GIST (geom);
CREATE INDEX delaunay_edges_start_point_idx ON delaunay_edges USING GIST (start_point);
CREATE INDEX delaunay_edges_end_point_idx ON delaunay_edges USING GIST (end_point);

-- Log the results
SELECT 'Created ' || COUNT(*) || ' Delaunay edges' FROM delaunay_edges;
