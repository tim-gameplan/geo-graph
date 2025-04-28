-- Test Performance Scaling for Voronoi Diagram Generation
-- This script tests ST_VoronoiPolygons with increasing numbers of points
-- to evaluate performance and identify potential issues with larger datasets

-- Function to generate random points within a specified extent
CREATE OR REPLACE FUNCTION generate_random_points(
    num_points INTEGER,
    min_x NUMERIC,
    min_y NUMERIC,
    max_x NUMERIC,
    max_y NUMERIC,
    srid INTEGER
) RETURNS GEOMETRY AS $$
DECLARE
    points GEOMETRY[];
    i INTEGER;
    x NUMERIC;
    y NUMERIC;
BEGIN
    FOR i IN 1..num_points LOOP
        -- Generate random coordinates within the specified extent
        x := min_x + (max_x - min_x) * random();
        y := min_y + (max_y - min_y) * random();
        points[i] := ST_SetSRID(ST_MakePoint(x, y), srid);
    END LOOP;
    
    RETURN ST_Collect(points);
END;
$$ LANGUAGE plpgsql;

-- Function to test Voronoi diagram generation with different numbers of points
CREATE OR REPLACE FUNCTION test_voronoi_performance_scaling() RETURNS VOID AS $$
DECLARE
    test_id INTEGER;
    result_id INTEGER;
    start_time TIMESTAMP;
    end_time TIMESTAMP;
    execution_time NUMERIC;
    voronoi_result GEOMETRY;
    error_message TEXT;
    success BOOLEAN;
    random_points GEOMETRY;
    point_counts INTEGER[] := ARRAY[10, 50, 100, 500, 1000, 2000, 5000];
    count INTEGER;
    envelope GEOMETRY;
BEGIN
    -- Loop through different point counts
    FOREACH count IN ARRAY point_counts LOOP
        -- Generate random points
        random_points := generate_random_points(
            count,
            0, 0,
            10000, 10000,
            3857
        );
        
        -- Create an envelope
        envelope := ST_Expand(ST_Envelope(random_points), 100);
        
        -- Insert test data
        INSERT INTO voronoi_test_points (
            test_name, 
            test_description, 
            test_phase, 
            test_category,
            point_count,
            points
        ) VALUES (
            'Performance Test ' || count || ' Points',
            'Performance test with ' || count || ' randomly generated points',
            'phase4_performance',
            'scaling',
            count,
            random_points
        ) RETURNING test_id INTO test_id;
        
        -- Run the test
        BEGIN
            start_time := clock_timestamp();
            voronoi_result := ST_VoronoiPolygons(
                random_points,
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
            'performance',
            success,
            error_message,
            execution_time,
            voronoi_result
        ) RETURNING result_id INTO result_id;
        
        -- Store the point count parameter
        INSERT INTO voronoi_test_parameters (
            result_id,
            param_name,
            param_value
        ) VALUES (
            result_id,
            'point_count',
            count::TEXT
        );
        
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
        RAISE NOTICE 'Test "Performance Test % Points": % (% ms)', 
            count, 
            CASE WHEN success THEN 'SUCCESS' ELSE 'FAILURE: ' || error_message END,
            execution_time;
    END LOOP;
    
    -- Test with a very large number of points (if system can handle it)
    -- This is in a separate try-catch block to avoid affecting the other tests
    BEGIN
        -- Generate 10,000 random points
        random_points := generate_random_points(
            10000,
            0, 0,
            10000, 10000,
            3857
        );
        
        -- Create an envelope
        envelope := ST_Expand(ST_Envelope(random_points), 100);
        
        -- Insert test data
        INSERT INTO voronoi_test_points (
            test_name, 
            test_description, 
            test_phase, 
            test_category,
            point_count,
            points
        ) VALUES (
            'Performance Test 10000 Points',
            'Performance test with 10000 randomly generated points',
            'phase4_performance',
            'scaling',
            10000,
            random_points
        ) RETURNING test_id INTO test_id;
        
        -- Run the test
        BEGIN
            start_time := clock_timestamp();
            voronoi_result := ST_VoronoiPolygons(
                random_points,
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
            'performance',
            success,
            error_message,
            execution_time,
            voronoi_result
        ) RETURNING result_id INTO result_id;
        
        -- Store the point count parameter
        INSERT INTO voronoi_test_parameters (
            result_id,
            param_name,
            param_value
        ) VALUES (
            result_id,
            'point_count',
            '10000'
        );
        
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
        RAISE NOTICE 'Test "Performance Test 10000 Points": % (% ms)', 
            CASE WHEN success THEN 'SUCCESS' ELSE 'FAILURE: ' || error_message END,
            execution_time;
    EXCEPTION WHEN OTHERS THEN
        RAISE NOTICE 'Test "Performance Test 10000 Points": SKIPPED (system could not handle it)';
    END;
END;
$$ LANGUAGE plpgsql;

-- Execute the test function
SELECT test_voronoi_performance_scaling();

-- Query to view the results
SELECT 
    p.test_name,
    p.point_count,
    r.success,
    r.error_message,
    r.execution_time,
    CASE 
        WHEN r.success THEN ST_NumGeometries(r.voronoi_diagram)
        ELSE NULL
    END AS num_voronoi_cells
FROM 
    voronoi_test_results r
JOIN 
    voronoi_test_points p ON r.test_id = p.test_id
WHERE 
    p.test_phase = 'phase4_performance' AND p.test_category = 'scaling'
ORDER BY 
    p.point_count;

-- Generate a performance report
SELECT 
    p.point_count,
    AVG(r.execution_time) AS avg_execution_time_ms,
    MIN(r.execution_time) AS min_execution_time_ms,
    MAX(r.execution_time) AS max_execution_time_ms,
    COUNT(*) AS num_tests,
    SUM(CASE WHEN r.success THEN 1 ELSE 0 END) AS num_successful,
    SUM(CASE WHEN r.success THEN 0 ELSE 1 END) AS num_failed
FROM 
    voronoi_test_results r
JOIN 
    voronoi_test_points p ON r.test_id = p.test_id
WHERE 
    p.test_phase = 'phase4_performance' AND p.test_category = 'scaling'
GROUP BY 
    p.point_count
ORDER BY 
    p.point_count;
