-- Test Simple Points for Voronoi Diagram Generation
-- This script tests ST_VoronoiPolygons with simple, well-distributed point sets

-- Function to test Voronoi diagram generation with simple point sets
CREATE OR REPLACE FUNCTION test_voronoi_simple_points() RETURNS VOID AS $$
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
    -- Test 1: Simple 5 points in a regular pattern
    -- Insert test data
    INSERT INTO voronoi_test_points (
        test_name, 
        test_description, 
        test_phase, 
        test_category,
        point_count,
        points
    ) VALUES (
        'Simple 5 Points Regular Pattern',
        'Five points arranged in a regular pattern (4 corners and 1 center)',
        'phase1_basic',
        'simple_points',
        5,
        ST_Collect(ARRAY[
            ST_SetSRID(ST_MakePoint(0, 0), 3857),
            ST_SetSRID(ST_MakePoint(1000, 0), 3857),
            ST_SetSRID(ST_MakePoint(0, 1000), 3857),
            ST_SetSRID(ST_MakePoint(1000, 1000), 3857),
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
    RAISE NOTICE 'Test "Simple 5 Points Regular Pattern": %', CASE WHEN success THEN 'SUCCESS' ELSE 'FAILURE: ' || error_message END;
    
    -- Test 2: Simple 10 points in a random pattern
    -- Insert test data
    INSERT INTO voronoi_test_points (
        test_name, 
        test_description, 
        test_phase, 
        test_category,
        point_count,
        points
    ) VALUES (
        'Simple 10 Points Random Pattern',
        'Ten points arranged in a random pattern',
        'phase1_basic',
        'simple_points',
        10,
        ST_Collect(ARRAY[
            ST_SetSRID(ST_MakePoint(100, 100), 3857),
            ST_SetSRID(ST_MakePoint(200, 300), 3857),
            ST_SetSRID(ST_MakePoint(300, 150), 3857),
            ST_SetSRID(ST_MakePoint(400, 400), 3857),
            ST_SetSRID(ST_MakePoint(500, 200), 3857),
            ST_SetSRID(ST_MakePoint(600, 350), 3857),
            ST_SetSRID(ST_MakePoint(700, 150), 3857),
            ST_SetSRID(ST_MakePoint(800, 250), 3857),
            ST_SetSRID(ST_MakePoint(900, 350), 3857),
            ST_SetSRID(ST_MakePoint(950, 100), 3857)
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
    RAISE NOTICE 'Test "Simple 10 Points Random Pattern": %', CASE WHEN success THEN 'SUCCESS' ELSE 'FAILURE: ' || error_message END;
    
    -- Test 3: Simple 4 points in a square pattern
    -- Insert test data
    INSERT INTO voronoi_test_points (
        test_name, 
        test_description, 
        test_phase, 
        test_category,
        point_count,
        points
    ) VALUES (
        'Simple 4 Points Square Pattern',
        'Four points arranged in a square pattern',
        'phase1_basic',
        'simple_points',
        4,
        ST_Collect(ARRAY[
            ST_SetSRID(ST_MakePoint(0, 0), 3857),
            ST_SetSRID(ST_MakePoint(1000, 0), 3857),
            ST_SetSRID(ST_MakePoint(0, 1000), 3857),
            ST_SetSRID(ST_MakePoint(1000, 1000), 3857)
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
    RAISE NOTICE 'Test "Simple 4 Points Square Pattern": %', CASE WHEN success THEN 'SUCCESS' ELSE 'FAILURE: ' || error_message END;
    
    -- Test 4: Simple 3 points in a triangle pattern
    -- Insert test data
    INSERT INTO voronoi_test_points (
        test_name, 
        test_description, 
        test_phase, 
        test_category,
        point_count,
        points
    ) VALUES (
        'Simple 3 Points Triangle Pattern',
        'Three points arranged in a triangle pattern',
        'phase1_basic',
        'simple_points',
        3,
        ST_Collect(ARRAY[
            ST_SetSRID(ST_MakePoint(500, 0), 3857),
            ST_SetSRID(ST_MakePoint(0, 866), 3857),  -- Equilateral triangle height = side * sqrt(3)/2
            ST_SetSRID(ST_MakePoint(1000, 866), 3857)
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
    RAISE NOTICE 'Test "Simple 3 Points Triangle Pattern": %', CASE WHEN success THEN 'SUCCESS' ELSE 'FAILURE: ' || error_message END;
END;
$$ LANGUAGE plpgsql;

-- Execute the test function
SELECT test_voronoi_simple_points();

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
    p.test_phase = 'phase1_basic' AND p.test_category = 'simple_points'
ORDER BY 
    p.test_id;
