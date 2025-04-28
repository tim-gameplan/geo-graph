-- Create Reversed Voronoi Obstacle Boundary Graph
-- This SQL script creates a graph representation of water obstacles using Voronoi diagrams
-- for connection assignment between terrain and water boundaries.
-- The "reversed" approach creates Voronoi cells for boundary terrain points instead of boundary nodes.

-- Create preprocessing function for robust Voronoi generation
CREATE OR REPLACE FUNCTION preprocess_voronoi_points(
    points geometry,
    tolerance float DEFAULT 0.1,
    envelope_expansion float DEFAULT 1000,
    add_jitter boolean DEFAULT true,
    jitter_amount float DEFAULT 0.01
)
RETURNS TABLE(
    preprocessed_points geometry,
    envelope geometry,
    tolerance_value float
)
AS $$
DECLARE
    deduped_points geometry;
    result_points geometry;
    result_envelope geometry;
BEGIN
    -- Remove duplicate points using ST_UnaryUnion
    deduped_points := ST_UnaryUnion(points);
    
    -- Add jitter to avoid collinearity issues
    IF add_jitter THEN
        WITH points_array AS (
            SELECT (ST_Dump(deduped_points)).geom AS geom
        ),
        jittered_points AS (
            SELECT ST_Translate(
                geom,
                (random() - 0.5) * jitter_amount,
                (random() - 0.5) * jitter_amount
            ) AS geom
            FROM points_array
        )
        SELECT ST_Collect(geom) INTO result_points
        FROM jittered_points;
    ELSE
        result_points := deduped_points;
    END IF;
    
    -- Create expanded envelope
    result_envelope := ST_Expand(ST_Envelope(result_points), envelope_expansion);
    
    -- Return the results
    RETURN QUERY SELECT result_points, result_envelope, tolerance;
END;
$$ LANGUAGE plpgsql;

-- Create robust Voronoi generation function
CREATE OR REPLACE FUNCTION generate_robust_voronoi(
    points geometry,
    tolerance float DEFAULT 0.1,
    envelope_expansion float DEFAULT 1000,
    add_jitter boolean DEFAULT true,
    jitter_amount float DEFAULT 0.01
)
RETURNS geometry
AS $$
DECLARE
    prep_result record;
    voronoi_result geometry;
BEGIN
    -- Preprocess the points
    SELECT * INTO prep_result 
    FROM preprocess_voronoi_points(
        points, tolerance, envelope_expansion, add_jitter, jitter_amount
    );
    
    -- Generate the Voronoi diagram
    voronoi_result := ST_VoronoiPolygons(
        prep_result.preprocessed_points,
        prep_result.tolerance_value,
        prep_result.envelope
    );
    
    RETURN voronoi_result;
END;
$$ LANGUAGE plpgsql;

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

-- Step 3: Identify boundary terrain points for Voronoi cell creation
DROP TABLE IF EXISTS boundary_terrain_points;
CREATE TABLE boundary_terrain_points AS
SELECT 
    id,
    geom
FROM 
    terrain_grid_points
WHERE 
    hex_type = 'boundary';

-- Create spatial index on boundary terrain points
CREATE INDEX IF NOT EXISTS boundary_terrain_points_geom_idx ON boundary_terrain_points USING GIST (geom);

-- Add diagnostic query
SELECT 'Number of boundary nodes: ' || COUNT(*) FROM obstacle_boundary_nodes;
SELECT 'Number of boundary terrain points: ' || COUNT(*) FROM boundary_terrain_points;

-- Step 4: Generate Voronoi diagram for boundary terrain points using ST_VoronoiPolygons
DROP TABLE IF EXISTS voronoi_cells;
CREATE TABLE voronoi_cells (
    terrain_point_id INTEGER PRIMARY KEY,
    cell_geom GEOMETRY(POLYGON, :storage_srid)
);

-- Use a simpler approach directly based on the test implementation
DO $$
DECLARE
    points_collection GEOMETRY;
    voronoi_polygons GEOMETRY;
    study_area_envelope GEOMETRY;
    boundary_count INTEGER;
    water_union GEOMETRY;
    cell_count INTEGER;
BEGIN
    -- Count boundary terrain points
    SELECT COUNT(*) INTO boundary_count 
    FROM boundary_terrain_points;
    
    RAISE NOTICE 'Found % boundary terrain points', boundary_count;
    
    -- Create a collection of boundary terrain points
    SELECT ST_Collect(geom) INTO points_collection 
    FROM boundary_terrain_points;
    
    -- Create a study area envelope with some padding
    SELECT ST_Envelope(ST_Buffer(ST_Extent(geom), 1000)) INTO study_area_envelope 
    FROM boundary_terrain_points;
    
    -- Generate Voronoi polygons directly
    SELECT ST_VoronoiPolygons(
        points_collection,
        0.0, -- Use zero tolerance as in the test
        study_area_envelope
    ) INTO voronoi_polygons;
    
    RAISE NOTICE 'Generated Voronoi polygons';
    
    -- Insert the Voronoi polygons into the voronoi_cells table
    WITH voronoi_dump AS (
        SELECT 
            (ST_Dump(voronoi_polygons)).geom AS cell_geom
    ),
    nearest_terrain_points AS (
        SELECT 
            vd.cell_geom,
            (
                SELECT id
                FROM boundary_terrain_points
                ORDER BY ST_Distance(geom, ST_PointOnSurface(vd.cell_geom))
                LIMIT 1
            ) AS terrain_point_id
        FROM 
            voronoi_dump vd
        WHERE 
            ST_IsValid(vd.cell_geom)
    )
    INSERT INTO voronoi_cells (terrain_point_id, cell_geom)
    SELECT 
        terrain_point_id,
        cell_geom
    FROM 
        nearest_terrain_points;
    
    -- Get final count
    SELECT COUNT(*) INTO boundary_count FROM voronoi_cells;
    RAISE NOTICE 'Created % Voronoi cells', boundary_count;
    
    -- If we have no cells, fall back to buffer-based approach
    IF boundary_count = 0 THEN
        RAISE NOTICE 'No Voronoi cells created, falling back to buffer-based approach';
        
        -- For each boundary terrain point, create a buffer that represents its "cell"
        INSERT INTO voronoi_cells (terrain_point_id, cell_geom)
        SELECT 
            id AS terrain_point_id,
            ST_Buffer(geom, :voronoi_buffer_distance) AS cell_geom
        FROM 
            boundary_terrain_points;
        
        RAISE NOTICE 'Created buffer-based Voronoi cells';
    END IF;
    
    -- Exclude water areas from cells
    BEGIN
        -- Create a simplified water union
        SELECT ST_Union(ST_SimplifyPreserveTopology(geom, 5)) INTO water_union 
        FROM water_obstacles;
        
        -- Update cells to exclude water areas
        UPDATE voronoi_cells
        SET cell_geom = ST_Difference(cell_geom, water_union)
        WHERE ST_IsValid(cell_geom) AND ST_Intersects(cell_geom, water_union);
        
        GET DIAGNOSTICS cell_count = ROW_COUNT;
        RAISE NOTICE 'Excluded water areas from % Voronoi cells', cell_count;
        
        -- Remove invalid geometries
        DELETE FROM voronoi_cells 
        WHERE NOT ST_IsValid(cell_geom) OR ST_IsEmpty(cell_geom);
        
        GET DIAGNOSTICS cell_count = ROW_COUNT;
        RAISE NOTICE 'Removed % invalid Voronoi cells', cell_count;
    EXCEPTION WHEN OTHERS THEN
        RAISE NOTICE 'Error excluding water areas: %', SQLERRM;
    END;
END $$;

-- Create spatial index on Voronoi cells
CREATE INDEX IF NOT EXISTS voronoi_cells_geom_idx ON voronoi_cells USING GIST (cell_geom);

-- Add diagnostic queries
SELECT 'Number of boundary terrain points: ' || COUNT(*) FROM boundary_terrain_points;
SELECT 'Number of boundary nodes: ' || COUNT(*) FROM obstacle_boundary_nodes;
SELECT 'Number of Voronoi cells: ' || COUNT(*) FROM voronoi_cells;

-- Check for terrain points without cells
SELECT 'Terrain points without cells: ' || COUNT(*) 
FROM boundary_terrain_points 
WHERE id NOT IN (SELECT terrain_point_id FROM voronoi_cells);

-- Step 5: Create connections between boundary terrain points and boundary nodes using Voronoi cells
DROP TABLE IF EXISTS obstacle_boundary_connection_edges;
CREATE TABLE obstacle_boundary_connection_edges (
    edge_id SERIAL PRIMARY KEY,
    source_id INTEGER,
    target_id INTEGER,
    geom GEOMETRY(LINESTRING, :storage_srid),
    cost FLOAT
);

-- Find boundary nodes that fall within each Voronoi cell
INSERT INTO obstacle_boundary_connection_edges (source_id, target_id, geom, cost)
SELECT 
    vc.terrain_point_id AS source_id,
    obn.node_id AS target_id,
    ST_MakeLine(
        (SELECT geom FROM boundary_terrain_points WHERE id = vc.terrain_point_id),
        obn.geom
    ) AS geom,
    ST_Distance(
        (SELECT geom FROM boundary_terrain_points WHERE id = vc.terrain_point_id),
        obn.geom
    ) AS cost
FROM 
    voronoi_cells vc
JOIN 
    obstacle_boundary_nodes obn ON ST_Intersects(vc.cell_geom, obn.geom)
WHERE 
    -- Ensure the connection doesn't cross through water obstacles
    NOT EXISTS (
        SELECT 1
        FROM water_obstacles wo
        WHERE ST_Crosses(
            ST_MakeLine(
                (SELECT geom FROM boundary_terrain_points WHERE id = vc.terrain_point_id),
                obn.geom
            ),
            wo.geom
        )
    )
    -- Limit the distance
    AND ST_Distance(
        (SELECT geom FROM boundary_terrain_points WHERE id = vc.terrain_point_id),
        obn.geom
    ) <= :voronoi_max_distance;

-- Ensure every boundary terrain point has at least one connection
DO $$
DECLARE
    unconnected_count INTEGER;
    total_terrain_points INTEGER;
    connected_count INTEGER;
BEGIN
    -- Count how many terrain points have connections
    SELECT COUNT(DISTINCT source_id) INTO connected_count 
    FROM obstacle_boundary_connection_edges;
    
    -- Count total boundary terrain points
    SELECT COUNT(*) INTO total_terrain_points 
    FROM boundary_terrain_points;
    
    -- Calculate unconnected points
    unconnected_count := total_terrain_points - connected_count;
    
    RAISE NOTICE 'Connection check: % of % boundary terrain points are connected (% unconnected)',
        connected_count, total_terrain_points, unconnected_count;
    
    -- If some terrain points don't have connections, create them using nearest neighbor approach
    IF unconnected_count > 0 THEN
        RAISE NOTICE 'Adding connections for % unconnected terrain points', unconnected_count;
        
        -- For each unconnected boundary terrain point, find the nearest boundary nodes
        WITH unconnected_terrain_points AS (
            SELECT id
            FROM boundary_terrain_points
            WHERE id NOT IN (SELECT DISTINCT source_id FROM obstacle_boundary_connection_edges)
        ),
        nearest_boundary_nodes AS (
            SELECT 
                utp.id AS terrain_point_id,
                obn.node_id AS boundary_node_id,
                ST_Distance(
                    (SELECT geom FROM boundary_terrain_points WHERE id = utp.id),
                    obn.geom
                ) AS distance,
                ROW_NUMBER() OVER (
                    PARTITION BY utp.id 
                    ORDER BY ST_Distance(
                        (SELECT geom FROM boundary_terrain_points WHERE id = utp.id),
                        obn.geom
                    )
                ) AS rank
            FROM 
                unconnected_terrain_points utp
            CROSS JOIN 
                obstacle_boundary_nodes obn
            WHERE 
                ST_DWithin(
                    (SELECT geom FROM boundary_terrain_points WHERE id = utp.id),
                    obn.geom, 
                    :voronoi_max_distance
                )
                -- Ensure the connection doesn't cross through water obstacles
                AND NOT EXISTS (
                    SELECT 1
                    FROM water_obstacles wo
                    WHERE ST_Crosses(
                        ST_MakeLine(
                            (SELECT geom FROM boundary_terrain_points WHERE id = utp.id),
                            obn.geom
                        ),
                        wo.geom
                    )
                )
        )
        INSERT INTO obstacle_boundary_connection_edges (source_id, target_id, geom, cost)
        SELECT 
            terrain_point_id AS source_id,
            boundary_node_id AS target_id,
            ST_MakeLine(
                (SELECT geom FROM boundary_terrain_points WHERE id = terrain_point_id),
                (SELECT geom FROM obstacle_boundary_nodes WHERE node_id = boundary_node_id)
            ) AS geom,
            distance AS cost
        FROM 
            nearest_boundary_nodes
        WHERE 
            rank <= :voronoi_connection_limit;
        
        -- Get count of newly added connections
        GET DIAGNOSTICS unconnected_count = ROW_COUNT;
        RAISE NOTICE 'Added % new connections for previously unconnected terrain points', unconnected_count;
    END IF;
    
    -- If there are still no connections at all, fall back to a more aggressive approach
    IF (SELECT COUNT(*) FROM obstacle_boundary_connection_edges) = 0 THEN
        RAISE NOTICE 'No connections created, falling back to nearest neighbor approach with increased distance';
        
        -- For each boundary terrain point, find the nearest boundary nodes with increased distance
        WITH nearest_boundary_nodes AS (
            SELECT 
                btp.id AS terrain_point_id,
                obn.node_id AS boundary_node_id,
                ST_Distance(btp.geom, obn.geom) AS distance,
                ROW_NUMBER() OVER (
                    PARTITION BY btp.id 
                    ORDER BY ST_Distance(btp.geom, obn.geom)
                ) AS rank
            FROM 
                boundary_terrain_points btp
            CROSS JOIN 
                obstacle_boundary_nodes obn
            WHERE 
                ST_DWithin(btp.geom, obn.geom, :voronoi_max_distance * 2)
                -- Relaxed crossing check - only avoid complete containment
                AND NOT EXISTS (
                    SELECT 1
                    FROM water_obstacles wo
                    WHERE ST_Contains(
                        wo.geom,
                        ST_MakeLine(btp.geom, obn.geom)
                    )
                )
        )
        INSERT INTO obstacle_boundary_connection_edges (source_id, target_id, geom, cost)
        SELECT 
            terrain_point_id AS source_id,
            boundary_node_id AS target_id,
            ST_MakeLine(
                (SELECT geom FROM boundary_terrain_points WHERE id = terrain_point_id),
                (SELECT geom FROM obstacle_boundary_nodes WHERE node_id = boundary_node_id)
            ) AS geom,
            distance AS cost
        FROM 
            nearest_boundary_nodes
        WHERE 
            rank <= 1;  -- Ensure at least one connection per terrain point
    END IF;
END $$;

-- Create spatial index on connection edges
CREATE INDEX IF NOT EXISTS obstacle_boundary_connection_edges_geom_idx ON obstacle_boundary_connection_edges USING GIST (geom);

-- Add diagnostic queries
SELECT 'Number of connection edges: ' || COUNT(*) FROM obstacle_boundary_connection_edges;

-- Check for cells without connections
SELECT 'Cells without connections: ' || COUNT(*) 
FROM voronoi_cells 
WHERE terrain_point_id NOT IN (SELECT source_id FROM obstacle_boundary_connection_edges);

-- Count how many boundary nodes are assigned to each terrain point
SELECT 'Connection distribution:' AS message;
SELECT 
    source_id AS terrain_point_id,
    COUNT(*) AS node_count
FROM 
    obstacle_boundary_connection_edges
GROUP BY 
    source_id
ORDER BY 
    node_count DESC
LIMIT 10;

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

-- Step 8: Identify and connect graph components
-- Create a function to identify connected components in the graph
CREATE OR REPLACE FUNCTION identify_connected_components()
RETURNS TABLE(
    component_id INTEGER,
    node_id INTEGER
) AS $$
BEGIN
    RETURN QUERY
    WITH RECURSIVE
    nodes AS (
        SELECT DISTINCT source_id AS id FROM unified_obstacle_edges
        UNION
        SELECT DISTINCT target_id AS id FROM unified_obstacle_edges
    ),
    components(component_id, node_id) AS (
        -- Start with the first node as component 1
        SELECT 1, (SELECT MIN(id) FROM nodes)
        UNION ALL
        -- For each component, add all directly connected nodes
        SELECT 
            c.component_id,
            CASE
                WHEN e.source_id = c.node_id THEN e.target_id
                ELSE e.source_id
            END
        FROM components c
        JOIN unified_obstacle_edges e ON e.source_id = c.node_id OR e.target_id = c.node_id
        WHERE 
            CASE
                WHEN e.source_id = c.node_id THEN e.target_id
                ELSE e.source_id
            END NOT IN (SELECT node_id FROM components WHERE component_id = c.component_id)
    ),
    -- Assign component IDs to all nodes
    component_assignment AS (
        SELECT 
            node_id,
            MIN(component_id) AS component_id
        FROM components
        GROUP BY node_id
    ),
    -- Find unassigned nodes
    unassigned_nodes AS (
        SELECT id AS node_id
        FROM nodes
        WHERE id NOT IN (SELECT node_id FROM component_assignment)
    ),
    -- Assign new component IDs to unassigned nodes
    new_components AS (
        SELECT 
            node_id,
            (SELECT MAX(component_id) FROM component_assignment) + 
            ROW_NUMBER() OVER (ORDER BY node_id) AS component_id
        FROM unassigned_nodes
    )
    -- Combine assigned and new components
    SELECT component_id, node_id FROM component_assignment
    UNION ALL
    SELECT component_id, node_id FROM new_components;
END;
$$ LANGUAGE plpgsql;

-- Create a function to connect disconnected components
CREATE OR REPLACE FUNCTION connect_graph_components()
RETURNS INTEGER AS $$
DECLARE
    components_connected INTEGER := 0;
    main_component INTEGER;
    other_component INTEGER;
    main_node INTEGER;
    other_node INTEGER;
    min_distance NUMERIC;
    connection_count INTEGER;
BEGIN
    -- Check if we have multiple components
    SELECT COUNT(DISTINCT component_id) INTO connection_count
    FROM identify_connected_components();
    
    IF connection_count <= 1 THEN
        RAISE NOTICE 'Graph is already fully connected with 1 component';
        RETURN 0;
    END IF;
    
    RAISE NOTICE 'Found % disconnected components in the graph', connection_count;
    
    -- Get the largest component (main graph)
    SELECT component_id INTO main_component
    FROM (
        SELECT component_id, COUNT(*) AS node_count
        FROM identify_connected_components()
        GROUP BY component_id
        ORDER BY node_count DESC
        LIMIT 1
    ) AS largest_component;
    
    RAISE NOTICE 'Main component is % with the most nodes', main_component;
    
    -- For each other component, find the closest pair of nodes and connect them
    FOR other_component IN
        SELECT DISTINCT component_id
        FROM identify_connected_components()
        WHERE component_id != main_component
    LOOP
        RAISE NOTICE 'Connecting component % to main component %', other_component, main_component;
        
        -- Find the closest pair of nodes between the two components
        WITH main_nodes AS (
            SELECT node_id, geom
            FROM identify_connected_components() c
            JOIN unified_obstacle_nodes n ON c.node_id = n.node_id
            WHERE component_id = main_component
        ),
        other_nodes AS (
            SELECT node_id, geom
            FROM identify_connected_components() c
            JOIN unified_obstacle_nodes n ON c.node_id = n.node_id
            WHERE component_id = other_component
        ),
        distances AS (
            SELECT 
                m.node_id AS main_node_id,
                o.node_id AS other_node_id,
                ST_Distance(m.geom, o.geom) AS distance
            FROM main_nodes m
            CROSS JOIN other_nodes o
        )
        SELECT 
            main_node_id, other_node_id, MIN(distance)
        INTO 
            main_node, other_node, min_distance
        FROM distances
        GROUP BY main_node_id, other_node_id
        ORDER BY MIN(distance)
        LIMIT 1;
        
        -- Add an edge between the closest pair of nodes
        IF main_node IS NOT NULL AND other_node IS NOT NULL THEN
            RAISE NOTICE 'Adding edge between node % (main) and node % (component %)', 
                main_node, other_node, other_component;
            
            INSERT INTO unified_obstacle_edges (
                source_id, target_id, geom, cost, reverse_cost, edge_type
            )
            SELECT 
                main_node,
                other_node,
                ST_MakeLine(
                    (SELECT geom FROM unified_obstacle_nodes WHERE node_id = main_node),
                    (SELECT geom FROM unified_obstacle_nodes WHERE node_id = other_node)
                ),
                min_distance, -- cost based on distance
                min_distance, -- same for reverse cost
                'connector' AS edge_type;
            
            components_connected := components_connected + 1;
        END IF;
    END LOOP;
    
    RAISE NOTICE 'Connected % components to the main component', components_connected;
    RETURN components_connected;
END;
$$ LANGUAGE plpgsql;

-- Verify graph connectivity and connect components if needed
DO $$
DECLARE
    component_count INTEGER;
    connected_components INTEGER;
BEGIN
    -- Check initial connectivity
    SELECT COUNT(DISTINCT component_id) INTO component_count
    FROM identify_connected_components();
    
    RAISE NOTICE 'Initial graph has % connected components', component_count;
    
    -- Connect components if needed
    IF component_count > 1 THEN
        SELECT connect_graph_components() INTO connected_components;
        RAISE NOTICE 'Connected % components', connected_components;
        
        -- Verify final connectivity
        SELECT COUNT(DISTINCT component_id) INTO component_count
        FROM identify_connected_components();
        RAISE NOTICE 'Final graph has % connected components', component_count;
    ELSE
        RAISE NOTICE 'Graph is already fully connected';
    END IF;
END $$;

-- Verify final graph connectivity
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
