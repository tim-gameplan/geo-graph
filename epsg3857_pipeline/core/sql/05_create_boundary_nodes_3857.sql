-- 05_create_boundary_nodes_3857.sql
-- Create boundary nodes and water boundary nodes for the boundary hexagon layer approach

-- Drop existing tables if they exist
DROP TABLE IF EXISTS boundary_land_portions CASCADE;
DROP TABLE IF EXISTS boundary_nodes CASCADE;
DROP TABLE IF EXISTS boundary_intersection_lines CASCADE;
DROP TABLE IF EXISTS water_boundary_nodes CASCADE;

-- Create land portions of boundary hexagons
CREATE TABLE boundary_land_portions AS
SELECT
    hg.id AS hex_id,
    hg.geom AS hex_geom,
    ST_Difference(hg.geom, ST_Union(wo.geom)) AS land_portion
FROM
    terrain_grid hg
JOIN
    water_obstacles wo ON ST_Intersects(hg.geom, wo.geom)
WHERE
    hg.hex_type = 'boundary'
GROUP BY
    hg.id, hg.geom;

-- Create boundary nodes
CREATE TABLE boundary_nodes AS
SELECT
    ROW_NUMBER() OVER () AS node_id,
    hex_id,
    'boundary' AS node_type,
    CASE
        WHEN ST_Contains(land_portion, ST_Centroid(hex_geom)) THEN ST_Centroid(hex_geom)
        ELSE ST_PointOnSurface(land_portion)
    END AS geom
FROM
    boundary_land_portions;

-- Extract intersection lines between boundary hexagons and water obstacles
CREATE TABLE boundary_intersection_lines AS
SELECT
    hg.id AS hex_id,
    wo.id AS water_obstacle_id,
    ST_Intersection(hg.geom, wo.geom) AS intersection_line
FROM
    terrain_grid hg
JOIN
    water_obstacles wo ON ST_Intersects(hg.geom, wo.geom)
WHERE
    hg.hex_type = 'boundary'
    AND ST_Dimension(ST_Intersection(hg.geom, wo.geom)) = 1; -- Only keep line intersections

-- Create water boundary nodes at regular intervals
CREATE TABLE water_boundary_nodes AS
WITH line_points AS (
    SELECT
        hex_id,
        water_obstacle_id,
        (ST_DumpPoints(ST_Segmentize(intersection_line, :boundary_node_spacing))).geom AS geom
    FROM
        boundary_intersection_lines
)
SELECT
    ROW_NUMBER() OVER () AS node_id,
    hex_id,
    water_obstacle_id,
    'water_boundary' AS node_type,
    geom
FROM
    line_points;

-- Create spatial indexes
CREATE INDEX boundary_nodes_geom_idx ON boundary_nodes USING GIST (geom);
CREATE INDEX water_boundary_nodes_geom_idx ON water_boundary_nodes USING GIST (geom);

-- Log the results
SELECT 'Created ' || COUNT(*) || ' boundary land portions' FROM boundary_land_portions;
SELECT 'Created ' || COUNT(*) || ' boundary nodes' FROM boundary_nodes;
SELECT 'Created ' || COUNT(*) || ' boundary intersection lines' FROM boundary_intersection_lines;
SELECT 'Created ' || COUNT(*) || ' water boundary nodes' FROM water_boundary_nodes;
