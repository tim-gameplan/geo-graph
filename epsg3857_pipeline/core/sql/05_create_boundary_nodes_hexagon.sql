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
DROP TABLE IF EXISTS boundary_nodes CASCADE;
DROP TABLE IF EXISTS water_boundary_nodes CASCADE;
DROP TABLE IF EXISTS land_portion_nodes CASCADE;

-- Create boundary nodes table
CREATE TABLE boundary_nodes (
    id SERIAL PRIMARY KEY,
    geom GEOMETRY(POINT, :storage_srid),
    node_type VARCHAR(20),
    hex_id INTEGER
);

-- Create water boundary nodes table
CREATE TABLE water_boundary_nodes (
    id SERIAL PRIMARY KEY,
    geom GEOMETRY(POINT, :storage_srid),
    node_type VARCHAR(20)
);

-- Create land portion nodes table
CREATE TABLE land_portion_nodes (
    id SERIAL PRIMARY KEY,
    geom GEOMETRY(POINT, :storage_srid),
    node_type VARCHAR(20),
    hex_id INTEGER
);

-- Create boundary nodes from terrain grid
-- Use DISTINCT ON to ensure we don't create duplicate boundary nodes
INSERT INTO boundary_nodes (geom, node_type, hex_id)
SELECT DISTINCT ON (ST_AsText(ST_SnapToGrid(ST_Centroid(t.geom), 0.001)))
    ST_Centroid(t.geom),
    'boundary',
    t.id
FROM 
    terrain_grid t
WHERE 
    t.hex_type = 'boundary';

-- Create water boundary nodes along water obstacle boundaries
-- Generate points along water obstacle boundaries at regular intervals
INSERT INTO water_boundary_nodes (geom, node_type)
WITH water_boundaries AS (
    SELECT 
        ST_Boundary(geom) AS boundary_geom
    FROM 
        water_obstacles
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
INSERT INTO land_portion_nodes (geom, node_type, hex_id)
WITH land_portion_centroids AS (
    SELECT 
        ROW_NUMBER() OVER () AS temp_id,
        ST_Centroid(land_portion) AS centroid,
        water_hex_geom
    FROM 
        water_hex_land_portions
),
land_portion_points AS (
    -- If the centroid is in water, find a point on the land portion
    SELECT 
        lpc.temp_id,
        CASE
            WHEN EXISTS (
                SELECT 1
                FROM water_obstacles wo
                WHERE ST_Contains(wo.geom, lpc.centroid)
            ) THEN (
                -- Find a point on the land portion that's not in water
                SELECT 
                    ST_PointOnSurface(whl.land_portion)
                FROM 
                    water_hex_land_portions whl
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
    terrain_grid t ON t.geom = lpp.water_hex_geom;

-- Create spatial indexes
CREATE INDEX boundary_nodes_geom_idx ON boundary_nodes USING GIST (geom);
CREATE INDEX water_boundary_nodes_geom_idx ON water_boundary_nodes USING GIST (geom);
CREATE INDEX land_portion_nodes_geom_idx ON land_portion_nodes USING GIST (geom);

-- Log the results
SELECT 'Created ' || COUNT(*) || ' boundary nodes' FROM boundary_nodes;
SELECT 'Created ' || COUNT(*) || ' water boundary nodes' FROM water_boundary_nodes;
SELECT 'Created ' || COUNT(*) || ' land portion nodes' FROM land_portion_nodes;
