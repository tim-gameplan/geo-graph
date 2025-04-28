-- Test for ST_VoronoiPolygons with a small set of boundary points
-- This script simulates our actual use case but with a smaller number of points

-- Create a test table for water obstacles
DROP TABLE IF EXISTS test_water_obstacles;
CREATE TABLE test_water_obstacles (
    id SERIAL PRIMARY KEY,
    geom GEOMETRY(POLYGON, 3857)
);

-- Insert a simple water obstacle (a square)
INSERT INTO test_water_obstacles (geom)
VALUES (
    ST_SetSRID(
        ST_MakePolygon(
            ST_MakeLine(ARRAY[
                ST_MakePoint(0, 0),
                ST_MakePoint(100, 0),
                ST_MakePoint(100, 100),
                ST_MakePoint(0, 100),
                ST_MakePoint(0, 0)
            ])
        ),
        3857
    )
);

-- Create a table for boundary nodes
DROP TABLE IF EXISTS test_boundary_nodes;
CREATE TABLE test_boundary_nodes (
    node_id SERIAL PRIMARY KEY,
    water_obstacle_id INTEGER,
    point_order INTEGER,
    geom GEOMETRY(POINT, 3857)
);

-- Extract points along the boundary at regular intervals
INSERT INTO test_boundary_nodes (water_obstacle_id, point_order, geom)
SELECT 
    id AS water_obstacle_id,
    generate_series(1, 20) AS point_order,
    ST_PointN(
        ST_ExteriorRing(geom), 
        1 + (generate_series(1, 20) - 1) * (ST_NPoints(ST_ExteriorRing(geom)) - 1) / 20
    ) AS geom
FROM 
    test_water_obstacles;

-- Create a table for terrain grid points
DROP TABLE IF EXISTS test_terrain_grid_points;
CREATE TABLE test_terrain_grid_points (
    id SERIAL PRIMARY KEY,
    hex_type TEXT,
    geom GEOMETRY(POINT, 3857)
);

-- Insert a grid of terrain points
INSERT INTO test_terrain_grid_points (hex_type, geom)
SELECT 
    'land' AS hex_type,
    ST_SetSRID(ST_MakePoint(x, y), 3857) AS geom
FROM 
    generate_series(-100, 200, 50) AS x,
    generate_series(-100, 200, 50) AS y
WHERE 
    NOT (x BETWEEN 0 AND 100 AND y BETWEEN 0 AND 100);

-- Create a table for Voronoi cells
DROP TABLE IF EXISTS test_voronoi_cells;
CREATE TABLE test_voronoi_cells (
    node_id INTEGER PRIMARY KEY,
    cell_geom GEOMETRY(POLYGON, 3857)
);

-- Generate Voronoi diagram
DO $$
DECLARE
    points_collection GEOMETRY;
    voronoi_polygons GEOMETRY;
    study_area_envelope GEOMETRY;
BEGIN
    -- Create a collection of points
    SELECT ST_Collect(geom) INTO points_collection FROM test_boundary_nodes;
    
    -- Create a study area envelope with some padding
    SELECT ST_Envelope(ST_Buffer(ST_Extent(geom), 200)) INTO study_area_envelope 
    FROM test_boundary_nodes;
    
    -- Generate Voronoi polygons
    SELECT ST_VoronoiPolygons(
        points_collection,
        0.0, -- tolerance
        study_area_envelope -- envelope to clip the result
    ) INTO voronoi_polygons;
    
    -- Insert the Voronoi polygons into the test_voronoi_cells table
    WITH voronoi_dump AS (
        SELECT 
            (ST_Dump(voronoi_polygons)).geom AS cell_geom
    ),
    nearest_nodes AS (
        SELECT 
            vd.cell_geom,
            (
                SELECT node_id
                FROM test_boundary_nodes
                ORDER BY ST_Distance(geom, ST_PointOnSurface(vd.cell_geom))
                LIMIT 1
            ) AS node_id
        FROM 
            voronoi_dump vd
    )
    INSERT INTO test_voronoi_cells (node_id, cell_geom)
    SELECT 
        node_id,
        cell_geom
    FROM 
        nearest_nodes;
    
    -- Log the results
    RAISE NOTICE 'Generated % Voronoi cells', (SELECT COUNT(*) FROM test_voronoi_cells);
END $$;

-- Create a table for connection edges
DROP TABLE IF EXISTS test_connection_edges;
CREATE TABLE test_connection_edges (
    edge_id SERIAL PRIMARY KEY,
    source_id INTEGER,
    target_id INTEGER,
    geom GEOMETRY(LINESTRING, 3857),
    cost FLOAT
);

-- Find terrain points that fall within each Voronoi cell
INSERT INTO test_connection_edges (source_id, target_id, geom, cost)
SELECT 
    tgp.id AS source_id,
    vc.node_id AS target_id,
    ST_MakeLine(
        tgp.geom,
        (SELECT geom FROM test_boundary_nodes WHERE node_id = vc.node_id)
    ) AS geom,
    ST_Distance(
        tgp.geom,
        (SELECT geom FROM test_boundary_nodes WHERE node_id = vc.node_id)
    ) AS cost
FROM 
    test_terrain_grid_points tgp
JOIN 
    test_voronoi_cells vc ON ST_Intersects(tgp.geom, vc.cell_geom)
WHERE 
    tgp.hex_type = 'land'
    -- Ensure the connection doesn't cross through water obstacles
    AND NOT EXISTS (
        SELECT 1
        FROM test_water_obstacles wo
        WHERE ST_Crosses(
            ST_MakeLine(
                tgp.geom,
                (SELECT geom FROM test_boundary_nodes WHERE node_id = vc.node_id)
            ),
            wo.geom
        )
    )
    -- Limit the distance
    AND ST_Distance(
        tgp.geom,
        (SELECT geom FROM test_boundary_nodes WHERE node_id = vc.node_id)
    ) <= 200;

-- Display the results
SELECT 'Number of boundary nodes: ' || COUNT(*) FROM test_boundary_nodes;
SELECT 'Number of terrain grid points: ' || COUNT(*) FROM test_terrain_grid_points;
SELECT 'Number of Voronoi cells: ' || COUNT(*) FROM test_voronoi_cells;
SELECT 'Number of connection edges: ' || COUNT(*) FROM test_connection_edges;

-- Verify that each Voronoi cell contains exactly one boundary node
SELECT 
    vc.node_id AS voronoi_id,
    COUNT(bn.node_id) AS node_count
FROM 
    test_voronoi_cells vc
LEFT JOIN 
    test_boundary_nodes bn ON ST_Contains(vc.cell_geom, bn.geom)
GROUP BY 
    vc.node_id
ORDER BY 
    vc.node_id;
