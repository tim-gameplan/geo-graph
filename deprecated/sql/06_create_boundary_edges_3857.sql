-- 06_create_boundary_edges_3857.sql
-- Create edges between different node types for the boundary hexagon layer approach

-- Drop existing tables if they exist
DROP TABLE IF EXISTS land_land_edges CASCADE;
DROP TABLE IF EXISTS land_boundary_edges CASCADE;
DROP TABLE IF EXISTS boundary_boundary_edges CASCADE;
DROP TABLE IF EXISTS boundary_water_edges CASCADE;
DROP TABLE IF EXISTS water_boundary_edges CASCADE;
DROP TABLE IF EXISTS water_boundary_to_boundary_edges CASCADE;
DROP TABLE IF EXISTS bridge_to_boundary_edges CASCADE;

-- Create land-to-land edges (similar to standard approach)
CREATE TABLE land_land_edges AS
SELECT
    t1.id AS source_id,
    t2.id AS target_id,
    ST_Length(ST_MakeLine(t1.geom, t2.geom)) AS length,
    ST_Length(ST_MakeLine(t1.geom, t2.geom)) / 5.0 AS cost, -- Normal speed on land (5 m/s)
    'land_land' AS edge_type,
    ST_MakeLine(t1.geom, t2.geom) AS geom
FROM
    terrain_grid_points t1
JOIN
    terrain_grid_points t2 ON ST_DWithin(t1.geom, t2.geom, :max_edge_length)
WHERE
    t1.id < t2.id
    AND t1.hex_type = 'land'
    AND t2.hex_type = 'land'
    AND NOT EXISTS (
        SELECT 1
        FROM water_obstacles
        WHERE ST_Intersects(water_obstacles.geom, ST_MakeLine(t1.geom, t2.geom))
    );

-- Create land-to-boundary edges (including boundary_extension and water_boundary nodes)
CREATE TABLE land_boundary_edges AS
SELECT
    t.id AS source_id,
    b.node_id AS target_id,
    ST_Length(ST_MakeLine(t.geom, b.geom)) AS length,
    ST_Length(ST_MakeLine(t.geom, b.geom)) / 5.0 AS cost, -- Normal speed on land (5 m/s)
    'land_boundary' AS edge_type,
    ST_MakeLine(t.geom, b.geom) AS geom
FROM
    terrain_grid_points t
JOIN
    boundary_nodes b ON ST_DWithin(t.geom, b.geom, :max_edge_length)
WHERE
    t.hex_type = 'land'
    AND b.node_type IN ('boundary', 'water_boundary')
    AND NOT EXISTS (
        SELECT 1
        FROM water_obstacles
        WHERE ST_Intersects(water_obstacles.geom, ST_MakeLine(t.geom, b.geom))
    );

-- Create boundary-to-boundary edges (including all boundary node types)
CREATE TABLE boundary_boundary_edges AS
SELECT
    b1.node_id AS source_id,
    b2.node_id AS target_id,
    ST_Length(ST_MakeLine(b1.geom, b2.geom)) AS length,
    ST_Length(ST_MakeLine(b1.geom, b2.geom)) / 5.0 AS cost, -- Normal speed on land (5 m/s)
    'boundary_boundary' AS edge_type,
    ST_MakeLine(b1.geom, b2.geom) AS geom
FROM
    boundary_nodes b1
JOIN
    boundary_nodes b2 ON ST_DWithin(b1.geom, b2.geom, :max_edge_length)
WHERE
    b1.node_id < b2.node_id
    AND b1.node_type IN ('boundary', 'water_boundary')
    AND b2.node_type IN ('boundary', 'water_boundary')
    AND NOT EXISTS (
        SELECT 1
        FROM water_obstacles
        WHERE ST_Intersects(water_obstacles.geom, ST_MakeLine(b1.geom, b2.geom))
    );

-- Create edges to connect water boundary nodes to regular boundary nodes
CREATE TABLE water_boundary_to_boundary_edges AS
SELECT
    wb.node_id AS source_id,
    b.node_id AS target_id,
    ST_Length(ST_MakeLine(wb.geom, b.geom)) AS length,
    ST_Length(ST_MakeLine(wb.geom, b.geom)) / 5.0 AS cost,
    'water_boundary_to_boundary' AS edge_type,
    ST_MakeLine(wb.geom, b.geom) AS geom
FROM
    boundary_nodes wb
JOIN
    boundary_nodes b ON ST_DWithin(wb.geom, b.geom, :max_edge_length)
WHERE
    wb.node_type = 'water_boundary'
    AND b.node_type = 'boundary'
    AND wb.node_id != b.node_id
    AND NOT EXISTS (
        SELECT 1
        FROM water_obstacles
        WHERE ST_Intersects(water_obstacles.geom, ST_MakeLine(wb.geom, b.geom))
    );

-- Create edges to connect bridge nodes to other nodes
CREATE TABLE bridge_to_boundary_edges AS
SELECT
    br.node_id AS source_id,
    b.node_id AS target_id,
    ST_Length(ST_MakeLine(br.geom, b.geom)) AS length,
    ST_Length(ST_MakeLine(br.geom, b.geom)) / 5.0 AS cost,
    'bridge_to_boundary' AS edge_type,
    ST_MakeLine(br.geom, b.geom) AS geom
FROM
    boundary_nodes br
JOIN
    boundary_nodes b ON ST_DWithin(br.geom, b.geom, :max_edge_length)
WHERE
    br.node_type = 'bridge'
    AND b.node_type IN ('boundary', 'water_boundary')
    AND br.node_id != b.node_id
    AND NOT EXISTS (
        SELECT 1
        FROM water_obstacles
        WHERE ST_Intersects(water_obstacles.geom, ST_MakeLine(br.geom, b.geom))
    );

-- Create boundary-to-water edges with enhanced directional filtering and more selective connections
CREATE TABLE boundary_water_edges AS
WITH directional_sectors AS (
    SELECT
        b.node_id AS boundary_node_id,
        w.node_id AS water_node_id,
        ST_Azimuth(b.geom, w.geom) AS azimuth,
        FLOOR(ST_Azimuth(b.geom, w.geom) / (2 * PI() / :direction_count)) AS direction_sector,
        ST_Distance(b.geom, w.geom) AS distance,
        ST_MakeLine(b.geom, w.geom) AS geom,
        -- Calculate the angle between the edge and the water obstacle boundary
        ABS(ST_Azimuth(b.geom, w.geom) - 
            ST_Azimuth(
                w.geom, 
                ST_ClosestPoint(
                    (SELECT ST_ExteriorRing(wo.geom) FROM water_obstacles wo WHERE wo.id = w.water_obstacle_id),
                    w.geom
                )
            )
        ) AS boundary_angle,
        -- Calculate the distance to the nearest other boundary node
        (SELECT MIN(ST_Distance(b.geom, b2.geom))
         FROM boundary_nodes b2
         WHERE b2.node_id != b.node_id AND b2.node_type = 'boundary') AS nearest_boundary_distance
    FROM
        boundary_nodes b
    JOIN
        water_boundary_nodes w ON ST_DWithin(b.geom, w.geom, :max_edge_length)
    WHERE
        b.node_type IN ('boundary', 'water_boundary')
        AND NOT EXISTS (
            SELECT 1
            FROM water_obstacles
            WHERE ST_Contains(water_obstacles.geom, b.geom)
        )
),
-- Calculate a score for each potential connection based on multiple factors
scored_connections AS (
    SELECT
        boundary_node_id,
        water_node_id,
        distance,
        geom,
        direction_sector,
        -- Enhanced scoring formula:
        -- 1. Prioritize shorter distances
        -- 2. Prefer perpendicular angles to the water boundary
        -- 3. Favor boundary nodes that are farther from other boundary nodes (to spread connections)
        -- 4. Add a small random factor to break ties
        (distance * 0.6) + 
        (ABS(PI()/2 - boundary_angle) * distance * 0.3) + 
        (1.0 / (nearest_boundary_distance + 1.0) * distance * 0.1) +
        (random() * 0.01 * distance) AS connection_score
    FROM
        directional_sectors
)
SELECT
    boundary_node_id AS source_id,
    water_node_id AS target_id,
    distance AS length,
    distance / (5.0 * :water_speed_factor) AS cost,
    'boundary_water' AS edge_type,
    geom
FROM (
    SELECT 
        boundary_node_id, water_node_id, distance, geom,
        ROW_NUMBER() OVER (PARTITION BY boundary_node_id, direction_sector ORDER BY connection_score) AS rank
    FROM
        scored_connections
) AS ranked_connections
WHERE
    -- Reduce the number of connections per direction for cleaner visualization
    rank <= GREATEST(1, FLOOR(:max_connections_per_direction / 2))
    -- Additional filtering to ensure more even distribution
    AND (boundary_node_id % 2 = 0 OR direction_sector % 2 = 0);

-- Create water boundary edges with improved connectivity and more natural distribution
CREATE TABLE water_boundary_edges AS
WITH ordered_nodes AS (
    SELECT
        node_id,
        water_obstacle_id,
        geom,
        ST_Azimuth(geom, ST_Centroid(
            (SELECT geom FROM water_obstacles WHERE id = water_obstacle_id)
        )) AS azimuth,
        -- Calculate the position along the boundary (normalized 0-1)
        ST_LineLocatePoint(
            ST_ExteriorRing((SELECT geom FROM water_obstacles WHERE id = water_obstacle_id)),
            geom
        ) AS boundary_position,
        -- Calculate the distance to the nearest other water boundary node
        (SELECT MIN(ST_Distance(wbn1.geom, wbn2.geom))
         FROM water_boundary_nodes wbn2
         WHERE wbn2.node_id != water_boundary_nodes.node_id 
         AND wbn2.water_obstacle_id = water_boundary_nodes.water_obstacle_id) AS nearest_node_distance
    FROM
        water_boundary_nodes
),
-- Calculate sequential nodes along the boundary
sequential_nodes AS (
    SELECT
        n1.node_id AS source_id,
        n2.node_id AS target_id,
        n1.water_obstacle_id,
        ST_Length(ST_MakeLine(n1.geom, n2.geom)) AS length,
        ST_MakeLine(n1.geom, n2.geom) AS geom,
        ABS(n1.boundary_position - n2.boundary_position) AS position_diff,
        -- Handle wrap-around at 0-1 boundary
        CASE 
            WHEN ABS(n1.boundary_position - n2.boundary_position) > 0.9 
            THEN 1.0 - ABS(n1.boundary_position - n2.boundary_position)
            ELSE ABS(n1.boundary_position - n2.boundary_position)
        END AS adjusted_position_diff,
        -- Rank nodes by their position along the boundary
        ROW_NUMBER() OVER (
            PARTITION BY n1.node_id 
            ORDER BY 
                CASE 
                    WHEN ABS(n1.boundary_position - n2.boundary_position) > 0.9 
                    THEN 1.0 - ABS(n1.boundary_position - n2.boundary_position)
                    ELSE ABS(n1.boundary_position - n2.boundary_position)
                END
        ) AS position_rank
    FROM
        ordered_nodes n1
    JOIN
        ordered_nodes n2 ON n1.water_obstacle_id = n2.water_obstacle_id
        AND ST_DWithin(n1.geom, n2.geom, :boundary_edge_max_length)
    WHERE
        n1.node_id < n2.node_id
)
SELECT
    source_id,
    target_id,
    length,
    length / (5.0 * :water_speed_factor) AS cost, -- Slower speed along water boundaries
    'water_boundary' AS edge_type,
    geom
FROM
    sequential_nodes
WHERE
    -- Keep only the closest 2 nodes in each direction along the boundary
    position_rank <= 2
    -- Additional filtering to ensure more even distribution
    AND (source_id % 3 != 0 OR adjusted_position_diff < 0.05)
    -- Ensure we're not creating edges that cross through water obstacles
    AND NOT EXISTS (
        SELECT 1
        FROM water_obstacles wo
        WHERE 
            wo.id != water_obstacle_id AND
            ST_Crosses(geom, wo.geom)
    );

-- Create spatial indexes
CREATE INDEX land_land_edges_geom_idx ON land_land_edges USING GIST (geom);
CREATE INDEX land_boundary_edges_geom_idx ON land_boundary_edges USING GIST (geom);
CREATE INDEX boundary_boundary_edges_geom_idx ON boundary_boundary_edges USING GIST (geom);
CREATE INDEX boundary_water_edges_geom_idx ON boundary_water_edges USING GIST (geom);
CREATE INDEX water_boundary_edges_geom_idx ON water_boundary_edges USING GIST (geom);
CREATE INDEX water_boundary_to_boundary_edges_geom_idx ON water_boundary_to_boundary_edges USING GIST (geom);
CREATE INDEX bridge_to_boundary_edges_geom_idx ON bridge_to_boundary_edges USING GIST (geom);

-- Log the results
SELECT 'Created ' || COUNT(*) || ' land-land edges' FROM land_land_edges;
SELECT 'Created ' || COUNT(*) || ' land-boundary edges' FROM land_boundary_edges;
SELECT 'Created ' || COUNT(*) || ' boundary-boundary edges' FROM boundary_boundary_edges;
SELECT 'Created ' || COUNT(*) || ' boundary-water edges' FROM boundary_water_edges;
SELECT 'Created ' || COUNT(*) || ' water-boundary edges' FROM water_boundary_edges;
SELECT 'Created ' || COUNT(*) || ' water-boundary-to-boundary edges' FROM water_boundary_to_boundary_edges;
SELECT 'Created ' || COUNT(*) || ' bridge-to-boundary edges' FROM bridge_to_boundary_edges;
