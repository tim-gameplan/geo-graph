-- Test Collinear Points for Voronoi Diagram Generation
-- This script tests ST_VoronoiPolygons with collinear point configurations
-- which might be causing the "Invalid number of points in LinearRing found 2 - must be 0 or >= 4" error

-- Function to test Voronoi diagram generation with collinear point sets
CREATE OR REPLACE FUNCTION test_voronoi_collinear_points() RETURNS VOID AS $$
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
    -- Test 1: Three collinear points in a horizontal line
    -- Insert test data
    INSERT INTO voronoi_test_points (
        test_name, 
        test_description, 
        test_phase, 
        test_category,
        point_count,
        points
    ) VALUES (
        'Three Collinear Points Horizontal',
        'Three points arranged in a horizontal line',
        'phase2_edge_cases',
        'collinear',
        3,
        ST_Collect(ARRAY[
            ST_SetSRID(ST_MakePoint(0, 500), 3857),
            ST_SetSRID(ST_MakePoint(500, 500), 3857),
            ST_SetSRID(ST_MakePoint(1000, 500), 3857)
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
    RAISE NOTICE 'Test "Three Collinear Points Horizontal": %', CASE WHEN success THEN 'SUCCESS' ELSE 'FAILURE: ' || error_message END;
    
    -- Test 2: Three collinear points in a vertical line
    -- Insert test data
    INSERT INTO voronoi_test_points (
        test_name, 
        test_description, 
        test_phase, 
        test_category,
        point_count,
        points
    ) VALUES (
        'Three Collinear Points Vertical',
        'Three points arranged in a vertical line',
        'phase2_edge_cases',
        'collinear',
        3,
        ST_Collect(ARRAY[
            ST_SetSRID(ST_MakePoint(500, 0), 3857),
            ST_SetSRID(ST_MakePoint(500, 500), 3857),
            ST_SetSRID(ST_MakePoint(500, 1000), 3857)
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
    RAISE NOTICE 'Test "Three Collinear Points Vertical": %', CASE WHEN success THEN 'SUCCESS' ELSE 'FAILURE: ' || error_message END;
    
    -- Test 3: Three collinear points in a diagonal line
    -- Insert test data
    INSERT INTO voronoi_test_points (
        test_name, 
        test_description, 
        test_phase, 
        test_category,
        point_count,
        points
    ) VALUES (
        'Three Collinear Points Diagonal',
        'Three points arranged in a diagonal line',
        'phase2_edge_cases',
        'collinear',
        3,
        ST_Collect(ARRAY[
            ST_SetSRID(ST_MakePoint(0, 0), 3857),
            ST_SetSRID(ST_MakePoint(500, 500), 3857),
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
    RAISE NOTICE 'Test "Three Collinear Points Diagonal": %', CASE WHEN success THEN 'SUCCESS' ELSE 'FAILURE: ' || error_message END;
    
    -- Test 4: Many collinear points in a line
    -- Insert test data
    INSERT INTO voronoi_test_points (
        test_name, 
        test_description, 
        test_phase, 
        test_category,
        point_count,
        points
    ) VALUES (
        'Many Collinear Points',
        'Ten points arranged in a straight line',
        'phase2_edge_cases',
        'collinear',
        10,
        ST_Collect(ARRAY[
            ST_SetSRID(ST_MakePoint(0, 0), 3857),
            ST_SetSRID(ST_MakePoint(100, 100), 3857),
            ST_SetSRID(ST_MakePoint(200, 200), 3857),
            ST_SetSRID(ST_MakePoint(300, 300), 3857),
            ST_SetSRID(ST_MakePoint(400, 400), 3857),
            ST_SetSRID(ST_MakePoint(500, 500), 3857),
            ST_SetSRID(ST_MakePoint(600, 600), 3857),
            ST_SetSRID(ST_MakePoint(700, 700), 3857),
            ST_SetSRID(ST_MakePoint(800, 800), 3857),
            ST_SetSRID(ST_MakePoint(900, 900), 3857)
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
    RAISE NOTICE 'Test "Many Collinear Points": %', CASE WHEN success THEN 'SUCCESS' ELSE 'FAILURE: ' || error_message END;
    
    -- Test 5: Collinear points with one additional non-collinear point
    -- Insert test data
    INSERT INTO voronoi_test_points (
        test_name, 
        test_description, 
        test_phase, 
        test_category,
        point_count,
        points
    ) VALUES (
        'Collinear Points Plus One',
        'Three collinear points plus one non-collinear point',
        'phase2_edge_cases',
        'collinear',
        4,
        ST_Collect(ARRAY[
            ST_SetSRID(ST_MakePoint(0, 0), 3857),
            ST_SetSRID(ST_MakePoint(500, 500), 3857),
            ST_SetSRID(ST_MakePoint(1000, 1000), 3857),
            ST_SetSRID(ST_MakePoint(500, 0), 3857)  -- Non-collinear point
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
    RAISE NOTICE 'Test "Collinear Points Plus One": %', CASE WHEN success THEN 'SUCCESS' ELSE 'FAILURE: ' || error_message END;
    
    -- Test 6: Two sets of collinear points forming an angle
    -- Insert test data
    INSERT INTO voronoi_test_points (
        test_name, 
        test_description, 
        test_phase, 
        test_category,
        point_count,
        points
    ) VALUES (
        'Two Sets of Collinear Points',
        'Two sets of collinear points forming an angle',
        'phase2_edge_cases',
        'collinear',
        5,
        ST_Collect(ARRAY[
            ST_SetSRID(ST_MakePoint(0, 0), 3857),
            ST_SetSRID(ST_MakePoint(500, 0), 3857),
            ST_SetSRID(ST_MakePoint(1000, 0), 3857),
            ST_SetSRID(ST_MakePoint(0, 500), 3857),
            ST_SetSRID(ST_MakePoint(0, 1000), 3857)
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
    RAISE NOTICE 'Test "Two Sets of Collinear Points": %', CASE WHEN success THEN 'SUCCESS' ELSE 'FAILURE: ' || error_message END;
END;
$$ LANGUAGE plpgsql;

-- Execute the test function
SELECT test_voronoi_collinear_points();

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
    p.test_phase = 'phase2_edge_cases' AND p.test_category = 'collinear'
ORDER BY 
    p.test_id;
