-- Create Voronoi Obstacle Boundary Graph
-- This SQL script creates a graph representation of water obstacles using Voronoi diagrams
-- for connection assignment between terrain and water boundaries.

-- Step 1: Create boundary nodes along water obstacle boundaries
DROP TABLE IF EXISTS obstacle_boundary_nodes;
CREATE TABLE obstacle_boundary_nodes (
    node_id SERIAL PRIMARY KEY,
    water_obstacle_id INTEGER,
    point_order INTEGER,
    geom GEOMETRY(POINT, :storage_srid)
);

-- Extract points along the boundary of water obstacles at regular distance intervals
INSERT INTO obstacle_boundary_nodes (water_obstacle_id, point_order, geom)
SELECT 
    id AS water_obstacle_id,
    (ST_DumpPoints(ST_Segmentize(ST_ExteriorRing(geom), :boundary_node_spacing))).path[1] AS point_order,
    (ST_DumpPoints(ST_Segmentize(ST_ExteriorRing(geom), :boundary_node_spacing))).geom AS geom
FROM 
    water_obstacles;

-- Create spatial index on boundary nodes
CREATE INDEX IF NOT EXISTS obstacle_boundary_nodes_geom_idx ON obstacle_boundary_nodes USING GIST (geom);

-- Step 2: Create edges between adjacent boundary nodes
DROP TABLE IF EXISTS obstacle_boundary_edges;
CREATE TABLE obstacle_boundary_edges (
    edge_id SERIAL PRIMARY KEY,
    source_id INTEGER,
    target_id INTEGER,
    geom GEOMETRY(LINESTRING, :storage_srid),
    cost FLOAT
);

-- Create edges between adjacent boundary nodes
INSERT INTO obstacle_boundary_edges (source_id, target_id, geom, cost)
WITH ordered_nodes AS (
    SELECT 
        node_id,
        water_obstacle_id,
        point_order,
        geom,
        LEAD(node_id) OVER (PARTITION BY water_obstacle_id ORDER BY point_order) AS next_node_id,
        LEAD(geom) OVER (PARTITION BY water_obstacle_id ORDER BY point_order) AS next_geom,
        MAX(point_order) OVER (PARTITION BY water_obstacle_id) AS max_order
    FROM 
        obstacle_boundary_nodes
)
-- Connect consecutive nodes
SELECT 
    node_id AS source_id,
    next_node_id AS target_id,
    ST_MakeLine(geom, next_geom) AS geom,
    ST_Length(ST_MakeLine(geom, next_geom)) AS cost
FROM 
    ordered_nodes
WHERE 
    next_node_id IS NOT NULL
UNION ALL
-- Connect last node back to first node to close the loop
SELECT 
    n1.node_id AS source_id,
    n2.node_id AS target_id,
    ST_MakeLine(n1.geom, n2.geom) AS geom,
    ST_Length(ST_MakeLine(n1.geom, n2.geom)) AS cost
FROM 
    ordered_nodes n1
JOIN 
    obstacle_boundary_nodes n2 
    ON n1.water_obstacle_id = n2.water_obstacle_id AND n2.point_order = 1
WHERE 
    n1.point_order = n1.max_order;

-- Create spatial index on boundary edges
CREATE INDEX IF NOT EXISTS obstacle_boundary_edges_geom_idx ON obstacle_boundary_edges USING GIST (geom);

-- Step 3: Preprocess boundary nodes for robust Voronoi diagram generation
DROP TABLE IF EXISTS preprocessed_boundary_nodes;
CREATE TABLE preprocessed_boundary_nodes AS
WITH preprocessed AS (
    SELECT 
        node_id,
        water_obstacle_id,
        (preprocess_voronoi_points(
            geom, 
            :voronoi_preprocessing_tolerance, 
            :voronoi_preprocessing_envelope_expansion, 
            :voronoi_preprocessing_add_jitter = 'TRUE', 
            :voronoi_preprocessing_jitter_amount
        )).preprocessed_points AS geom
    FROM 
        obstacle_boundary_nodes
)
SELECT 
    node_id,
    water_obstacle_id,
    geom
FROM 
    preprocessed
WHERE 
    geom IS NOT NULL;

-- Create spatial index on preprocessed boundary nodes
CREATE INDEX IF NOT EXISTS preprocessed_boundary_nodes_geom_idx ON preprocessed_boundary_nodes USING GIST (geom);

-- Add diagnostic query
SELECT 'Number of boundary nodes: ' || COUNT(*) FROM obstacle_boundary_nodes;
SELECT 'Number of preprocessed boundary nodes: ' || COUNT(*) FROM preprocessed_boundary_nodes;

-- Step 4: Generate Voronoi diagram using ST_VoronoiPolygons
DROP TABLE IF EXISTS voronoi_cells;
CREATE TABLE voronoi_cells (
    node_id INTEGER PRIMARY KEY,
    cell_geom GEOMETRY(POLYGON, :storage_srid)
);

-- Use ST_VoronoiPolygons to create Voronoi cells
DO $$
DECLARE
    cell_count INTEGER;
    error_count INTEGER := 0;
    water_union GEOMETRY;
    study_area_envelope GEOMETRY;
    voronoi_polygons GEOMETRY;
    points_collection GEOMETRY;
    max_points_per_chunk INTEGER := 1000;
    total_points INTEGER;
    chunk_count INTEGER;
    current_chunk INTEGER;
    chunk_size INTEGER;
    chunk_start INTEGER;
    chunk_end INTEGER;
BEGIN
    -- Create a simplified water union to improve performance
    BEGIN
        SELECT ST_Union(ST_SimplifyPreserveTopology(geom, 5)) INTO water_union FROM water_obstacles;
        RAISE NOTICE 'Created water union geometry';
    EXCEPTION WHEN OTHERS THEN
        RAISE NOTICE 'Error creating water union: %', SQLERRM;
        -- Fallback to individual water obstacles
        water_union := NULL;
    END;
    
    -- Create a study area envelope with some padding
    BEGIN
        SELECT ST_Envelope(ST_Buffer(ST_Extent(geom), 1000)) INTO study_area_envelope 
        FROM obstacle_boundary_nodes;
        RAISE NOTICE 'Created study area envelope';
    EXCEPTION WHEN OTHERS THEN
        RAISE NOTICE 'Error creating study area envelope: %', SQLERRM;
        -- Fallback to a large buffer around the first point
        SELECT ST_Buffer(geom, 10000) INTO study_area_envelope 
        FROM obstacle_boundary_nodes LIMIT 1;
    END;
    
    -- Get total number of points
    SELECT COUNT(*) INTO total_points FROM obstacle_boundary_nodes;
    
    -- Calculate number of chunks needed
    chunk_count := CEIL(total_points::float / max_points_per_chunk::float);
    RAISE NOTICE 'Processing % points in % chunks of % points each', 
                 total_points, chunk_count, max_points_per_chunk;
    
    -- Process points in chunks to avoid memory issues
    FOR current_chunk IN 1..chunk_count LOOP
        BEGIN
            -- Calculate chunk boundaries
            chunk_start := (current_chunk - 1) * max_points_per_chunk + 1;
            chunk_end := LEAST(current_chunk * max_points_per_chunk, total_points);
            chunk_size := chunk_end - chunk_start + 1;
            
            RAISE NOTICE 'Processing chunk % of % (points % to %)', 
                         current_chunk, chunk_count, chunk_start, chunk_end;
            
            -- Create a collection of points for this chunk
            SELECT ST_Collect(geom) INTO points_collection
            FROM (
                SELECT geom 
                FROM obstacle_boundary_nodes
                ORDER BY node_id
                LIMIT chunk_size OFFSET chunk_start - 1
            ) AS chunk_points;
            
            -- Generate Voronoi polygons for this chunk
            BEGIN
                -- Add tolerance and envelope parameters to make it more robust
                voronoi_polygons := ST_VoronoiPolygons(
                    points_collection,
                    0.0, -- tolerance
                    study_area_envelope -- envelope to clip the result
                );
                
                RAISE NOTICE 'Generated Voronoi polygons for chunk %', current_chunk;
                
                -- Match each Voronoi cell with the nearest boundary node
                WITH voronoi_dump AS (
                    SELECT 
                        (ST_Dump(voronoi_polygons)).geom AS cell_geom
                ),
                nearest_nodes AS (
                    SELECT 
                        vd.cell_geom,
                        (
                            SELECT node_id
                            FROM obstacle_boundary_nodes
                            ORDER BY ST_Distance(geom, ST_PointOnSurface(vd.cell_geom))
                            LIMIT 1
                        ) AS node_id
                    FROM 
                        voronoi_dump vd
                    WHERE 
                        ST_IsValid(vd.cell_geom)
                )
                INSERT INTO voronoi_cells (node_id, cell_geom)
                SELECT 
                    node_id,
                    cell_geom
                FROM 
                    nearest_nodes
                ON CONFLICT (node_id) DO UPDATE
                SET cell_geom = 
                    CASE
                        -- Keep the smaller cell if we have a conflict
                        WHEN ST_Area(voronoi_cells.cell_geom) > ST_Area(EXCLUDED.cell_geom)
                        THEN EXCLUDED.cell_geom
                        ELSE voronoi_cells.cell_geom
                    END;
                
                GET DIAGNOSTICS cell_count = ROW_COUNT;
                RAISE NOTICE 'Inserted/updated % Voronoi cells from chunk %', cell_count, current_chunk;
            EXCEPTION WHEN OTHERS THEN
                RAISE NOTICE 'Error generating Voronoi polygons for chunk %: %', current_chunk, SQLERRM;
                error_count := error_count + 1;
            END;
        EXCEPTION WHEN OTHERS THEN
            RAISE NOTICE 'Error processing chunk %: %', current_chunk, SQLERRM;
            error_count := error_count + 1;
        END;
    END LOOP;
    
    -- Exclude water areas from cells
    IF water_union IS NOT NULL THEN
        BEGIN
            UPDATE voronoi_cells
            SET cell_geom = ST_Difference(cell_geom, water_union)
            WHERE ST_IsValid(cell_geom) AND ST_Intersects(cell_geom, water_union);
            
            GET DIAGNOSTICS cell_count = ROW_COUNT;
            RAISE NOTICE 'Excluded water areas from % Voronoi cells', cell_count;
        EXCEPTION WHEN OTHERS THEN
            RAISE NOTICE 'Error excluding water areas: %', SQLERRM;
            error_count := error_count + 1;
        END;
    END IF;
    
    -- Remove invalid geometries
    BEGIN
        DELETE FROM voronoi_cells WHERE NOT ST_IsValid(cell_geom) OR ST_IsEmpty(cell_geom);
        
        GET DIAGNOSTICS cell_count = ROW_COUNT;
        RAISE NOTICE 'Removed % invalid Voronoi cells', cell_count;
    EXCEPTION WHEN OTHERS THEN
        RAISE NOTICE 'Error removing invalid geometries: %', SQLERRM;
        error_count := error_count + 1;
    END;
    
    -- Get final count
    SELECT COUNT(*) INTO cell_count FROM voronoi_cells;
    RAISE NOTICE 'Final Voronoi cell count after processing: % (with % errors)', cell_count, error_count;
    
    -- If we have no cells, fall back to buffer-based approach
    IF cell_count = 0 THEN
        RAISE NOTICE 'No Voronoi cells created, falling back to buffer-based approach';
        BEGIN
            -- For each boundary node, create a buffer that represents its "cell"
            INSERT INTO voronoi_cells (node_id, cell_geom)
            SELECT 
                node_id,
                ST_Buffer(geom, :voronoi_buffer_distance) AS cell_geom
            FROM 
                obstacle_boundary_nodes;
            
            GET DIAGNOSTICS cell_count = ROW_COUNT;
            RAISE NOTICE 'Created % buffer-based Voronoi cells', cell_count;
            
            -- Clip the cells to limit to max distance
            UPDATE voronoi_cells
            SET cell_geom = ST_Intersection(
                cell_geom,
                ST_Buffer(
                    (SELECT geom FROM obstacle_boundary_nodes WHERE node_id = voronoi_cells.node_id),
                    :voronoi_max_distance
                )
            )
            WHERE ST_IsValid(cell_geom);
            
            -- Exclude water areas if available
            IF water_union IS NOT NULL THEN
                UPDATE voronoi_cells
                SET cell_geom = ST_Difference(cell_geom, water_union)
                WHERE ST_IsValid(cell_geom) AND ST_Intersects(cell_geom, water_union);
            END IF;
            
            -- Remove invalid geometries
            DELETE FROM voronoi_cells WHERE NOT ST_IsValid(cell_geom) OR ST_IsEmpty(cell_geom);
            
            -- Get final count after fallback
            SELECT COUNT(*) INTO cell_count FROM voronoi_cells;
            RAISE NOTICE 'Final buffer-based Voronoi cell count: %', cell_count;
        EXCEPTION WHEN OTHERS THEN
            RAISE NOTICE 'Error in buffer-based fallback: %', SQLERRM;
        END;
    END IF;
END $$;

-- Create spatial index on Voronoi cells
CREATE INDEX IF NOT EXISTS voronoi_cells_geom_idx ON voronoi_cells USING GIST (cell_geom);

-- Add diagnostic query
SELECT 'Number of Voronoi cells: ' || COUNT(*) FROM voronoi_cells;

-- Step 5: Create connections between terrain grid points and boundary nodes using Voronoi cells
DROP TABLE IF EXISTS obstacle_boundary_connection_edges;
CREATE TABLE obstacle_boundary_connection_edges (
    edge_id SERIAL PRIMARY KEY,
    source_id INTEGER,
    target_id INTEGER,
    geom GEOMETRY(LINESTRING, :storage_srid),
    cost FLOAT
);

-- Find terrain points that fall within each Voronoi cell
INSERT INTO obstacle_boundary_connection_edges (source_id, target_id, geom, cost)
SELECT 
    tgp.id AS source_id,
    vc.node_id AS target_id,
    ST_MakeLine(
        tgp.geom,
        (SELECT geom FROM obstacle_boundary_nodes WHERE node_id = vc.node_id)
    ) AS geom,
    ST_Distance(
        tgp.geom,
        (SELECT geom FROM obstacle_boundary_nodes WHERE node_id = vc.node_id)
    ) AS cost
FROM 
    terrain_grid_points tgp
JOIN 
    voronoi_cells vc ON ST_Intersects(tgp.geom, vc.cell_geom)
WHERE 
    (tgp.hex_type = 'land' OR tgp.hex_type = 'boundary')
    -- Ensure the connection doesn't cross through water obstacles
    AND NOT EXISTS (
        SELECT 1
        FROM water_obstacles wo
        WHERE ST_Crosses(
            ST_MakeLine(
                tgp.geom,
                (SELECT geom FROM obstacle_boundary_nodes WHERE node_id = vc.node_id)
            ),
            wo.geom
        )
    )
    -- Limit the distance
    AND ST_Distance(
        tgp.geom,
        (SELECT geom FROM obstacle_boundary_nodes WHERE node_id = vc.node_id)
    ) <= :voronoi_max_distance;

-- If no connections were created with Voronoi cells, fall back to nearest neighbor approach
DO $$
BEGIN
    IF (SELECT COUNT(*) FROM obstacle_boundary_connection_edges) = 0 THEN
        RAISE NOTICE 'No connections created with Voronoi cells, falling back to nearest neighbor approach';
        
        -- Create a temporary table with boundary nodes and their buffers
        DROP TABLE IF EXISTS temp_boundary_node_buffers;
        CREATE TEMPORARY TABLE temp_boundary_node_buffers AS
        SELECT 
            node_id,
            geom,
            ST_Buffer(geom, :voronoi_buffer_distance) AS buffer_geom
        FROM 
            obstacle_boundary_nodes;

        -- Create spatial index on the buffers
        CREATE INDEX IF NOT EXISTS temp_boundary_node_buffers_geom_idx 
        ON temp_boundary_node_buffers USING GIST (buffer_geom);

        -- Create a temporary table to store the nearest boundary node for each terrain grid point
        DROP TABLE IF EXISTS temp_nearest_boundary_nodes;
        CREATE TEMPORARY TABLE temp_nearest_boundary_nodes AS
        WITH candidate_nodes AS (
            -- Find boundary nodes whose buffer contains the terrain point
            -- This is much faster than calculating distances to all boundary nodes
            SELECT 
                tgp.id AS terrain_id,
                bnb.node_id AS boundary_node_id,
                ST_Distance(tgp.geom, bnb.geom) AS distance
            FROM 
                terrain_grid_points tgp
            JOIN 
                temp_boundary_node_buffers bnb
            ON 
                ST_DWithin(tgp.geom, bnb.geom, :voronoi_max_distance)
                AND ST_Intersects(tgp.geom, bnb.buffer_geom)
            WHERE 
                (tgp.hex_type = 'land' OR tgp.hex_type = 'boundary')
        ),
        ranked_distances AS (
            SELECT 
                terrain_id,
                boundary_node_id,
                distance,
                ROW_NUMBER() OVER (
                    PARTITION BY terrain_id 
                    ORDER BY distance
                ) AS rank
            FROM 
                candidate_nodes
        )
        SELECT 
            terrain_id,
            boundary_node_id,
            distance
        FROM 
            ranked_distances
        WHERE 
            rank <= :voronoi_connection_limit;

        -- Create connections between terrain grid points and boundary nodes
        INSERT INTO obstacle_boundary_connection_edges (source_id, target_id, geom, cost)
        SELECT 
            nbn.terrain_id AS source_id,
            nbn.boundary_node_id AS target_id,
            ST_MakeLine(
                (SELECT geom FROM terrain_grid_points WHERE id = nbn.terrain_id),
                (SELECT geom FROM obstacle_boundary_nodes WHERE node_id = nbn.boundary_node_id)
            ) AS geom,
            nbn.distance AS cost
        FROM 
            temp_nearest_boundary_nodes nbn;
    END IF;
END $$;

-- Create spatial index on connection edges
CREATE INDEX IF NOT EXISTS obstacle_boundary_connection_edges_geom_idx ON obstacle_boundary_connection_edges USING GIST (geom);

-- Add diagnostic query
SELECT 'Number of connection edges: ' || COUNT(*) FROM obstacle_boundary_connection_edges;

-- Step 6: Create unified graph by combining terrain edges, boundary edges, and connection edges
DROP TABLE IF EXISTS unified_obstacle_edges;
CREATE TABLE unified_obstacle_edges (
    edge_id SERIAL PRIMARY KEY,
    source_id INTEGER,
    target_id INTEGER,
    geom GEOMETRY(LINESTRING, :storage_srid),
    cost FLOAT,
    reverse_cost FLOAT,
    edge_type VARCHAR(20)
);

-- Add terrain edges
INSERT INTO unified_obstacle_edges (source_id, target_id, geom, cost, reverse_cost, edge_type)
SELECT 
    source_id,
    target_id,
    geom,
    cost,
    cost AS reverse_cost,
    'terrain' AS edge_type
FROM 
    terrain_edges;

-- Add boundary edges
INSERT INTO unified_obstacle_edges (source_id, target_id, geom, cost, reverse_cost, edge_type)
SELECT 
    source_id,
    target_id,
    geom,
    cost,
    cost AS reverse_cost,
    'boundary' AS edge_type
FROM 
    obstacle_boundary_edges;

-- Add connection edges
INSERT INTO unified_obstacle_edges (source_id, target_id, geom, cost, reverse_cost, edge_type)
SELECT 
    source_id,
    target_id,
    geom,
    cost,
    cost AS reverse_cost,
    'connection' AS edge_type
FROM 
    obstacle_boundary_connection_edges;

-- Create spatial index on unified edges
CREATE INDEX IF NOT EXISTS unified_obstacle_edges_geom_idx ON unified_obstacle_edges USING GIST (geom);

-- Step 7: Create a unified nodes table for visualization and analysis
DROP TABLE IF EXISTS unified_obstacle_nodes;
CREATE TABLE unified_obstacle_nodes (
    node_id INTEGER PRIMARY KEY,
    geom GEOMETRY(POINT, :storage_srid),
    node_type VARCHAR(20)
);

-- Add terrain nodes
INSERT INTO unified_obstacle_nodes (node_id, geom, node_type)
SELECT 
    id AS node_id,
    geom,
    'terrain' AS node_type
FROM 
    terrain_grid_points
ON CONFLICT (node_id) DO NOTHING;

-- Add boundary nodes
INSERT INTO unified_obstacle_nodes (node_id, geom, node_type)
SELECT 
    node_id,
    geom,
    'boundary' AS node_type
FROM 
    obstacle_boundary_nodes
ON CONFLICT (node_id) DO NOTHING;

-- Create spatial index on unified nodes
CREATE INDEX IF NOT EXISTS unified_obstacle_nodes_geom_idx ON unified_obstacle_nodes USING GIST (geom);

-- Step 8: Verify graph connectivity
-- This query checks if the graph is fully connected
WITH RECURSIVE connected_nodes(node_id) AS (
    -- Start with the first node
    SELECT source_id FROM unified_obstacle_edges LIMIT 1
    UNION
    -- Add all nodes reachable from already connected nodes
    SELECT e.target_id
    FROM connected_nodes c
    JOIN unified_obstacle_edges e ON c.node_id = e.source_id
    WHERE e.target_id NOT IN (SELECT node_id FROM connected_nodes)
)
SELECT
    (SELECT COUNT(DISTINCT source_id) FROM unified_obstacle_edges) AS total_nodes,
    COUNT(*) AS connected_nodes,
    COUNT(*) * 100.0 / (SELECT COUNT(DISTINCT source_id) FROM unified_obstacle_edges) AS connectivity_percentage
FROM
    connected_nodes;

-- Add diagnostic queries for final counts
SELECT 'Final counts:' AS message;
SELECT 'Number of terrain grid points: ' || COUNT(*) FROM terrain_grid_points;
SELECT 'Number of boundary nodes: ' || COUNT(*) FROM obstacle_boundary_nodes;
SELECT 'Number of boundary edges: ' || COUNT(*) FROM obstacle_boundary_edges;
SELECT 'Number of connection edges: ' || COUNT(*) FROM obstacle_boundary_connection_edges;
SELECT 'Number of unified edges: ' || COUNT(*) FROM unified_obstacle_edges;
SELECT 'Number of Voronoi cells: ' || COUNT(*) FROM voronoi_cells;
