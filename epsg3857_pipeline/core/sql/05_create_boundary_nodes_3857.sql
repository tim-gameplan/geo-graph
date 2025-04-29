-- 05_create_boundary_nodes_3857.sql
-- Create boundary nodes and water boundary nodes for the boundary hexagon layer approach

-- Drop existing tables if they exist
DROP TABLE IF EXISTS boundary_land_portions CASCADE;
DROP TABLE IF EXISTS boundary_nodes CASCADE;
DROP TABLE IF EXISTS boundary_intersection_lines CASCADE;
DROP TABLE IF EXISTS water_boundary_nodes CASCADE;
DROP TABLE IF EXISTS narrow_water_crossings CASCADE;

-- Create land portions of boundary hexagons (including extended boundaries)
CREATE TABLE boundary_land_portions AS
SELECT
    hg.id AS hex_id,
    hg.geom AS hex_geom,
    CASE
        WHEN hg.hex_type IN ('boundary', 'boundary_extension') THEN 
            ST_Difference(hg.geom, ST_Union(wo.geom))
        ELSE hg.geom
    END AS land_portion
FROM
    terrain_grid hg
LEFT JOIN
    water_obstacles wo ON ST_Intersects(hg.geom, wo.geom)
WHERE
    hg.hex_type IN ('boundary', 'boundary_extension')
GROUP BY
    hg.id, hg.geom, hg.hex_type;

-- Create boundary nodes for boundary and boundary_extension hexagons
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

-- Create boundary nodes for water hexagons with land portions
INSERT INTO boundary_nodes (hex_id, node_type, geom)
SELECT
    hg.id AS hex_id,
    'water_boundary' AS node_type,
    CASE
        WHEN ST_Area(whlp.land_portion) > 0 THEN ST_PointOnSurface(whlp.land_portion)
        ELSE ST_Centroid(hg.geom)
    END AS geom
FROM
    terrain_grid hg
JOIN
    water_hex_land_portions whlp ON ST_Equals(hg.geom, whlp.water_hex_geom)
WHERE
    hg.hex_type = 'water_with_land'
    AND ST_Area(whlp.land_portion) > 0;

-- Extract intersection lines between boundary hexagons (including extended) and water obstacles
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
    hg.hex_type IN ('boundary', 'boundary_extension')
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
),
-- Add additional water boundary nodes in water hexagons for better connectivity
water_hex_points AS (
    SELECT
        hg.id AS hex_id,
        wo.id AS water_obstacle_id,
        ST_PointOnSurface(ST_Intersection(hg.geom, wo.geom)) AS geom
    FROM
        terrain_grid hg
    JOIN
        water_obstacles wo ON ST_Intersects(hg.geom, wo.geom)
    WHERE
        hg.hex_type = 'water_with_land'
        AND ST_Area(ST_Intersection(hg.geom, wo.geom)) > 0
)
SELECT
    ROW_NUMBER() OVER () AS node_id,
    hex_id,
    water_obstacle_id,
    'water_boundary' AS node_type,
    geom
FROM
    (
        SELECT hex_id, water_obstacle_id, geom FROM line_points
        UNION
        SELECT hex_id, water_obstacle_id, geom FROM water_hex_points
    ) AS combined_points;

-- Identify narrow water crossings
CREATE TABLE narrow_water_crossings AS
WITH land_pairs AS (
    SELECT
        l1.id AS land1_id,
        l2.id AS land2_id,
        l1.geom AS land1_geom,
        l2.geom AS land2_geom,
        ST_ShortestLine(l1.geom, l2.geom) AS crossing_line,
        -- Calculate the angle of the crossing line
        ST_Azimuth(l1.geom, l2.geom) AS crossing_angle
    FROM
        terrain_grid_points l1
    JOIN
        terrain_grid_points l2 ON ST_DWithin(l1.geom, l2.geom, :max_bridge_distance)
    WHERE
        l1.id < l2.id
        AND l1.hex_type IN ('land', 'boundary', 'boundary_extension')
        AND l2.hex_type IN ('land', 'boundary', 'boundary_extension')
        AND EXISTS (
            SELECT 1
            FROM water_obstacles wo
            WHERE ST_Intersects(ST_MakeLine(l1.geom, l2.geom), wo.geom)
        )
),
-- Find strategic crossing points at narrow parts of water obstacles
strategic_crossings AS (
    SELECT
        wo.id AS water_obstacle_id,
        ST_LineInterpolatePoint(
            ST_ShortestLine(
                ST_ExteriorRing(wo.geom),
                ST_ExteriorRing(ST_Translate(wo.geom, 1, 1))
            ),
            0.5
        ) AS crossing_point
    FROM
        water_obstacles wo
    WHERE
        ST_GeometryType(wo.geom) = 'ST_Polygon'
        AND ST_Area(wo.geom) > 0
        AND ST_Width(wo.geom) < :max_bridge_length
)
SELECT
    land1_id,
    land2_id,
    crossing_line,
    ST_Length(crossing_line) AS crossing_length,
    crossing_angle
FROM
    land_pairs
WHERE
    ST_Length(crossing_line) <= :max_bridge_length
UNION
-- Add strategic crossings as additional bridge locations
SELECT
    NULL AS land1_id,
    NULL AS land2_id,
    ST_MakeLine(
        ST_ClosestPoint(ST_ExteriorRing(wo.geom), sc.crossing_point),
        ST_ClosestPoint(ST_ExteriorRing(wo.geom), ST_Translate(sc.crossing_point, 1, 1))
    ) AS crossing_line,
    ST_Length(
        ST_MakeLine(
            ST_ClosestPoint(ST_ExteriorRing(wo.geom), sc.crossing_point),
            ST_ClosestPoint(ST_ExteriorRing(wo.geom), ST_Translate(sc.crossing_point, 1, 1))
        )
    ) AS crossing_length,
    ST_Azimuth(
        ST_ClosestPoint(ST_ExteriorRing(wo.geom), sc.crossing_point),
        ST_ClosestPoint(ST_ExteriorRing(wo.geom), ST_Translate(sc.crossing_point, 1, 1))
    ) AS crossing_angle
FROM
    strategic_crossings sc
JOIN
    water_obstacles wo ON sc.water_obstacle_id = wo.id
WHERE
    ST_Length(
        ST_MakeLine(
            ST_ClosestPoint(ST_ExteriorRing(wo.geom), sc.crossing_point),
            ST_ClosestPoint(ST_ExteriorRing(wo.geom), ST_Translate(sc.crossing_point, 1, 1))
        )
    ) <= :max_bridge_length;

-- Create bridge nodes
INSERT INTO boundary_nodes (node_type, geom)
SELECT
    'bridge' AS node_type,
    ST_LineInterpolatePoint(crossing_line, 0.5) AS geom
FROM
    narrow_water_crossings;

-- Create spatial indexes
CREATE INDEX boundary_nodes_geom_idx ON boundary_nodes USING GIST (geom);
CREATE INDEX water_boundary_nodes_geom_idx ON water_boundary_nodes USING GIST (geom);
CREATE INDEX narrow_water_crossings_geom_idx ON narrow_water_crossings USING GIST (crossing_line);

-- Log the results
SELECT 'Created ' || COUNT(*) || ' boundary land portions' FROM boundary_land_portions;
SELECT 'Created ' || COUNT(*) || ' boundary nodes' FROM boundary_nodes;
SELECT 'Created ' || COUNT(*) || ' boundary intersection lines' FROM boundary_intersection_lines;
SELECT 'Created ' || COUNT(*) || ' water boundary nodes' FROM water_boundary_nodes;
SELECT 'Created ' || COUNT(*) || ' narrow water crossings' FROM narrow_water_crossings;
SELECT 'Boundary nodes by type:';
SELECT node_type, COUNT(*) FROM boundary_nodes GROUP BY node_type;
