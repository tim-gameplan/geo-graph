-- Test for Reversed Voronoi Connection Strategy
-- This script creates Voronoi cells for boundary terrain nodes instead of boundary nodes

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

-- Create terrain grid with hexagons
DROP TABLE IF EXISTS test_terrain_grid;
CREATE TABLE test_terrain_grid (
    id SERIAL PRIMARY KEY,
    geom GEOMETRY(POLYGON, 3857),
    hex_type VARCHAR(10)
);

-- Insert a grid of hexagons
WITH hex_grid AS (
    SELECT 
        ST_SetSRID((ST_HexagonGrid(25, ST_Expand(ST_Extent(geom), 100))).geom, 3857) AS geom
    FROM 
        test_water_obstacles
)
INSERT INTO test_terrain_grid (geom, hex_type)
SELECT 
    hg.geom,
    CASE
        WHEN EXISTS (
            SELECT 1
            FROM test_water_obstacles wo
            WHERE ST_Contains(wo.geom, ST_Centroid(hg.geom))
        ) THEN 'water'
        WHEN EXISTS (
            SELECT 1
            FROM test_water_obstacles wo
            WHERE ST_Intersects(wo.geom, hg.geom)
        ) THEN 'boundary'
        ELSE 'land'
    END AS hex_type
FROM 
    hex_grid hg;

-- Create terrain grid points
DROP TABLE IF EXISTS test_terrain_grid_points;
CREATE TABLE test_terrain_grid_points (
    id SERIAL PRIMARY KEY,
    grid_id INTEGER REFERENCES test_terrain_grid(id),
    hex_type VARCHAR(10),
    geom GEOMETRY(POINT, 3857)
);

-- Insert centroids for all hexagons
INSERT INTO test_terrain_grid_points (grid_id, hex_type, geom)
SELECT 
    id,
    hex_type,
    ST_Centroid(geom)
FROM 
    test_terrain_grid;

-- Create boundary nodes along water obstacle boundaries
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
    -- Use ST_LineInterpolatePoint to get evenly spaced points along the boundary
    ST_LineInterpolatePoint(
        ST_ExteriorRing(geom),
        (generate_series(1, 20) - 1) / 20.0
    ) AS geom
FROM 
    test_water_obstacles;

-- Create Voronoi cells for boundary terrain points
DROP TABLE IF EXISTS test_reversed_voronoi_cells;
CREATE TABLE test_reversed_voronoi_cells (
    cell_id SERIAL PRIMARY KEY,
    terrain_point_id INTEGER,
    cell_geom GEOMETRY(POLYGON, 3857)
);

-- Generate Voronoi diagram for boundary terrain points
DO $$
DECLARE
    points_collection GEOMETRY;
    voronoi_polygons GEOMETRY;
    study_area_envelope GEOMETRY;
    boundary_count INTEGER;
BEGIN
    -- Count boundary terrain points
    SELECT COUNT(*) INTO boundary_count 
    FROM test_terrain_grid_points 
    WHERE hex_type = 'boundary';
    
    RAISE NOTICE 'Found % boundary terrain points', boundary_count;
    
    -- Create a collection of boundary terrain points
    SELECT ST_Collect(geom) INTO points_collection 
    FROM test_terrain_grid_points 
    WHERE hex_type = 'boundary';
    
    -- Create a study area envelope with some padding
    SELECT ST_Envelope(ST_Buffer(ST_Extent(geom), 200)) INTO study_area_envelope 
    FROM test_terrain_grid_points;
    
    -- Generate Voronoi polygons
    SELECT ST_VoronoiPolygons(
        points_collection,
        0.0, -- tolerance
        study_area_envelope -- envelope to clip the result
    ) INTO voronoi_polygons;
    
    RAISE NOTICE 'Generated Voronoi polygons';
    
    -- Insert the Voronoi polygons into the test_reversed_voronoi_cells table
    WITH voronoi_dump AS (
        SELECT 
            (ST_Dump(voronoi_polygons)).geom AS cell_geom
    ),
    nearest_terrain_points AS (
        SELECT 
            vd.cell_geom,
            (
                SELECT id
                FROM test_terrain_grid_points
                WHERE hex_type = 'boundary'
                ORDER BY ST_Distance(geom, ST_PointOnSurface(vd.cell_geom))
                LIMIT 1
            ) AS terrain_point_id
        FROM 
            voronoi_dump vd
    )
    INSERT INTO test_reversed_voronoi_cells (terrain_point_id, cell_geom)
    SELECT 
        terrain_point_id,
        cell_geom
    FROM 
        nearest_terrain_points;
    
    RAISE NOTICE 'Inserted Voronoi cells';
END $$;

-- Create connection edges
DROP TABLE IF EXISTS test_reversed_connection_edges;
CREATE TABLE test_reversed_connection_edges (
    edge_id SERIAL PRIMARY KEY,
    terrain_point_id INTEGER,
    boundary_node_id INTEGER,
    geom GEOMETRY(LINESTRING, 3857),
    cost FLOAT
);

-- Find boundary nodes that fall within each Voronoi cell
INSERT INTO test_reversed_connection_edges (terrain_point_id, boundary_node_id, geom, cost)
SELECT 
    vc.terrain_point_id,
    bn.node_id,
    ST_MakeLine(
        (SELECT geom FROM test_terrain_grid_points WHERE id = vc.terrain_point_id),
        bn.geom
    ) AS geom,
    ST_Distance(
        (SELECT geom FROM test_terrain_grid_points WHERE id = vc.terrain_point_id),
        bn.geom
    ) AS cost
FROM 
    test_reversed_voronoi_cells vc
JOIN 
    test_boundary_nodes bn ON ST_Intersects(vc.cell_geom, bn.geom)
WHERE 
    -- Ensure the connection doesn't cross through water obstacles
    NOT EXISTS (
        SELECT 1
        FROM test_water_obstacles wo
        WHERE ST_Crosses(
            ST_MakeLine(
                (SELECT geom FROM test_terrain_grid_points WHERE id = vc.terrain_point_id),
                bn.geom
            ),
            wo.geom
        )
    )
    -- Limit the distance
    AND ST_Distance(
        (SELECT geom FROM test_terrain_grid_points WHERE id = vc.terrain_point_id),
        bn.geom
    ) <= 200;

-- Display the results
SELECT 'Number of boundary terrain points: ' || COUNT(*) FROM test_terrain_grid_points WHERE hex_type = 'boundary';
SELECT 'Number of boundary nodes: ' || COUNT(*) FROM test_boundary_nodes;
SELECT 'Number of Voronoi cells: ' || COUNT(*) FROM test_reversed_voronoi_cells;
SELECT 'Number of connection edges: ' || COUNT(*) FROM test_reversed_connection_edges;

-- Count how many boundary nodes are assigned to each terrain point
SELECT 
    terrain_point_id,
    COUNT(*) AS node_count
FROM 
    test_reversed_connection_edges
GROUP BY 
    terrain_point_id
ORDER BY 
    terrain_point_id;

-- Visualize the results (optional)
SELECT 
    'Boundary Terrain Points' AS layer,
    id::TEXT AS id,
    geom
FROM 
    test_terrain_grid_points
WHERE 
    hex_type = 'boundary'
UNION ALL
SELECT 
    'Boundary Nodes' AS layer,
    node_id::TEXT AS id,
    geom
FROM 
    test_boundary_nodes
UNION ALL
SELECT 
    'Voronoi Cells' AS layer,
    cell_id::TEXT AS id,
    ST_Boundary(cell_geom) AS geom
FROM 
    test_reversed_voronoi_cells
UNION ALL
SELECT 
    'Connection Edges' AS layer,
    edge_id::TEXT AS id,
    geom
FROM 
    test_reversed_connection_edges;
