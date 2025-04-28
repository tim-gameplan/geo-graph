-- Test Envelope Configurations for Voronoi Diagram Generation
-- This script tests ST_VoronoiPolygons with various envelope configurations
-- which might be causing the "Invalid number of points in LinearRing found 2 - must be 0 or >= 4" error

-- Function to test Voronoi diagram generation with different envelope configurations
CREATE OR REPLACE FUNCTION test_voronoi_envelope_configurations() RETURNS VOID AS $$
DECLARE
    test_id INTEGER;
    result_id INTEGER;
    start_time TIMESTAMP;
    end_time TIMESTAMP;
    execution_time NUMERIC;
    voronoi_result GEOMETRY;
    error_message TEXT;
    success BOOLEAN;
    envelope GEOMETRY;
BEGIN
    -- Test 1: Points on the boundary of the envelope
    -- Insert test data
    INSERT INTO voronoi_test_points (
        test_name, 
        test_description, 
        test_phase, 
        test_category,
        point_count,
        points
    ) VALUES (
        'Points on Envelope Boundary',
        'Points positioned exactly on the boundary of the envelope',
        'phase3_boundary_cases',
        'envelope',
        5,
        ST_Collect(ARRAY[
            ST_SetSRID(ST_MakePoint(0, 0), 3857),     -- Bottom-left corner
            ST_SetSRID(ST_MakePoint(1000, 0), 3857),  -- Bottom-right corner
            ST_SetSRID(ST_MakePoint(1000, 1000), 3857), -- Top-right corner
            ST_SetSRID(ST_MakePoint(0, 1000), 3857),  -- Top-left corner
            ST_SetSRID(ST_MakePoint(500, 500), 3857)  -- Center point
        ])
    ) RETURNING test_id INTO test_id;
    
    -- Create an envelope that exactly matches the points' extent
    envelope := ST_Envelope((SELECT points FROM voronoi_test_points WHERE test_id = test_id));
    
    -- Run the test
    BEGIN
        start_time := clock_timestamp();
        voronoi_result := ST_VoronoiPolygons(
            (SELECT points FROM voronoi_test_points WHERE test_id = test_id),
            0, -- tolerance
            envelope
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
        'envelope',
        success,
        error_message,
        execution_time,
        voronoi_result
    ) RETURNING result_id INTO result_id;
    
    -- Store the envelope parameter
    INSERT INTO voronoi_test_parameters (
        result_id,
        param_name,
        param_value
    ) VALUES (
        result_id,
        'envelope',
        ST_AsText(envelope)
    );
    
    -- Log the result
    RAISE NOTICE 'Test "Points on Envelope Boundary": %', CASE WHEN success THEN 'SUCCESS' ELSE 'FAILURE: ' || error_message END;
    
    -- Test 2: Expanded envelope
    -- Run the test with an expanded envelope
    envelope := ST_Expand(envelope, 100);
    
    BEGIN
        start_time := clock_timestamp();
        voronoi_result := ST_VoronoiPolygons(
            (SELECT points FROM voronoi_test_points WHERE test_id = test_id),
            0, -- tolerance
            envelope
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
    
    -- Store the result with a new test name
    INSERT INTO voronoi_test_points (
        test_name, 
        test_description, 
        test_phase, 
        test_category,
        point_count,
        points
    ) VALUES (
        'Points with Expanded Envelope',
        'Same points but with an envelope expanded by 100 units',
        'phase3_boundary_cases',
        'envelope',
        5,
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
        'envelope',
        success,
        error_message,
        execution_time,
        voronoi_result
    ) RETURNING result_id INTO result_id;
    
    -- Store the envelope parameter
    INSERT INTO voronoi_test_parameters (
        result_id,
        param_name,
        param_value
    ) VALUES (
        result_id,
        'envelope',
        ST_AsText(envelope)
    );
    
    -- Log the result
    RAISE NOTICE 'Test "Points with Expanded Envelope": %', CASE WHEN success THEN 'SUCCESS' ELSE 'FAILURE: ' || error_message END;
    
    -- Test 3: Points outside the envelope
    -- Insert test data
    INSERT INTO voronoi_test_points (
        test_name, 
        test_description, 
        test_phase, 
        test_category,
        point_count,
        points
    ) VALUES (
        'Points Outside Envelope',
        'Points that are outside the specified envelope',
        'phase3_boundary_cases',
        'envelope',
        5,
        ST_Collect(ARRAY[
            ST_SetSRID(ST_MakePoint(0, 0), 3857),
            ST_SetSRID(ST_MakePoint(1000, 0), 3857),
            ST_SetSRID(ST_MakePoint(1000, 1000), 3857),
            ST_SetSRID(ST_MakePoint(0, 1000), 3857),
            ST_SetSRID(ST_MakePoint(500, 500), 3857)
        ])
    ) RETURNING test_id INTO test_id;
    
    -- Create a smaller envelope that doesn't contain all points
    envelope := ST_MakeEnvelope(100, 100, 900, 900, 3857);
    
    -- Run the test
    BEGIN
        start_time := clock_timestamp();
        voronoi_result := ST_VoronoiPolygons(
            (SELECT points FROM voronoi_test_points WHERE test_id = test_id),
            0, -- tolerance
            envelope
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
        'envelope',
        success,
        error_message,
        execution_time,
        voronoi_result
    ) RETURNING result_id INTO result_id;
    
    -- Store the envelope parameter
    INSERT INTO voronoi_test_parameters (
        result_id,
        param_name,
        param_value
    ) VALUES (
        result_id,
        'envelope',
        ST_AsText(envelope)
    );
    
    -- Log the result
    RAISE NOTICE 'Test "Points Outside Envelope": %', CASE WHEN success THEN 'SUCCESS' ELSE 'FAILURE: ' || error_message END;
    
    -- Test 4: Very large envelope
    -- Run the test with a very large envelope
    envelope := ST_MakeEnvelope(-10000, -10000, 10000, 10000, 3857);
    
    BEGIN
        start_time := clock_timestamp();
        voronoi_result := ST_VoronoiPolygons(
            (SELECT points FROM voronoi_test_points WHERE test_id = test_id),
            0, -- tolerance
            envelope
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
    
    -- Store the result with a new test name
    INSERT INTO voronoi_test_points (
        test_name, 
        test_description, 
        test_phase, 
        test_category,
        point_count,
        points
    ) VALUES (
        'Points with Very Large Envelope',
        'Same points but with a very large envelope',
        'phase3_boundary_cases',
        'envelope',
        5,
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
        'envelope',
        success,
        error_message,
        execution_time,
        voronoi_result
    ) RETURNING result_id INTO result_id;
    
    -- Store the envelope parameter
    INSERT INTO voronoi_test_parameters (
        result_id,
        param_name,
        param_value
    ) VALUES (
        result_id,
        'envelope',
        ST_AsText(envelope)
    );
    
    -- Log the result
    RAISE NOTICE 'Test "Points with Very Large Envelope": %', CASE WHEN success THEN 'SUCCESS' ELSE 'FAILURE: ' || error_message END;
    
    -- Test 5: No envelope parameter
    -- Insert test data
    INSERT INTO voronoi_test_points (
        test_name, 
        test_description, 
        test_phase, 
        test_category,
        point_count,
        points
    ) VALUES (
        'Points with No Envelope',
        'Points with no envelope parameter (NULL)',
        'phase3_boundary_cases',
        'envelope',
        5,
        ST_Collect(ARRAY[
            ST_SetSRID(ST_MakePoint(0, 0), 3857),
            ST_SetSRID(ST_MakePoint(1000, 0), 3857),
            ST_SetSRID(ST_MakePoint(1000, 1000), 3857),
            ST_SetSRID(ST_MakePoint(0, 1000), 3857),
            ST_SetSRID(ST_MakePoint(500, 500), 3857)
        ])
    ) RETURNING test_id INTO test_id;
    
    -- Run the test with NULL envelope
    BEGIN
        start_time := clock_timestamp();
        voronoi_result := ST_VoronoiPolygons(
            (SELECT points FROM voronoi_test_points WHERE test_id = test_id),
            0 -- tolerance, no envelope parameter
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
        'envelope',
        success,
        error_message,
        execution_time,
        voronoi_result
    ) RETURNING result_id INTO result_id;
    
    -- Store the envelope parameter
    INSERT INTO voronoi_test_parameters (
        result_id,
        param_name,
        param_value
    ) VALUES (
        result_id,
        'envelope',
        'NULL'
    );
    
    -- Log the result
    RAISE NOTICE 'Test "Points with No Envelope": %', CASE WHEN success THEN 'SUCCESS' ELSE 'FAILURE: ' || error_message END;
    
    -- Test 6: Tiny envelope
    -- Run the test with a very small envelope
    envelope := ST_MakeEnvelope(499, 499, 501, 501, 3857);
    
    BEGIN
        start_time := clock_timestamp();
        voronoi_result := ST_VoronoiPolygons(
            (SELECT points FROM voronoi_test_points WHERE test_id = test_id),
            0, -- tolerance
            envelope
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
    
    -- Store the result with a new test name
    INSERT INTO voronoi_test_points (
        test_name, 
        test_description, 
        test_phase, 
        test_category,
        point_count,
        points
    ) VALUES (
        'Points with Tiny Envelope',
        'Same points but with a very small envelope that only contains the center point',
        'phase3_boundary_cases',
        'envelope',
        5,
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
        'envelope',
        success,
        error_message,
        execution_time,
        voronoi_result
    ) RETURNING result_id INTO result_id;
    
    -- Store the envelope parameter
    INSERT INTO voronoi_test_parameters (
        result_id,
        param_name,
        param_value
    ) VALUES (
        result_id,
        'envelope',
        ST_AsText(envelope)
    );
    
    -- Log the result
    RAISE NOTICE 'Test "Points with Tiny Envelope": %', CASE WHEN success THEN 'SUCCESS' ELSE 'FAILURE: ' || error_message END;
END;
$$ LANGUAGE plpgsql;

-- Execute the test function
SELECT test_voronoi_envelope_configurations();

-- Query to view the results
SELECT 
    p.test_name,
    r.success,
    r.error_message,
    r.execution_time,
    param.param_value AS envelope,
    ST_AsText(r.voronoi_diagram) AS voronoi_wkt
FROM 
    voronoi_test_results r
JOIN 
    voronoi_test_points p ON r.test_id = p.test_id
LEFT JOIN
    voronoi_test_parameters param ON r.result_id = param.result_id AND param.param_name = 'envelope'
WHERE 
    p.test_phase = 'phase3_boundary_cases' AND p.test_category = 'envelope'
ORDER BY 
    p.test_id;
