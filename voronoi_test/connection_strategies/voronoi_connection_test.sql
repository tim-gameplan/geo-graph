-- Voronoi Connection Test
-- This script tests different strategies for connecting terrain grid points to water obstacle boundaries.
-- It creates test data, implements each strategy, and collects metrics for comparison.

-- Set parameters
\set storage_srid 3857
\set buffer_distance 200
\set max_distance 500
\set voronoi_connection_limit 1
\set node_tolerance 10
\set random_seed 42

-- Enable timing
\timing on

-- Clean up any existing test tables
DROP TABLE IF EXISTS test_water_obstacles CASCADE;
DROP TABLE IF EXISTS test_terrain_points CASCADE;
DROP TABLE IF EXISTS test_boundary_nodes CASCADE;
DROP TABLE IF EXISTS nearest_neighbor_connections CASCADE;
DROP TABLE IF EXISTS buffer_based_voronoi_connections CASCADE;
DROP TABLE IF EXISTS true_voronoi_connections CASCADE;
DROP TABLE IF EXISTS reversed_voronoi_connections CASCADE;
DROP TABLE IF EXISTS connection_metrics CASCADE;

-- Create test tables
CREATE TABLE test_water_obstacles (
    id SERIAL PRIMARY KEY,
    geom GEOMETRY(POLYGON, :storage_srid)
);

CREATE TABLE test_terrain_points (
    id SERIAL PRIMARY KEY,
    hex_type TEXT, -- 'land', 'boundary', or 'water'
    geom GEOMETRY(POINT, :storage_srid)
);

CREATE TABLE test_boundary_nodes (
    id SERIAL PRIMARY KEY,
    water_obstacle_id INTEGER,
    geom GEOMETRY(POINT, :storage_srid)
);

-- Create tables for connection results
CREATE TABLE nearest_neighbor_connections (
    id SERIAL PRIMARY KEY,
    terrain_point_id INTEGER,
    boundary_node_id INTEGER,
    distance NUMERIC
);

CREATE TABLE buffer_based_voronoi_connections (
    id SERIAL PRIMARY KEY,
    terrain_point_id INTEGER,
    boundary_node_id INTEGER,
    distance NUMERIC,
    voronoi_cell GEOMETRY(POLYGON, :storage_srid)
);

CREATE TABLE true_voronoi_connections (
    id SERIAL PRIMARY KEY,
    terrain_point_id INTEGER,
    boundary_node_id INTEGER,
    distance NUMERIC,
    voronoi_cell GEOMETRY(POLYGON, :storage_srid)
);

CREATE TABLE reversed_voronoi_connections (
    id SERIAL PRIMARY KEY,
    terrain_point_id INTEGER,
    boundary_node_id INTEGER,
    distance NUMERIC,
    voronoi_cell GEOMETRY(POLYGON, :storage_srid)
);

-- Create table for metrics
CREATE TABLE connection_metrics (
    strategy TEXT PRIMARY KEY,
    connection_count INTEGER,
    avg_connection_length NUMERIC,
    execution_time_ms NUMERIC,
    evenness_score NUMERIC
);

-- Create spatial indexes
CREATE INDEX test_water_obstacles_geom_idx ON test_water_obstacles USING GIST (geom);
CREATE INDEX test_terrain_points_geom_idx ON test_terrain_points USING GIST (geom);
CREATE INDEX test_boundary_nodes_geom_idx ON test_boundary_nodes USING GIST (geom);

-- Generate test data
-- 1. Create water obstacles (simple polygons)
INSERT INTO test_water_obstacles (geom)
VALUES
    (ST_Buffer(ST_SetSRID(ST_MakePoint(0, 0), :storage_srid), 500)),
    (ST_Buffer(ST_SetSRID(ST_MakePoint(1500, 1000), :storage_srid), 300)),
    (ST_Buffer(ST_SetSRID(ST_MakePoint(-1000, 1000), :storage_srid), 400));

-- 2. Create terrain points (hexagonal grid)
WITH 
grid_extent AS (
    SELECT ST_Extent(ST_Buffer(geom, 1000)) AS extent
    FROM test_water_obstacles
),
hex_grid AS (
    SELECT (ST_HexagonGrid(200, extent)).*
    FROM grid_extent
)
INSERT INTO test_terrain_points (hex_type, geom)
SELECT
    CASE
        WHEN EXISTS (
            SELECT 1
            FROM test_water_obstacles wo
            WHERE ST_Contains(wo.geom, ST_Centroid(hg.geom))
        ) THEN 'water'
        WHEN EXISTS (
            SELECT 1
            FROM test_water_obstacles wo
            WHERE ST_Intersects(wo.geom, ST_Centroid(hg.geom))
            AND NOT ST_Contains(wo.geom, ST_Centroid(hg.geom))
        ) THEN 'boundary'
        ELSE 'land'
    END AS hex_type,
    ST_Centroid(hg.geom) AS geom
FROM
    hex_grid hg;

-- 3. Create boundary nodes (points along water obstacle boundaries)
INSERT INTO test_boundary_nodes (water_obstacle_id, geom)
SELECT
    wo.id AS water_obstacle_id,
    (ST_DumpPoints(ST_Boundary(ST_Segmentize(wo.geom, 100)))).geom AS geom
FROM
    test_water_obstacles wo;

-- Remove duplicate boundary nodes
DELETE FROM test_boundary_nodes
WHERE id IN (
    SELECT b1.id
    FROM test_boundary_nodes b1
    JOIN test_boundary_nodes b2
    ON ST_DWithin(b1.geom, b2.geom, 10)
    AND b1.id > b2.id
    AND b1.water_obstacle_id = b2.water_obstacle_id
);

-- Set random seed for reproducibility
SELECT setseed(:random_seed);

-- Strategy 1: Nearest Neighbor
-- Each terrain point connects to its nearest boundary node
DO $$
DECLARE
    start_time TIMESTAMPTZ;
    end_time TIMESTAMPTZ;
    execution_time_ms NUMERIC;
    connection_count INTEGER;
    avg_connection_length NUMERIC;
    evenness_score NUMERIC;
    std_dev NUMERIC;
    mean NUMERIC;
BEGIN
    start_time := clock_timestamp();
    
    -- Find the nearest boundary node for each terrain point
    INSERT INTO nearest_neighbor_connections (terrain_point_id, boundary_node_id, distance)
    SELECT 
        tgp.id AS terrain_point_id,
        (
            SELECT bn.id
            FROM test_boundary_nodes bn
            ORDER BY ST_Distance(tgp.geom, bn.geom)
            LIMIT 1
        ) AS boundary_node_id,
        ST_Distance(
            tgp.geom,
            (SELECT geom FROM test_boundary_nodes WHERE id = (
                SELECT bn.id
                FROM test_boundary_nodes bn
                ORDER BY ST_Distance(tgp.geom, bn.geom)
                LIMIT 1
            ))
        ) AS distance
    FROM 
        test_terrain_points tgp
    WHERE 
        tgp.hex_type = 'boundary'
        AND ST_Distance(
            tgp.geom,
            (SELECT geom FROM test_boundary_nodes WHERE id = (
                SELECT bn.id
                FROM test_boundary_nodes bn
                ORDER BY ST_Distance(tgp.geom, bn.geom)
                LIMIT 1
            ))
        ) <= :max_distance;
    
    end_time := clock_timestamp();
    execution_time_ms := EXTRACT(EPOCH FROM (end_time - start_time)) * 1000;
    
    -- Calculate metrics
    SELECT COUNT(*) INTO connection_count FROM nearest_neighbor_connections;
    SELECT AVG(distance) INTO avg_connection_length FROM nearest_neighbor_connections;
    
    -- Calculate evenness score
    WITH connection_counts AS (
        SELECT 
            boundary_node_id,
            COUNT(*) AS count
        FROM 
            nearest_neighbor_connections
        GROUP BY 
            boundary_node_id
    )
    SELECT 
        AVG(count) INTO mean
    FROM 
        connection_counts;
    
    WITH connection_counts AS (
        SELECT 
            boundary_node_id,
            COUNT(*) AS count
        FROM 
            nearest_neighbor_connections
        GROUP BY 
            boundary_node_id
    )
    SELECT 
        SQRT(AVG(POWER(count - mean, 2))) INTO std_dev
    FROM 
        connection_counts;
    
    evenness_score := 1 - (std_dev / NULLIF(mean, 0));
    
    -- Insert metrics
    INSERT INTO connection_metrics (strategy, connection_count, avg_connection_length, execution_time_ms, evenness_score)
    VALUES ('Nearest Neighbor', connection_count, avg_connection_length, execution_time_ms, evenness_score);
END $$;

-- Strategy 2: Buffer-Based Voronoi
-- Creates a "Voronoi-like" partitioning using buffers around boundary nodes
DO $$
DECLARE
    start_time TIMESTAMPTZ;
    end_time TIMESTAMPTZ;
    execution_time_ms NUMERIC;
    connection_count INTEGER;
    avg_connection_length NUMERIC;
    evenness_score NUMERIC;
    std_dev NUMERIC;
    mean NUMERIC;
BEGIN
    start_time := clock_timestamp();
    
    -- Create buffers around boundary nodes
    WITH boundary_node_buffers AS (
        SELECT 
            id,
            geom,
            ST_Buffer(geom, :buffer_distance) AS buffer_geom
        FROM 
            test_boundary_nodes
    )
    -- Find terrain points that fall within each buffer
    INSERT INTO buffer_based_voronoi_connections (terrain_point_id, boundary_node_id, distance, voronoi_cell)
    SELECT DISTINCT ON (tgp.id)
        tgp.id AS terrain_point_id,
        bnb.id AS boundary_node_id,
        ST_Distance(tgp.geom, bnb.geom) AS distance,
        bnb.buffer_geom AS voronoi_cell
    FROM 
        test_terrain_points tgp
    JOIN 
        boundary_node_buffers bnb
        ON ST_Intersects(tgp.geom, bnb.buffer_geom)
    WHERE 
        tgp.hex_type = 'boundary'
        AND ST_Distance(tgp.geom, bnb.geom) <= :max_distance
    ORDER BY
        tgp.id, ST_Distance(tgp.geom, bnb.geom);
    
    end_time := clock_timestamp();
    execution_time_ms := EXTRACT(EPOCH FROM (end_time - start_time)) * 1000;
    
    -- Calculate metrics
    SELECT COUNT(*) INTO connection_count FROM buffer_based_voronoi_connections;
    SELECT AVG(distance) INTO avg_connection_length FROM buffer_based_voronoi_connections;
    
    -- Calculate evenness score
    WITH connection_counts AS (
        SELECT 
            boundary_node_id,
            COUNT(*) AS count
        FROM 
            buffer_based_voronoi_connections
        GROUP BY 
            boundary_node_id
    )
    SELECT 
        AVG(count) INTO mean
    FROM 
        connection_counts;
    
    WITH connection_counts AS (
        SELECT 
            boundary_node_id,
            COUNT(*) AS count
        FROM 
            buffer_based_voronoi_connections
        GROUP BY 
            boundary_node_id
    )
    SELECT 
        SQRT(AVG(POWER(count - mean, 2))) INTO std_dev
    FROM 
        connection_counts;
    
    evenness_score := 1 - (std_dev / NULLIF(mean, 0));
    
    -- Insert metrics
    INSERT INTO connection_metrics (strategy, connection_count, avg_connection_length, execution_time_ms, evenness_score)
    VALUES ('Buffer-Based Voronoi', connection_count, avg_connection_length, execution_time_ms, evenness_score);
END $$;

-- Strategy 3: True Voronoi
-- Uses PostGIS's ST_VoronoiPolygons to create true Voronoi cells for boundary nodes
DO $$
DECLARE
    start_time TIMESTAMPTZ;
    end_time TIMESTAMPTZ;
    execution_time_ms NUMERIC;
    connection_count INTEGER;
    avg_connection_length NUMERIC;
    evenness_score NUMERIC;
    std_dev NUMERIC;
    mean NUMERIC;
BEGIN
    start_time := clock_timestamp();
    
    BEGIN
        -- Create Voronoi diagram for boundary nodes
        WITH voronoi_polygons AS (
            SELECT (ST_Dump(ST_VoronoiPolygons(ST_Collect(geom)))).geom AS cell_geom
            FROM test_boundary_nodes
        ),
        -- Associate each Voronoi cell with its boundary node
        voronoi_cells AS (
            SELECT 
                bn.id AS boundary_node_id,
                vp.cell_geom
            FROM 
                test_boundary_nodes bn
            JOIN 
                voronoi_polygons vp
                ON ST_Contains(vp.cell_geom, bn.geom)
        )
        -- Find terrain points that fall within each Voronoi cell
        INSERT INTO true_voronoi_connections (terrain_point_id, boundary_node_id, distance, voronoi_cell)
        SELECT 
            tgp.id AS terrain_point_id,
            vc.boundary_node_id,
            ST_Distance(tgp.geom, (SELECT geom FROM test_boundary_nodes WHERE id = vc.boundary_node_id)) AS distance,
            vc.cell_geom AS voronoi_cell
        FROM 
            test_terrain_points tgp
        JOIN 
            voronoi_cells vc
            ON ST_Intersects(tgp.geom, vc.cell_geom)
        WHERE 
            tgp.hex_type = 'boundary'
            AND ST_Distance(tgp.geom, (SELECT geom FROM test_boundary_nodes WHERE id = vc.boundary_node_id)) <= :max_distance;
    EXCEPTION
        WHEN OTHERS THEN
            -- If Voronoi diagram generation fails, fall back to buffer-based approach
            RAISE NOTICE 'True Voronoi diagram generation failed, falling back to buffer-based approach';
            
            -- Create buffers around boundary nodes
            WITH boundary_node_buffers AS (
                SELECT 
                    id,
                    geom,
                    ST_Buffer(geom, :buffer_distance) AS buffer_geom
                FROM 
                    test_boundary_nodes
            )
            -- Find terrain points that fall within each buffer
            INSERT INTO true_voronoi_connections (terrain_point_id, boundary_node_id, distance, voronoi_cell)
            SELECT DISTINCT ON (tgp.id)
                tgp.id AS terrain_point_id,
                bnb.id AS boundary_node_id,
                ST_Distance(tgp.geom, bnb.geom) AS distance,
                bnb.buffer_geom AS voronoi_cell
            FROM 
                test_terrain_points tgp
            JOIN 
                boundary_node_buffers bnb
                ON ST_Intersects(tgp.geom, bnb.buffer_geom)
            WHERE 
                tgp.hex_type = 'boundary'
                AND ST_Distance(tgp.geom, bnb.geom) <= :max_distance
            ORDER BY
                tgp.id, ST_Distance(tgp.geom, bnb.geom);
    END;
    
    end_time := clock_timestamp();
    execution_time_ms := EXTRACT(EPOCH FROM (end_time - start_time)) * 1000;
    
    -- Calculate metrics
    SELECT COUNT(*) INTO connection_count FROM true_voronoi_connections;
    SELECT AVG(distance) INTO avg_connection_length FROM true_voronoi_connections;
    
-- Calculate evenness score
    WITH connection_counts AS (
        SELECT 
            boundary_node_id,
            COUNT(*) AS count
        FROM 
            true_voronoi_connections
        GROUP BY 
            boundary_node_id
    )
    SELECT 
        AVG(count) INTO mean
    FROM 
        connection_counts;
    
    WITH connection_counts AS (
        SELECT 
            boundary_node_id,
            COUNT(*) AS count
        FROM 
            true_voronoi_connections
        GROUP BY 
            boundary_node_id
    )
    SELECT 
        SQRT(AVG(POWER(count - mean, 2))) INTO std_dev
    FROM 
        connection_counts;
    
    evenness_score := 1 - (std_dev / NULLIF(mean, 0));
    
    -- Insert metrics
    INSERT INTO connection_metrics (strategy, connection_count, avg_connection_length, execution_time_ms, evenness_score)
    VALUES ('True Voronoi', connection_count, avg_connection_length, execution_time_ms, evenness_score);
END $$;

-- Strategy 4: Reversed Voronoi
-- Creates Voronoi cells for boundary terrain points instead of boundary nodes
DO $$
DECLARE
    start_time TIMESTAMPTZ;
    end_time TIMESTAMPTZ;
    execution_time_ms NUMERIC;
    connection_count INTEGER;
    avg_connection_length NUMERIC;
    evenness_score NUMERIC;
    std_dev NUMERIC;
    mean NUMERIC;
BEGIN
    start_time := clock_timestamp();
    
    BEGIN
        -- Create Voronoi diagram for boundary terrain points
        WITH boundary_terrain_points AS (
            SELECT id, geom
            FROM test_terrain_points
            WHERE hex_type = 'boundary'
        ),
        voronoi_polygons AS (
            SELECT (ST_Dump(ST_VoronoiPolygons(ST_Collect(geom)))).geom AS cell_geom
            FROM boundary_terrain_points
        ),
        -- Associate each Voronoi cell with its terrain point
        voronoi_cells AS (
            SELECT 
                btp.id AS terrain_point_id,
                vp.cell_geom
            FROM 
                boundary_terrain_points btp
            JOIN 
                voronoi_polygons vp
                ON ST_Contains(vp.cell_geom, btp.geom)
        )
        -- Find boundary nodes that fall within each Voronoi cell
        INSERT INTO reversed_voronoi_connections (terrain_point_id, boundary_node_id, distance, voronoi_cell)
        SELECT 
            vc.terrain_point_id,
            bn.id AS boundary_node_id,
            ST_Distance(
                (SELECT geom FROM test_terrain_points WHERE id = vc.terrain_point_id),
                bn.geom
            ) AS distance,
            vc.cell_geom AS voronoi_cell
        FROM 
            voronoi_cells vc
        JOIN 
            test_boundary_nodes bn
            ON ST_Intersects(vc.cell_geom, bn.geom)
        WHERE 
            ST_Distance(
                (SELECT geom FROM test_terrain_points WHERE id = vc.terrain_point_id),
                bn.geom
            ) <= :max_distance;
    EXCEPTION
        WHEN OTHERS THEN
            -- If Voronoi diagram generation fails, fall back to nearest neighbor approach
            RAISE NOTICE 'Reversed Voronoi diagram generation failed, falling back to nearest neighbor approach';
            
            -- For each boundary terrain point, find the nearest boundary node
            INSERT INTO reversed_voronoi_connections (terrain_point_id, boundary_node_id, distance)
            SELECT 
                tgp.id AS terrain_point_id,
                (
                    SELECT bn.id
                    FROM test_boundary_nodes bn
                    ORDER BY ST_Distance(tgp.geom, bn.geom)
                    LIMIT 1
                ) AS boundary_node_id,
                ST_Distance(
                    tgp.geom,
                    (SELECT geom FROM test_boundary_nodes WHERE id = (
                        SELECT bn.id
                        FROM test_boundary_nodes bn
                        ORDER BY ST_Distance(tgp.geom, bn.geom)
                        LIMIT 1
                    ))
                ) AS distance
            FROM 
                test_terrain_points tgp
            WHERE 
                tgp.hex_type = 'boundary'
                AND ST_Distance(
                    tgp.geom,
                    (SELECT geom FROM test_boundary_nodes WHERE id = (
                        SELECT bn.id
                        FROM test_boundary_nodes bn
                        ORDER BY ST_Distance(tgp.geom, bn.geom)
                        LIMIT 1
                    ))
                ) <= :max_distance;
    END;
    
    end_time := clock_timestamp();
    execution_time_ms := EXTRACT(EPOCH FROM (end_time - start_time)) * 1000;
    
    -- Calculate metrics
    SELECT COUNT(*) INTO connection_count FROM reversed_voronoi_connections;
    SELECT AVG(distance) INTO avg_connection_length FROM reversed_voronoi_connections;
    
    -- Calculate evenness score
    WITH connection_counts AS (
        SELECT 
            boundary_node_id,
            COUNT(*) AS count
        FROM 
            reversed_voronoi_connections
        GROUP BY 
            boundary_node_id
    )
    SELECT 
        AVG(count) INTO mean
    FROM 
        connection_counts;
    
    WITH connection_counts AS (
        SELECT 
            boundary_node_id,
            COUNT(*) AS count
        FROM 
            reversed_voronoi_connections
        GROUP BY 
            boundary_node_id
    )
    SELECT 
        SQRT(AVG(POWER(count - mean, 2))) INTO std_dev
    FROM 
        connection_counts;
    
    evenness_score := 1 - (std_dev / NULLIF(mean, 0));
    
    -- Insert metrics
    INSERT INTO connection_metrics (strategy, connection_count, avg_connection_length, execution_time_ms, evenness_score)
    VALUES ('Reversed Voronoi', connection_count, avg_connection_length, execution_time_ms, evenness_score);
END $$;

-- Print metrics
SELECT * FROM connection_metrics ORDER BY evenness_score DESC;

-- Print connection counts
SELECT 'Nearest Neighbor' AS strategy, COUNT(*) AS connection_count FROM nearest_neighbor_connections
UNION ALL
SELECT 'Buffer-Based Voronoi' AS strategy, COUNT(*) AS connection_count FROM buffer_based_voronoi_connections
UNION ALL
SELECT 'True Voronoi' AS strategy, COUNT(*) AS connection_count FROM true_voronoi_connections
UNION ALL
SELECT 'Reversed Voronoi' AS strategy, COUNT(*) AS connection_count FROM reversed_voronoi_connections
ORDER BY strategy;

-- Print boundary node connection distribution
SELECT 'Nearest Neighbor' AS strategy, boundary_node_id, COUNT(*) AS connection_count
FROM nearest_neighbor_connections
GROUP BY boundary_node_id
ORDER BY boundary_node_id
LIMIT 10;

SELECT 'Buffer-Based Voronoi' AS strategy, boundary_node_id, COUNT(*) AS connection_count
FROM buffer_based_voronoi_connections
GROUP BY boundary_node_id
ORDER BY boundary_node_id
LIMIT 10;

SELECT 'True Voronoi' AS strategy, boundary_node_id, COUNT(*) AS connection_count
FROM true_voronoi_connections
GROUP BY boundary_node_id
ORDER BY boundary_node_id
LIMIT 10;

SELECT 'Reversed Voronoi' AS strategy, boundary_node_id, COUNT(*) AS connection_count
FROM reversed_voronoi_connections
GROUP BY boundary_node_id
ORDER BY boundary_node_id
LIMIT 10;

-- Disable timing
\timing off
