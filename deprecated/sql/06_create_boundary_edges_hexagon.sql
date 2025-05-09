/*
 * 06_create_boundary_edges_hexagon.sql
 * 
 * Create boundary edges for the boundary hexagon layer approach
 * This script creates:
 * 1. Boundary-to-boundary edges (connecting boundary nodes to each other)
 * 2. Boundary-to-land-portion edges (connecting boundary nodes to land portion nodes)
 * 3. Land-portion-to-water-boundary edges (connecting land portion nodes to water boundary nodes)
 * 4. Water-boundary-to-water-boundary edges (connecting water boundary nodes to form the water obstacle graph)
 * 5. Boundary-to-water-boundary edges (connecting boundary nodes directly to water boundary nodes)
 */

-- Drop existing tables if they exist
DROP TABLE IF EXISTS boundary_boundary_edges CASCADE;
DROP TABLE IF EXISTS boundary_land_portion_edges CASCADE;
DROP TABLE IF EXISTS land_portion_water_boundary_edges CASCADE;
DROP TABLE IF EXISTS water_boundary_water_boundary_edges CASCADE;
DROP TABLE IF EXISTS boundary_water_boundary_edges CASCADE;
DROP TABLE IF EXISTS land_portion_land_edges CASCADE;
DROP TABLE IF EXISTS all_boundary_edges CASCADE;

-- Create boundary-to-boundary edges table
CREATE TABLE boundary_boundary_edges (
    id SERIAL PRIMARY KEY,
    start_node_id INTEGER,
    end_node_id INTEGER,
    geom GEOMETRY(LINESTRING, :storage_srid),
    length DOUBLE PRECISION,
    cost DOUBLE PRECISION
);

-- Create boundary-to-land-portion edges table
CREATE TABLE boundary_land_portion_edges (
    id SERIAL PRIMARY KEY,
    start_node_id INTEGER,
    end_node_id INTEGER,
    geom GEOMETRY(LINESTRING, :storage_srid),
    length DOUBLE PRECISION,
    cost DOUBLE PRECISION
);

-- Create land-portion-to-water-boundary edges table
CREATE TABLE land_portion_water_boundary_edges (
    id SERIAL PRIMARY KEY,
    start_node_id INTEGER,
    end_node_id INTEGER,
    geom GEOMETRY(LINESTRING, :storage_srid),
    length DOUBLE PRECISION,
    cost DOUBLE PRECISION
);

-- Create water-boundary-to-water-boundary edges table
CREATE TABLE water_boundary_water_boundary_edges (
    id SERIAL PRIMARY KEY,
    start_node_id INTEGER,
    end_node_id INTEGER,
    geom GEOMETRY(LINESTRING, :storage_srid),
    length DOUBLE PRECISION,
    cost DOUBLE PRECISION
);

-- Create boundary-to-water-boundary edges table
CREATE TABLE boundary_water_boundary_edges (
    id SERIAL PRIMARY KEY,
    start_node_id INTEGER,
    end_node_id INTEGER,
    geom GEOMETRY(LINESTRING, :storage_srid),
    length DOUBLE PRECISION,
    cost DOUBLE PRECISION
);

-- Create land-portion-to-land edges table
CREATE TABLE land_portion_land_edges (
    id SERIAL PRIMARY KEY,
    start_node_id INTEGER,
    end_node_id INTEGER,
    geom GEOMETRY(LINESTRING, :storage_srid),
    length DOUBLE PRECISION,
    cost DOUBLE PRECISION
);

-- Create all boundary edges table
CREATE TABLE all_boundary_edges (
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
INSERT INTO boundary_boundary_edges (start_node_id, end_node_id, geom, length, cost)
SELECT 
    b1.id AS start_node_id,
    b2.id AS end_node_id,
    ST_MakeLine(b1.geom, b2.geom) AS geom,
    ST_Length(ST_MakeLine(b1.geom, b2.geom)) AS length,
    ST_Length(ST_MakeLine(b1.geom, b2.geom)) AS cost
FROM 
    boundary_nodes b1
JOIN 
    boundary_nodes b2 ON b1.id < b2.id
WHERE 
    ST_DWithin(b1.geom, b2.geom, :boundary_edge_max_length)
    -- Ensure the edge doesn't cross through water obstacles
    AND NOT EXISTS (
        SELECT 1
        FROM water_obstacles wo
        WHERE ST_Intersects(ST_MakeLine(b1.geom, b2.geom), wo.geom)
            AND NOT ST_Intersects(ST_Buffer(b1.geom, 1), wo.geom)
            AND NOT ST_Intersects(ST_Buffer(b2.geom, 1), wo.geom)
    );

-- Create boundary-to-land-portion edges
-- Connect boundary nodes to land portion nodes within a certain distance
INSERT INTO boundary_land_portion_edges (start_node_id, end_node_id, geom, length, cost)
SELECT 
    b.id AS start_node_id,
    lp.id AS end_node_id,
    ST_MakeLine(b.geom, lp.geom) AS geom,
    ST_Length(ST_MakeLine(b.geom, lp.geom)) AS length,
    ST_Length(ST_MakeLine(b.geom, lp.geom)) AS cost
FROM 
    boundary_nodes b
JOIN 
    land_portion_nodes lp ON ST_DWithin(b.geom, lp.geom, :boundary_edge_max_length)
WHERE 
    -- Ensure the edge doesn't cross through water obstacles
    NOT EXISTS (
        SELECT 1
        FROM water_obstacles wo
        WHERE ST_Intersects(ST_MakeLine(b.geom, lp.geom), wo.geom)
            AND NOT ST_Intersects(ST_Buffer(b.geom, 1), wo.geom)
            AND NOT ST_Intersects(ST_Buffer(lp.geom, 1), wo.geom)
    );

-- Create land-portion-to-water-boundary edges
-- Connect land portion nodes to water boundary nodes within a certain distance
INSERT INTO land_portion_water_boundary_edges (start_node_id, end_node_id, geom, length, cost)
SELECT 
    lp.id AS start_node_id,
    wb.id AS end_node_id,
    ST_MakeLine(lp.geom, wb.geom) AS geom,
    ST_Length(ST_MakeLine(lp.geom, wb.geom)) AS length,
    ST_Length(ST_MakeLine(lp.geom, wb.geom)) * :water_speed_factor AS cost
FROM 
    land_portion_nodes lp
JOIN 
    water_boundary_nodes wb ON ST_DWithin(lp.geom, wb.geom, :boundary_edge_max_length)
WHERE 
    -- Limit the number of connections per land portion node
    wb.id IN (
        SELECT wb2.id
        FROM water_boundary_nodes wb2
        WHERE ST_DWithin(lp.geom, wb2.geom, :boundary_edge_max_length)
        ORDER BY ST_Distance(lp.geom, wb2.geom)
        LIMIT :max_connections_per_direction
    );

-- Create water-boundary-to-water-boundary edges
-- Connect water boundary nodes to adjacent nodes along the water obstacle boundary
-- This creates a chain of nodes that follows the water boundary, rather than connecting all nodes to each other
INSERT INTO water_boundary_water_boundary_edges (start_node_id, end_node_id, geom, length, cost)
WITH water_boundaries AS (
    -- Get all water obstacle boundaries
    SELECT 
        ST_Boundary(geom) AS boundary_geom
    FROM 
        water_obstacles
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
        water_boundary_nodes wb
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
        ROW_NUMBER() OVER (PARTITION BY line_geom ORDER BY line_position) AS position_rank
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
INSERT INTO boundary_water_boundary_edges (start_node_id, end_node_id, geom, length, cost)
SELECT 
    b.id AS start_node_id,
    wb.id AS end_node_id,
    ST_MakeLine(b.geom, wb.geom) AS geom,
    ST_Length(ST_MakeLine(b.geom, wb.geom)) AS length,
    ST_Length(ST_MakeLine(b.geom, wb.geom)) * :water_speed_factor AS cost
FROM 
    boundary_nodes b
JOIN 
    water_boundary_nodes wb ON ST_DWithin(b.geom, wb.geom, :boundary_edge_max_length)
WHERE 
    -- Limit the number of connections per boundary node
    wb.id IN (
        SELECT wb2.id
        FROM water_boundary_nodes wb2
        WHERE ST_DWithin(b.geom, wb2.geom, :boundary_edge_max_length)
        ORDER BY ST_Distance(b.geom, wb2.geom)
        LIMIT :max_connections_per_direction
    )
    -- Ensure the edge doesn't cross through water obstacles
    AND NOT EXISTS (
        SELECT 1
        FROM water_obstacles wo
        WHERE ST_Intersects(ST_MakeLine(b.geom, wb.geom), wo.geom)
            AND NOT ST_Intersects(ST_Buffer(b.geom, 1), wo.geom)
            AND NOT ST_Intersects(ST_Buffer(wb.geom, 1), wo.geom)
    );

-- Create land-portion-to-land-portion edges
-- Connect land portion nodes to other land portion nodes
INSERT INTO land_portion_land_edges (start_node_id, end_node_id, geom, length, cost)
SELECT
    lp1.id AS start_node_id,
    lp2.id AS end_node_id,
    ST_MakeLine(lp1.geom, lp2.geom) AS geom,
    ST_Length(ST_MakeLine(lp1.geom, lp2.geom)) AS length,
    ST_Length(ST_MakeLine(lp1.geom, lp2.geom)) / (5.0 * :land_speed_factor) AS cost
FROM
    land_portion_nodes lp1
JOIN
    land_portion_nodes lp2 ON ST_DWithin(lp1.geom, lp2.geom, :max_land_portion_connection_distance)
WHERE
    lp1.id < lp2.id
    AND (lp1.id % :land_portion_connection_modulo) = 0
    AND NOT EXISTS (
        SELECT 1
        FROM water_obstacles wo
        WHERE ST_Intersects(ST_MakeLine(lp1.geom, lp2.geom), wo.geom)
            AND NOT ST_Intersects(ST_Buffer(lp1.geom, 1), wo.geom)
            AND NOT ST_Intersects(ST_Buffer(lp2.geom, 1), wo.geom)
    );

-- Create land-portion-to-land edges
-- Connect land portion nodes to land or boundary nodes
INSERT INTO land_portion_land_edges (start_node_id, end_node_id, geom, length, cost)
SELECT
    lp.id AS start_node_id,
    t.id AS end_node_id,
    ST_MakeLine(lp.geom, t.geom) AS geom,
    ST_Length(ST_MakeLine(lp.geom, t.geom)) AS length,
    ST_Length(ST_MakeLine(lp.geom, t.geom)) AS cost
FROM
    land_portion_nodes lp
JOIN
    terrain_grid_points t ON t.hex_type IN ('land', 'boundary')
WHERE
    ST_DWithin(lp.geom, t.geom, :boundary_edge_max_length)
    -- Ensure the edge doesn't cross through water obstacles
    AND NOT EXISTS (
        SELECT 1
        FROM water_obstacles wo
        WHERE ST_Intersects(ST_MakeLine(lp.geom, t.geom), wo.geom)
            AND NOT ST_Intersects(ST_Buffer(lp.geom, 1), wo.geom)
            AND NOT ST_Intersects(ST_Buffer(t.geom, 1), wo.geom)
    )
    -- Limit to the closest land/boundary nodes for each land portion node
    AND t.id IN (
        SELECT t2.id
        FROM terrain_grid_points t2
        WHERE t2.hex_type IN ('land', 'boundary')
          AND ST_DWithin(lp.geom, t2.geom, :boundary_edge_max_length)
        ORDER BY ST_Distance(lp.geom, t2.geom)
        LIMIT :max_connections_per_direction
    );

-- Combine all edges into a single table
INSERT INTO all_boundary_edges (start_node_id, end_node_id, start_node_type, end_node_type, geom, length, cost)
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
    boundary_boundary_edges e
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
    boundary_land_portion_edges e
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
    land_portion_water_boundary_edges e
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
    water_boundary_water_boundary_edges e
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
    boundary_water_boundary_edges e
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
    land_portion_land_edges e
WHERE
    EXISTS (
        SELECT 1
        FROM terrain_grid_points t
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
    land_portion_land_edges e
WHERE
    EXISTS (
        SELECT 1
        FROM land_portion_nodes lp
        WHERE lp.id = e.end_node_id
    );

-- Create spatial indexes
CREATE INDEX boundary_boundary_edges_geom_idx ON boundary_boundary_edges USING GIST (geom);
CREATE INDEX boundary_land_portion_edges_geom_idx ON boundary_land_portion_edges USING GIST (geom);
CREATE INDEX land_portion_water_boundary_edges_geom_idx ON land_portion_water_boundary_edges USING GIST (geom);
CREATE INDEX water_boundary_water_boundary_edges_geom_idx ON water_boundary_water_boundary_edges USING GIST (geom);
CREATE INDEX boundary_water_boundary_edges_geom_idx ON boundary_water_boundary_edges USING GIST (geom);
CREATE INDEX land_portion_land_edges_geom_idx ON land_portion_land_edges USING GIST (geom);
CREATE INDEX all_boundary_edges_geom_idx ON all_boundary_edges USING GIST (geom);

-- Log the results
SELECT 'Created ' || COUNT(*) || ' boundary-to-boundary edges' FROM boundary_boundary_edges;
SELECT 'Created ' || COUNT(*) || ' boundary-to-land-portion edges' FROM boundary_land_portion_edges;
SELECT 'Created ' || COUNT(*) || ' land-portion-to-water-boundary edges' FROM land_portion_water_boundary_edges;
SELECT 'Created ' || COUNT(*) || ' water-boundary-to-water-boundary edges' FROM water_boundary_water_boundary_edges;
SELECT 'Created ' || COUNT(*) || ' boundary-to-water-boundary edges' FROM boundary_water_boundary_edges;
SELECT 'Created ' || COUNT(*) || ' land-portion-to-land edges' FROM land_portion_land_edges;
SELECT 'Created ' || COUNT(*) || ' total boundary edges' FROM all_boundary_edges;
