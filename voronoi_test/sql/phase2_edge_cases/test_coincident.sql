-- Test Coincident Points for Voronoi Diagram Generation
-- This script tests ST_VoronoiPolygons with coincident or nearly coincident point configurations
-- which might be causing the "Invalid number of points in LinearRing found 2 - must be 0 or >= 4" error

-- Function to test Voronoi diagram generation with coincident point sets
CREATE OR REPLACE FUNCTION test_voronoi_coincident_points() RETURNS VOID AS $$
DECLARE
    test_id INTEGER;
    result_id INTEGER;
    start_time TIMESTAMP;
    end_time TIMESTAMP;
    execution_time NUMERIC;
    voronoi_result GEOMETRY;
    error_message TEXT;
    success BOOLEAN;
BEGIN
    -- Test 1: Two exactly coincident points
    -- Insert test data
    INSERT INTO voronoi_test_points (
        test_name, 
        test_description, 
        test_phase, 
        test_category,
        point_count,
        points
    ) VALUES (
        'Two Exactly Coincident Points',
        'Two points at exactly the same location',
        'phase2_edge_cases',
        'coincident',
        2,
        ST_Collect(ARRAY[
            ST_SetSRID(ST_MakePoint(500, 500), 3857),
            ST_SetSRID(ST_MakePoint(500, 500), 3857)  -- Exactly the same point
        ])
    ) RETURNING test_id INTO test_id;
    
    -- Run the test
    BEGIN
        start_time := clock_timestamp();
        voronoi_result := ST_VoronoiPolygons(
            (SELECT points FROM voronoi_test_points WHERE test_id = test_id),
            0, -- tolerance
            ST_Expand((SELECT ST_Envelope(points) FROM voronoi_test_points WHERE test_id = test_id), 100)
        );
        end_time := clock_timestamp();
        execution_time := EXTRACT(EPOCH FROM (end_time - start_time)) * 1000; -- in milliseconds
        success := TRUE;
        error_message := NULL;
    EXCEPTION WHEN OTHERS THEN
        end_time := clock_timestamp();
        execution_time := EXTRACT(EPOCH FROM (end_time - start_time)) * 1000; -- in milliseconds
        success := FALSE;
        error_message := SQLERRM;
        voronoi_result := NULL;
    END;
    
    -- Store the result
    INSERT INTO voronoi_test_results (
        test_id,
        test_type,
        success,
        error_message,
        execution_time,
        voronoi_diagram
    ) VALUES (
        test_id,
        'points',
        success,
        error_message,
        execution_time,
        voronoi_result
    ) RETURNING result_id INTO result_id;
    
    -- Log the result
    RAISE NOTICE 'Test "Two Exactly Coincident Points": %', CASE WHEN success THEN 'SUCCESS' ELSE 'FAILURE: ' || error_message END;
    
    -- Test 2: Two nearly coincident points (very close)
    -- Insert test data
    INSERT INTO voronoi_test_points (
        test_name, 
        test_description, 
        test_phase, 
        test_category,
        point_count,
        points
    ) VALUES (
        'Two Nearly Coincident Points',
        'Two points very close to each other (0.0001 units apart)',
        'phase2_edge_cases',
        'coincident',
        2,
        ST_Collect(ARRAY[
            ST_SetSRID(ST_MakePoint(500, 500), 3857),
            ST_SetSRID(ST_MakePoint(500.0001, 500.0001), 3857)  -- Very close point
        ])
    ) RETURNING test_id INTO test_id;
    
    -- Run the test
    BEGIN
        start_time := clock_timestamp();
        voronoi_result := ST_VoronoiPolygons(
            (SELECT points FROM voronoi_test_points WHERE test_id = test_id),
            0, -- tolerance
            ST_Expand((SELECT ST_Envelope(points) FROM voronoi_test_points WHERE test_id = test_id), 100)
        );
        end_time := clock_timestamp();
        execution_time := EXTRACT(EPOCH FROM (end_time - start_time)) * 1000; -- in milliseconds
        success := TRUE;
        error_message := NULL;
    EXCEPTION WHEN OTHERS THEN
        end_time := clock_timestamp();
        execution_time := EXTRACT(EPOCH FROM (end_time - start_time)) * 1000; -- in milliseconds
        success := FALSE;
        error_message := SQLERRM;
        voronoi_result := NULL;
    END;
    
    -- Store the result
    INSERT INTO voronoi_test_results (
        test_id,
        test_type,
        success,
        error_message,
        execution_time,
        voronoi_diagram
    ) VALUES (
        test_id,
        'points',
        success,
        error_message,
        execution_time,
        voronoi_result
    ) RETURNING result_id INTO result_id;
    
    -- Log the result
    RAISE NOTICE 'Test "Two Nearly Coincident Points": %', CASE WHEN success THEN 'SUCCESS' ELSE 'FAILURE: ' || error_message END;
    
    -- Test 3: Multiple coincident points
    -- Insert test data
    INSERT INTO voronoi_test_points (
        test_name, 
        test_description, 
        test_phase, 
        test_category,
        point_count,
        points
    ) VALUES (
        'Multiple Coincident Points',
        'Five points, with three at the same location',
        'phase2_edge_cases',
        'coincident',
        5,
        ST_Collect(ARRAY[
            ST_SetSRID(ST_MakePoint(0, 0), 3857),
            ST_SetSRID(ST_MakePoint(1000, 1000), 3857),
            ST_SetSRID(ST_MakePoint(500, 500), 3857),  -- Three coincident points
            ST_SetSRID(ST_MakePoint(500, 500), 3857),
            ST_SetSRID(ST_MakePoint(500, 500), 3857)
        ])
    ) RETURNING test_id INTO test_id;
    
    -- Run the test
    BEGIN
        start_time := clock_timestamp();
        voronoi_result := ST_VoronoiPolygons(
            (SELECT points FROM voronoi_test_points WHERE test_id = test_id),
            0, -- tolerance
            ST_Expand((SELECT ST_Envelope(points) FROM voronoi_test_points WHERE test_id = test_id), 100)
        );
        end_time := clock_timestamp();
        execution_time := EXTRACT(EPOCH FROM (end_time - start_time)) * 1000; -- in milliseconds
        success := TRUE;
        error_message := NULL;
    EXCEPTION WHEN OTHERS THEN
        end_time := clock_timestamp();
        execution_time := EXTRACT(EPOCH FROM (end_time - start_time)) * 1000; -- in milliseconds
        success := FALSE;
        error_message := SQLERRM;
        voronoi_result := NULL;
    END;
    
    -- Store the result
    INSERT INTO voronoi_test_results (
        test_id,
        test_type,
        success,
        error_message,
        execution_time,
        voronoi_diagram
    ) VALUES (
        test_id,
        'points',
        success,
        error_message,
        execution_time,
        voronoi_result
    ) RETURNING result_id INTO result_id;
    
    -- Log the result
    RAISE NOTICE 'Test "Multiple Coincident Points": %', CASE WHEN success THEN 'SUCCESS' ELSE 'FAILURE: ' || error_message END;
    
    -- Test 4: Coincident points with tolerance
    -- Insert test data
    INSERT INTO voronoi_test_points (
        test_name, 
        test_description, 
        test_phase, 
        test_category,
        point_count,
        points
    ) VALUES (
        'Coincident Points With Tolerance',
        'Two nearly coincident points with tolerance parameter',
        'phase2_edge_cases',
        'coincident',
        2,
        ST_Collect(ARRAY[
            ST_SetSRID(ST_MakePoint(500, 500), 3857),
            ST_SetSRID(ST_MakePoint(500.01, 500.01), 3857)  -- Close point
        ])
    ) RETURNING test_id INTO test_id;
    
    -- Run the test with tolerance
    BEGIN
        start_time := clock_timestamp();
        voronoi_result := ST_VoronoiPolygons(
            (SELECT points FROM voronoi_test_points WHERE test_id = test_id),
            0.1, -- tolerance (should merge points within 0.1 units)
            ST_Expand((SELECT ST_Envelope(points) FROM voronoi_test_points WHERE test_id = test_id), 100)
        );
        end_time := clock_timestamp();
        execution_time := EXTRACT(EPOCH FROM (end_time - start_time)) * 1000; -- in milliseconds
        success := TRUE;
        error_message := NULL;
    EXCEPTION WHEN OTHERS THEN
        end_time := clock_timestamp();
        execution_time := EXTRACT(EPOCH FROM (end_time - start_time)) * 1000; -- in milliseconds
        success := FALSE;
        error_message := SQLERRM;
        voronoi_result := NULL;
    END;
    
    -- Store the result
    INSERT INTO voronoi_test_results (
        test_id,
        test_type,
        success,
        error_message,
        execution_time,
        voronoi_diagram
    ) VALUES (
        test_id,
        'points',
        success,
        error_message,
        execution_time,
        voronoi_result
    ) RETURNING result_id INTO result_id;
    
    -- Store the tolerance parameter
    INSERT INTO voronoi_test_parameters (
        result_id,
        param_name,
        param_value
    ) VALUES (
        result_id,
        'tolerance',
        '0.1'
    );
    
    -- Log the result
    RAISE NOTICE 'Test "Coincident Points With Tolerance": %', CASE WHEN success THEN 'SUCCESS' ELSE 'FAILURE: ' || error_message END;
    
    -- Test 5: Cluster of nearly coincident points
    -- Insert test data
    INSERT INTO voronoi_test_points (
        test_name, 
        test_description, 
        test_phase, 
        test_category,
        point_count,
        points
    ) VALUES (
        'Cluster of Nearly Coincident Points',
        'A cluster of 10 points very close to each other',
        'phase2_edge_cases',
        'coincident',
        10,
        ST_Collect(ARRAY[
            ST_SetSRID(ST_MakePoint(500, 500), 3857),
            ST_SetSRID(ST_MakePoint(500.001, 500.001), 3857),
            ST_SetSRID(ST_MakePoint(500.002, 500.002), 3857),
            ST_SetSRID(ST_MakePoint(499.999, 499.999), 3857),
            ST_SetSRID(ST_MakePoint(499.998, 499.998), 3857),
            ST_SetSRID(ST_MakePoint(500.001, 499.999), 3857),
            ST_SetSRID(ST_MakePoint(499.999, 500.001), 3857),
            ST_SetSRID(ST_MakePoint(500.002, 499.998), 3857),
            ST_SetSRID(ST_MakePoint(499.998, 500.002), 3857),
            ST_SetSRID(ST_MakePoint(500, 500.001), 3857)
        ])
    ) RETURNING test_id INTO test_id;
    
    -- Run the test
    BEGIN
        start_time := clock_timestamp();
        voronoi_result := ST_VoronoiPolygons(
            (SELECT points FROM voronoi_test_points WHERE test_id = test_id),
            0, -- tolerance
            ST_Expand((SELECT ST_Envelope(points) FROM voronoi_test_points WHERE test_id = test_id), 100)
        );
        end_time := clock_timestamp();
        execution_time := EXTRACT(EPOCH FROM (end_time - start_time)) * 1000; -- in milliseconds
        success := TRUE;
        error_message := NULL;
    EXCEPTION WHEN OTHERS THEN
        end_time := clock_timestamp();
        execution_time := EXTRACT(EPOCH FROM (end_time - start_time)) * 1000; -- in milliseconds
        success := FALSE;
        error_message := SQLERRM;
        voronoi_result := NULL;
    END;
    
    -- Store the result
    INSERT INTO voronoi_test_results (
        test_id,
        test_type,
        success,
        error_message,
        execution_time,
        voronoi_diagram
    ) VALUES (
        test_id,
        'points',
        success,
        error_message,
        execution_time,
        voronoi_result
    ) RETURNING result_id INTO result_id;
    
    -- Log the result
    RAISE NOTICE 'Test "Cluster of Nearly Coincident Points": %', CASE WHEN success THEN 'SUCCESS' ELSE 'FAILURE: ' || error_message END;
    
    -- Test 6: Same test with preprocessing to remove duplicates
    -- Create a preprocessing step to remove duplicates
    BEGIN
        start_time := clock_timestamp();
        
        -- Get the original points
        DECLARE
            original_points GEOMETRY;
            deduplicated_points GEOMETRY;
        BEGIN
            SELECT points INTO original_points FROM voronoi_test_points WHERE test_id = test_id;
            
            -- Remove duplicates by using ST_Dump and ST_UnaryUnion
            deduplicated_points := ST_UnaryUnion(original_points);
            
            -- Run Voronoi on deduplicated points
            voronoi_result := ST_VoronoiPolygons(
                deduplicated_points,
                0, -- tolerance
                ST_Expand(ST_Envelope(deduplicated_points), 100)
            );
        END;
        
        end_time := clock_timestamp();
        execution_time := EXTRACT(EPOCH FROM (end_time - start_time)) * 1000; -- in milliseconds
        success := TRUE;
        error_message := NULL;
    EXCEPTION WHEN OTHERS THEN
        end_time := clock_timestamp();
        execution_time := EXTRACT(EPOCH FROM (end_time - start_time)) * 1000; -- in milliseconds
        success := FALSE;
        error_message := SQLERRM;
        voronoi_result := NULL;
    END;
    
    -- Store the result with a new test name
    INSERT INTO voronoi_test_points (
        test_name, 
        test_description, 
        test_phase, 
        test_category,
        point_count,
        points
    ) VALUES (
        'Cluster with Preprocessing',
        'Cluster of nearly coincident points with preprocessing to remove duplicates',
        'phase2_edge_cases',
        'coincident',
        10,
        (SELECT points FROM voronoi_test_points WHERE test_id = test_id)
    ) RETURNING test_id INTO test_id;
    
    -- Store the result
    INSERT INTO voronoi_test_results (
        test_id,
        test_type,
        success,
        error_message,
        execution_time,
        voronoi_diagram
    ) VALUES (
        test_id,
        'points_preprocessed',
        success,
        error_message,
        execution_time,
        voronoi_result
    ) RETURNING result_id INTO result_id;
    
    -- Store the preprocessing information
    INSERT INTO voronoi_test_preprocessing (
        result_id,
        preprocessing_type,
        description
    ) VALUES (
        result_id,
        'deduplication',
        'Used ST_UnaryUnion to remove duplicate points before Voronoi generation'
    );
    
    -- Log the result
    RAISE NOTICE 'Test "Cluster with Preprocessing": %', CASE WHEN success THEN 'SUCCESS' ELSE 'FAILURE: ' || error_message END;
END;
$$ LANGUAGE plpgsql;

-- Execute the test function
SELECT test_voronoi_coincident_points();

-- Query to view the results
SELECT 
    p.test_name,
    r.success,
    r.error_message,
    r.execution_time,
    ST_AsText(r.voronoi_diagram) AS voronoi_wkt
FROM 
    voronoi_test_results r
JOIN 
    voronoi_test_points p ON r.test_id = p.test_id
WHERE 
    p.test_phase = 'phase2_edge_cases' AND p.test_category = 'coincident'
ORDER BY 
    p.test_id;
