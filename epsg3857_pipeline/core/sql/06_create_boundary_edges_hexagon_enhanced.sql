/*
 * 06_create_boundary_edges_hexagon_enhanced.sql
 * 
 * Enhanced version of the boundary edges creation script for the boundary hexagon layer approach
 * This script creates:
 * 1. Boundary-to-boundary edges (connecting boundary nodes to each other)
 * 2. Boundary-to-land-portion edges (connecting boundary nodes to land portion nodes)
 * 3. Land-portion-to-water-boundary edges (connecting land portion nodes to water boundary nodes)
 * 4. Water-boundary-to-water-boundary edges (connecting water boundary nodes to form the water obstacle graph)
 * 5. Boundary-to-water-boundary edges (connecting boundary nodes directly to water boundary nodes)
 * 6. Land-portion-to-land edges (connecting land portion nodes to land nodes)
 * 
 * ENHANCEMENT: Improved land-portion-to-land/boundary connections to ensure better connectivity
 */

-- Drop existing tables if they exist
DROP TABLE IF EXISTS s06_edges_boundary_boundary CASCADE;
DROP TABLE IF EXISTS s06_edges_boundary_land_portion CASCADE;
DROP TABLE IF EXISTS s06_edges_land_portion_water_boundary CASCADE;
DROP TABLE IF EXISTS s06_edges_water_boundary_water_boundary CASCADE;
DROP TABLE IF EXISTS s06_edges_boundary_water_boundary CASCADE;
DROP TABLE IF EXISTS s06_edges_land_portion_land CASCADE;
DROP TABLE IF EXISTS s06_edges_all_boundary CASCADE;

-- Create boundary-to-boundary edges table
CREATE TABLE s06_edges_boundary_boundary (
    id SERIAL PRIMARY KEY,
    start_node_id INTEGER,
    end_node_id INTEGER,
    geom GEOMETRY(LINESTRING, :storage_srid),
    length DOUBLE PRECISION,
    cost DOUBLE PRECISION
);

-- Create boundary-to-land-portion edges table
CREATE TABLE s06_edges_boundary_land_portion (
    id SERIAL PRIMARY KEY,
    start_node_id INTEGER,
    end_node_id INTEGER,
    geom GEOMETRY(LINESTRING, :storage_srid),
    length DOUBLE PRECISION,
    cost DOUBLE PRECISION
);

-- Create land-portion-to-water-boundary edges table
CREATE TABLE s06_edges_land_portion_water_boundary (
    id SERIAL PRIMARY KEY,
    start_node_id INTEGER,
    end_node_id INTEGER,
    geom GEOMETRY(LINESTRING, :storage_srid),
    length DOUBLE PRECISION,
    cost DOUBLE PRECISION
);

-- Create water-boundary-to-water-boundary edges table
CREATE TABLE s06_edges_water_boundary_water_boundary (
    id SERIAL PRIMARY KEY,
    start_node_id INTEGER,
    end_node_id INTEGER,
    geom GEOMETRY(LINESTRING, :storage_srid),
    length DOUBLE PRECISION,
    cost DOUBLE PRECISION
);

-- Create boundary-to-water-boundary edges table
CREATE TABLE s06_edges_boundary_water_boundary (
    id SERIAL PRIMARY KEY,
    start_node_id INTEGER,
    end_node_id INTEGER,
    geom GEOMETRY(LINESTRING, :storage_srid),
    length DOUBLE PRECISION,
    cost DOUBLE PRECISION
);

-- Create land-portion-to-land edges table
CREATE TABLE s06_edges_land_portion_land (
    id SERIAL PRIMARY KEY,
    start_node_id INTEGER,
    end_node_id INTEGER,
    geom GEOMETRY(LINESTRING, :storage_srid),
    length DOUBLE PRECISION,
    cost DOUBLE PRECISION
);

-- Create all boundary edges table
CREATE TABLE s06_edges_all_boundary (
    id SERIAL PRIMARY KEY,
    start_node_id INTEGER,
    end_node_id INTEGER,
    start_node_type VARCHAR(20),
    end_node_type VARCHAR(20),
    geom GEOMETRY(LINESTRING, :storage_srid),
    length DOUBLE PRECISION,
    cost DOUBLE PRECISION
);

-- Create boundary-to-boundary edges
-- Connect boundary nodes to other boundary nodes within a certain distance
INSERT INTO s06_edges_boundary_boundary (start_node_id, end_node_id, geom, length, cost)
SELECT 
    b1.id AS start_node_id,
    b2.id AS end_node_id,
    ST_MakeLine(b1.geom, b2.geom) AS geom,
    ST_Length(ST_MakeLine(b1.geom, b2.geom)) AS length,
    ST_Length(ST_MakeLine(b1.geom, b2.geom)) AS cost
FROM 
    s05_nodes_boundary b1
JOIN 
    s05_nodes_boundary b2 ON b1.id < b2.id
WHERE 
    ST_DWithin(b1.geom, b2.geom, :boundary_edge_max_length)
    -- Ensure the edge doesn't cross through water obstacles
    AND NOT EXISTS (
        SELECT 1
        FROM s03_water_obstacles wo
        WHERE ST_Intersects(ST_MakeLine(b1.geom, b2.geom), wo.geom)
            AND NOT ST_Intersects(ST_Buffer(b1.geom, 1), wo.geom)
            AND NOT ST_Intersects(ST_Buffer(b2.geom, 1), wo.geom)
    );

-- Create boundary-to-land-portion edges
-- Connect boundary nodes to land portion nodes within a certain distance
INSERT INTO s06_edges_boundary_land_portion (start_node_id, end_node_id, geom, length, cost)
SELECT 
    b.id AS start_node_id,
    lp.id AS end_node_id,
    ST_MakeLine(b.geom, lp.geom) AS geom,
    ST_Length(ST_MakeLine(b.geom, lp.geom)) AS length,
    ST_Length(ST_MakeLine(b.geom, lp.geom)) AS cost
FROM 
    s05_nodes_boundary b
JOIN 
    s05_nodes_land_portion lp ON ST_DWithin(b.geom, lp.geom, :boundary_edge_max_length)
WHERE 
    -- Ensure the edge doesn't cross through water obstacles
    NOT EXISTS (
        SELECT 1
        FROM s03_water_obstacles wo
        WHERE ST_Intersects(ST_MakeLine(b.geom, lp.geom), wo.geom)
            AND NOT ST_Intersects(ST_Buffer(b.geom, 1), wo.geom)
            AND NOT ST_Intersects(ST_Buffer(lp.geom, 1), wo.geom)
    );

-- Create land-portion-to-water-boundary edges
-- Connect land portion nodes to water boundary nodes within a certain distance
INSERT INTO s06_edges_land_portion_water_boundary (start_node_id, end_node_id, geom, length, cost)
SELECT 
    lp.id AS start_node_id,
    wb.id AS end_node_id,
    ST_MakeLine(lp.geom, wb.geom) AS geom,
    ST_Length(ST_MakeLine(lp.geom, wb.geom)) AS length,
    ST_Length(ST_MakeLine(lp.geom, wb.geom)) * :water_speed_factor AS cost
FROM 
    s05_nodes_land_portion lp
JOIN 
    s05_nodes_water_boundary wb ON ST_DWithin(lp.geom, wb.geom, :boundary_edge_max_length)
WHERE 
    -- Limit the number of connections per land portion node
    wb.id IN (
        SELECT wb2.id
        FROM s05_nodes_water_boundary wb2
        WHERE ST_DWithin(lp.geom, wb2.geom, :boundary_edge_max_length)
        ORDER BY ST_Distance(lp.geom, wb2.geom)
        LIMIT :max_connections_per_direction
    );

-- Create water-boundary-to-water-boundary edges
-- Connect water boundary nodes to adjacent nodes along the water obstacle boundary
-- This creates a chain of nodes that follows the water boundary, rather than connecting all nodes to each other
INSERT INTO s06_edges_water_boundary_water_boundary (start_node_id, end_node_id, geom, length, cost)
WITH water_boundaries AS (
    -- Get all water obstacle boundaries
    SELECT 
        ST_Boundary(geom) AS boundary_geom
    FROM 
        s03_water_obstacles
),
boundary_lines AS (
    -- Convert boundaries to linestrings
    SELECT 
        (ST_Dump(boundary_geom)).geom AS line_geom
    FROM 
        water_boundaries
    WHERE 
        ST_GeometryType(boundary_geom) IN ('ST_MultiLineString', 'ST_LineString')
),
boundary_points AS (
    -- Get all water boundary nodes with their position along each boundary line
    SELECT 
        wb.id,
        wb.geom,
        bl.line_geom,
        ST_LineLocatePoint(bl.line_geom, wb.geom) AS line_position
    FROM 
        s05_nodes_water_boundary wb
    CROSS JOIN 
        boundary_lines bl
    WHERE 
        ST_DWithin(wb.geom, bl.line_geom, 1)
),
ordered_points AS (
    -- Order points along each boundary line
    SELECT 
        id,
        geom,
        line_geom,
        line_position,
        ROW_NUMBER() OVER (PARTITION BY line_geom ORDER BY line_position) AS position_rank,
        COUNT(*) OVER (PARTITION BY line_geom) AS total_points
    FROM 
        boundary_points
),
adjacent_points AS (
    -- Connect each point to the next point along the boundary
    SELECT 
        op1.id AS start_id,
        op2.id AS end_id,
        op1.geom AS start_geom,
        op2.geom AS end_geom,
        ST_MakeLine(op1.geom, op2.geom) AS edge_geom
    FROM 
        ordered_points op1
    JOIN 
        ordered_points op2 ON op1.line_geom = op2.line_geom AND op1.position_rank + 1 = op2.position_rank
    WHERE 
        ST_DWithin(op1.geom, op2.geom, :boundary_edge_max_length)
    
    UNION ALL
    
    -- Connect the last point back to the first point to close the loop
    SELECT 
        op_last.id AS start_id,
        op_first.id AS end_id,
        op_last.geom AS start_geom,
        op_first.geom AS end_geom,
        ST_MakeLine(op_last.geom, op_first.geom) AS edge_geom
    FROM 
        ordered_points op_last
    JOIN 
        ordered_points op_first ON op_last.line_geom = op_first.line_geom 
                               AND op_last.position_rank = op_last.total_points 
                               AND op_first.position_rank = 1
    WHERE 
        ST_DWithin(op_last.geom, op_first.geom, :boundary_edge_max_length)
)
SELECT 
    start_id,
    end_id,
    edge_geom,
    ST_Length(edge_geom),
    ST_Length(edge_geom) * :water_speed_factor
FROM 
    adjacent_points;

-- Create boundary-to-water-boundary edges
-- Connect boundary nodes directly to water boundary nodes
INSERT INTO s06_edges_boundary_water_boundary (start_node_id, end_node_id, geom, length, cost)
SELECT 
    b.id AS start_node_id,
    wb.id AS end_node_id,
    ST_MakeLine(b.geom, wb.geom) AS geom,
    ST_Length(ST_MakeLine(b.geom, wb.geom)) AS length,
    ST_Length(ST_MakeLine(b.geom, wb.geom)) * :water_speed_factor AS cost
FROM 
    s05_nodes_boundary b
JOIN 
    s05_nodes_water_boundary wb ON ST_DWithin(b.geom, wb.geom, :boundary_edge_max_length)
WHERE 
    -- Limit the number of connections per boundary node
    wb.id IN (
        SELECT wb2.id
        FROM s05_nodes_water_boundary wb2
        WHERE ST_DWithin(b.geom, wb2.geom, :boundary_edge_max_length)
        ORDER BY ST_Distance(b.geom, wb2.geom)
        LIMIT :max_connections_per_direction
    )
    -- Ensure the edge doesn't cross through water obstacles
    AND NOT EXISTS (
        SELECT 1
        FROM s03_water_obstacles wo
        WHERE ST_Intersects(ST_MakeLine(b.geom, wb.geom), wo.geom)
            AND NOT ST_Intersects(ST_Buffer(b.geom, 1), wo.geom)
            AND NOT ST_Intersects(ST_Buffer(wb.geom, 1), wo.geom)
    );

-- Create land-portion-to-land-portion edges
-- Connect land portion nodes to other land portion nodes
INSERT INTO s06_edges_land_portion_land (start_node_id, end_node_id, geom, length, cost)
SELECT
    lp1.id AS start_node_id,
    lp2.id AS end_node_id,
    ST_MakeLine(lp1.geom, lp2.geom) AS geom,
    ST_Length(ST_MakeLine(lp1.geom, lp2.geom)) AS length,
    ST_Length(ST_MakeLine(lp1.geom, lp2.geom)) / (5.0 * :land_speed_factor) AS cost
FROM
    s05_nodes_land_portion lp1
JOIN
    s05_nodes_land_portion lp2 ON ST_DWithin(lp1.geom, lp2.geom, :max_land_portion_connection_distance)
WHERE
    lp1.id < lp2.id
    AND (lp1.id % :land_portion_connection_modulo) = 0
    AND NOT EXISTS (
        SELECT 1
        FROM s03_water_obstacles wo
        WHERE ST_Intersects(ST_MakeLine(lp1.geom, lp2.geom), wo.geom)
            AND NOT ST_Intersects(ST_Buffer(lp1.geom, 1), wo.geom)
            AND NOT ST_Intersects(ST_Buffer(lp2.geom, 1), wo.geom)
    );

-- ENHANCED: Create land-portion-to-land/boundary edges
-- Connect each land portion node to the closest land and boundary nodes
-- This ensures better connectivity between land portions and the rest of the terrain
INSERT INTO s06_edges_land_portion_land (start_node_id, end_node_id, geom, length, cost)
WITH land_boundary_nodes AS (
    -- Get all land and boundary nodes
    SELECT 
        id, 
        geom, 
        hex_type AS node_type
    FROM 
        s04_grid_terrain_points
    WHERE 
        hex_type IN ('land', 'boundary')
),
closest_nodes AS (
    -- For each land portion node, find the closest land and boundary nodes
    SELECT 
        lp.id AS land_portion_id,
        lb.id AS land_boundary_id,
        lb.node_type,
        ST_Distance(lp.geom, lb.geom) AS distance,
        ST_MakeLine(lp.geom, lb.geom) AS geom,
        -- Rank nodes by distance for each land portion node
        ROW_NUMBER() OVER (PARTITION BY lp.id ORDER BY ST_Distance(lp.geom, lb.geom)) AS rank
    FROM 
        s05_nodes_land_portion lp
    CROSS JOIN 
        land_boundary_nodes lb
    WHERE 
        ST_DWithin(lp.geom, lb.geom, :boundary_edge_max_length * 2)
        -- Ensure the edge doesn't cross through water obstacles
        AND NOT EXISTS (
            SELECT 1
            FROM s03_water_obstacles wo
            WHERE ST_Intersects(ST_MakeLine(lp.geom, lb.geom), wo.geom)
                AND NOT ST_Intersects(ST_Buffer(lp.geom, 1), wo.geom)
                AND NOT ST_Intersects(ST_Buffer(lb.geom, 1), wo.geom)
        )
)
-- Select the top 5 closest land/boundary nodes for each land portion node
SELECT 
    land_portion_id AS start_node_id,
    land_boundary_id AS end_node_id,
    geom,
    distance AS length,
    distance AS cost
FROM 
    closest_nodes
WHERE 
    rank <= 5;  -- Connect to 5 closest land/boundary nodes instead of just 2

-- Combine all edges into a single table
INSERT INTO s06_edges_all_boundary (start_node_id, end_node_id, start_node_type, end_node_type, geom, length, cost)
-- Boundary-to-boundary edges
SELECT 
    e.start_node_id,
    e.end_node_id,
    'boundary' AS start_node_type,
    'boundary' AS end_node_type,
    e.geom,
    e.length,
    e.cost
FROM 
    s06_edges_boundary_boundary e
UNION ALL
-- Boundary-to-land-portion edges
SELECT 
    e.start_node_id,
    e.end_node_id,
    'boundary' AS start_node_type,
    'land_portion' AS end_node_type,
    e.geom,
    e.length,
    e.cost
FROM 
    s06_edges_boundary_land_portion e
UNION ALL
-- Land-portion-to-water-boundary edges
SELECT 
    e.start_node_id,
    e.end_node_id,
    'land_portion' AS start_node_type,
    'water_boundary' AS end_node_type,
    e.geom,
    e.length,
    e.cost
FROM 
    s06_edges_land_portion_water_boundary e
UNION ALL
-- Water-boundary-to-water-boundary edges
SELECT 
    e.start_node_id,
    e.end_node_id,
    'water_boundary' AS start_node_type,
    'water_boundary' AS end_node_type,
    e.geom,
    e.length,
    e.cost
FROM 
    s06_edges_water_boundary_water_boundary e
UNION ALL
-- Boundary-to-water-boundary edges
SELECT 
    e.start_node_id,
    e.end_node_id,
    'boundary' AS start_node_type,
    'water_boundary' AS end_node_type,
    e.geom,
    e.length,
    e.cost
FROM 
    s06_edges_boundary_water_boundary e
UNION ALL
-- Land-portion-to-land edges
SELECT
    e.start_node_id,
    e.end_node_id,
    'land_portion' AS start_node_type,
    'land' AS end_node_type,
    e.geom,
    e.length,
    e.cost
FROM
    s06_edges_land_portion_land e
WHERE
    EXISTS (
        SELECT 1
        FROM s04_grid_terrain_points t
        WHERE t.id = e.end_node_id AND t.hex_type IN ('land', 'boundary')
    )
UNION ALL
-- Land-portion-to-land-portion edges
SELECT
    e.start_node_id,
    e.end_node_id,
    'land_portion' AS start_node_type,
    'land_portion' AS end_node_type,
    e.geom,
    e.length,
    e.cost
FROM
    s06_edges_land_portion_land e
WHERE
    EXISTS (
        SELECT 1
        FROM s05_nodes_land_portion lp
        WHERE lp.id = e.end_node_id
    );

-- Create spatial indexes
CREATE INDEX boundary_boundary_edges_geom_idx ON s06_edges_boundary_boundary USING GIST (geom);
CREATE INDEX boundary_land_portion_edges_geom_idx ON s06_edges_boundary_land_portion USING GIST (geom);
CREATE INDEX land_portion_water_boundary_edges_geom_idx ON s06_edges_land_portion_water_boundary USING GIST (geom);
CREATE INDEX water_boundary_water_boundary_edges_geom_idx ON s06_edges_water_boundary_water_boundary USING GIST (geom);
CREATE INDEX boundary_water_boundary_edges_geom_idx ON s06_edges_boundary_water_boundary USING GIST (geom);
CREATE INDEX land_portion_land_edges_geom_idx ON s06_edges_land_portion_land USING GIST (geom);
CREATE INDEX all_boundary_edges_geom_idx ON s06_edges_all_boundary USING GIST (geom);

-- Log the results
SELECT 'Created ' || COUNT(*) || ' boundary-to-boundary edges' FROM s06_edges_boundary_boundary;
SELECT 'Created ' || COUNT(*) || ' boundary-to-land-portion edges' FROM s06_edges_boundary_land_portion;
SELECT 'Created ' || COUNT(*) || ' land-portion-to-water-boundary edges' FROM s06_edges_land_portion_water_boundary;
SELECT 'Created ' || COUNT(*) || ' water-boundary-to-water-boundary edges' FROM s06_edges_water_boundary_water_boundary;
SELECT 'Created ' || COUNT(*) || ' boundary-to-water-boundary edges' FROM s06_edges_boundary_water_boundary;
SELECT 'Created ' || COUNT(*) || ' land-portion-to-land edges' FROM s06_edges_land_portion_land;
SELECT 'Created ' || COUNT(*) || ' total boundary edges' FROM s06_edges_all_boundary;
