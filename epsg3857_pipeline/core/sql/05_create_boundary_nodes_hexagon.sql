/*
 * 05_create_boundary_nodes_hexagon.sql
 * 
 * Create boundary nodes for the boundary hexagon layer approach
 * This script creates:
 * 1. Boundary nodes on the edges of terrain hexagons
 * 2. Water boundary nodes along water obstacle boundaries
 * 3. Land portion nodes on the land portions of water hexagons
 */

-- Drop existing tables if they exist
DROP TABLE IF EXISTS s05_nodes_boundary CASCADE;
DROP TABLE IF EXISTS s05_nodes_water_boundary CASCADE;
DROP TABLE IF EXISTS s05_nodes_land_portion CASCADE;

-- Create boundary nodes table
CREATE TABLE s05_nodes_boundary (
    id SERIAL PRIMARY KEY,
    geom GEOMETRY(POINT, :storage_srid),
    node_type VARCHAR(20),
    hex_id INTEGER
);

-- Create water boundary nodes table
CREATE TABLE s05_nodes_water_boundary (
    id SERIAL PRIMARY KEY,
    geom GEOMETRY(POINT, :storage_srid),
    node_type VARCHAR(20)
);

-- Create land portion nodes table
CREATE TABLE s05_nodes_land_portion (
    id SERIAL PRIMARY KEY,
    geom GEOMETRY(POINT, :storage_srid),
    node_type VARCHAR(20),
    hex_id INTEGER
);

-- Create boundary nodes from terrain grid
-- Use DISTINCT ON to ensure we don't create duplicate boundary nodes
INSERT INTO s05_nodes_boundary (geom, node_type, hex_id)
SELECT DISTINCT ON (ST_AsText(ST_SnapToGrid(ST_Centroid(t.geom), 0.001)))
    ST_Centroid(t.geom),
    'boundary',
    t.id
FROM 
    s04_grid_terrain t
WHERE 
    t.hex_type = 'boundary';

-- Create water boundary nodes along water obstacle boundaries
-- Generate points along water obstacle boundaries at regular intervals
INSERT INTO s05_nodes_water_boundary (geom, node_type)
WITH water_boundaries AS (
    SELECT 
        ST_Boundary(geom) AS boundary_geom
    FROM 
        s03_water_obstacles
),
boundary_points AS (
    SELECT 
        (ST_DumpPoints(ST_Segmentize(boundary_geom, :boundary_node_spacing))).geom AS point_geom
    FROM 
        water_boundaries
)
SELECT 
    point_geom,
    'water_boundary'
FROM 
    boundary_points;

-- Create land portion nodes on the land portions of water hexagons
INSERT INTO s05_nodes_land_portion (geom, node_type, hex_id)
WITH land_portion_centroids AS (
    SELECT 
        ROW_NUMBER() OVER () AS temp_id,
        ST_Centroid(land_portion) AS centroid,
        water_hex_geom
    FROM 
        s04_grid_water_land_portions
),
land_portion_points AS (
    -- If the centroid is in water, find a point on the land portion
    SELECT 
        lpc.temp_id,
        CASE
            WHEN EXISTS (
                SELECT 1
                FROM s03_water_obstacles wo
                WHERE ST_Contains(wo.geom, lpc.centroid)
            ) THEN (
                -- Find a point on the land portion that's not in water
                SELECT 
                    ST_PointOnSurface(whl.land_portion)
                FROM 
                    s04_grid_water_land_portions whl
                WHERE 
                    whl.water_hex_geom = lpc.water_hex_geom
            )
            ELSE lpc.centroid
        END AS point_geom,
        lpc.water_hex_geom
    FROM 
        land_portion_centroids lpc
)
SELECT 
    lpp.point_geom,
    'land_portion',
    t.id
FROM 
    land_portion_points lpp
JOIN 
    s04_grid_terrain t ON t.geom = lpp.water_hex_geom;

-- Create spatial indexes
CREATE INDEX s05_nodes_boundary_geom_idx ON s05_nodes_boundary USING GIST (geom);
CREATE INDEX s05_nodes_water_boundary_geom_idx ON s05_nodes_water_boundary USING GIST (geom);
CREATE INDEX s05_nodes_land_portion_geom_idx ON s05_nodes_land_portion USING GIST (geom);

-- Log the results
SELECT 'Created ' || COUNT(*) || ' boundary nodes' FROM s05_nodes_boundary;
SELECT 'Created ' || COUNT(*) || ' water boundary nodes' FROM s05_nodes_water_boundary;
SELECT 'Created ' || COUNT(*) || ' land portion nodes' FROM s05_nodes_land_portion;
