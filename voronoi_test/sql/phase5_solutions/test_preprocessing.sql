-- Test Preprocessing Solutions for Voronoi Diagram Generation
-- This script tests various preprocessing techniques to solve the
-- "Invalid number of points in LinearRing found 2 - must be 0 or >= 4" error

-- Function to test Voronoi diagram generation with different preprocessing techniques
CREATE OR REPLACE FUNCTION test_voronoi_preprocessing_solutions() RETURNS VOID AS $$
DECLARE
    test_id INTEGER;
    result_id INTEGER;
    start_time TIMESTAMP;
    end_time TIMESTAMP;
    execution_time NUMERIC;
    voronoi_result GEOMETRY;
    error_message TEXT;
    success BOOLEAN;
    problematic_points GEOMETRY;
    preprocessed_points GEOMETRY;
    envelope GEOMETRY;
    tolerance NUMERIC;
BEGIN
    -- Create a set of problematic points known to cause the error
    -- This includes collinear points and coincident points
    problematic_points := ST_Collect(ARRAY[
        -- Collinear points
        ST_SetSRID(ST_MakePoint(0, 0), 3857),
        ST_SetSRID(ST_MakePoint(500, 500), 3857),
        ST_SetSRID(ST_MakePoint(1000, 1000), 3857),
        -- Coincident points
        ST_SetSRID(ST_MakePoint(250, 250), 3857),
        ST_SetSRID(ST_MakePoint(250, 250), 3857),
        -- Nearly coincident points
        ST_SetSRID(ST_MakePoint(750, 750), 3857),
        ST_SetSRID(ST_MakePoint(750.0001, 750.0001), 3857),
        -- Points on envelope boundary
        ST_SetSRID(ST_MakePoint(0, 1000), 3857),
        ST_SetSRID(ST_MakePoint(1000, 0), 3857)
    ]);
    
    -- Create an envelope
    envelope := ST_Envelope(problematic_points);
    
    -- Insert test data for the problematic points
    INSERT INTO voronoi_test_points (
        test_name, 
        test_description, 
        test_phase, 
        test_category,
        point_count,
        points
    ) VALUES (
        'Problematic Points Baseline',
        'Set of points known to cause the "Invalid number of points in LinearRing found 2 - must be 0 or >= 4" error',
        'phase5_solutions',
        'preprocessing',
        ST_NumGeometries(problematic_points),
        problematic_points
    ) RETURNING test_id INTO test_id;
    
    -- Run the baseline test (expected to fail)
    BEGIN
        start_time := clock_timestamp();
        voronoi_result := ST_VoronoiPolygons(
            problematic_points,
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
        'baseline',
        success,
        error_message,
        execution_time,
        voronoi_result
    ) RETURNING result_id INTO result_id;
    
    -- Log the result
    RAISE NOTICE 'Test "Problematic Points Baseline": %', CASE WHEN success THEN 'SUCCESS' ELSE 'FAILURE: ' || error_message END;
    
    -- Solution 1: Use ST_UnaryUnion to remove duplicate points
    preprocessed_points := ST_UnaryUnion(problematic_points);
    
    -- Insert test data for the preprocessed points
    INSERT INTO voronoi_test_points (
        test_name, 
        test_description, 
        test_phase, 
        test_category,
        point_count,
        points
    ) VALUES (
        'Solution 1: Remove Duplicates',
        'Using ST_UnaryUnion to remove duplicate points',
        'phase5_solutions',
        'preprocessing',
        ST_NumGeometries(preprocessed_points),
        preprocessed_points
    ) RETURNING test_id INTO test_id;
    
    -- Run the test with preprocessed points
    BEGIN
        start_time := clock_timestamp();
        voronoi_result := ST_VoronoiPolygons(
            preprocessed_points,
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
        'preprocessing',
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
        'Used ST_UnaryUnion to remove duplicate points'
    );
    
    -- Log the result
    RAISE NOTICE 'Test "Solution 1: Remove Duplicates": %', CASE WHEN success THEN 'SUCCESS' ELSE 'FAILURE: ' || error_message END;
    
    -- Solution 2: Add small random offsets to points
    WITH points_array AS (
        SELECT (ST_Dump(problematic_points)).geom AS geom
    ),
    jittered_points AS (
        SELECT ST_Translate(
            geom,
            (random() - 0.5) * 0.01, -- Small random X offset
            (random() - 0.5) * 0.01  -- Small random Y offset
        ) AS geom
        FROM points_array
    )
    SELECT ST_Collect(geom) INTO preprocessed_points
    FROM jittered_points;
    
    -- Insert test data for the preprocessed points
    INSERT INTO voronoi_test_points (
        test_name, 
        test_description, 
        test_phase, 
        test_category,
        point_count,
        points
    ) VALUES (
        'Solution 2: Add Random Offsets',
        'Adding small random offsets to points to break collinearity and coincidence',
        'phase5_solutions',
        'preprocessing',
        ST_NumGeometries(preprocessed_points),
        preprocessed_points
    ) RETURNING test_id INTO test_id;
    
    -- Run the test with preprocessed points
    BEGIN
        start_time := clock_timestamp();
        voronoi_result := ST_VoronoiPolygons(
            preprocessed_points,
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
        'preprocessing',
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
        'jittering',
        'Added small random offsets to points to break collinearity and coincidence'
    );
    
    -- Log the result
    RAISE NOTICE 'Test "Solution 2: Add Random Offsets": %', CASE WHEN success THEN 'SUCCESS' ELSE 'FAILURE: ' || error_message END;
    
    -- Solution 3: Use a non-zero tolerance value
    tolerance := 0.1; -- Use a small tolerance value
    
    -- Insert test data for the original problematic points
    INSERT INTO voronoi_test_points (
        test_name, 
        test_description, 
        test_phase, 
        test_category,
        point_count,
        points
    ) VALUES (
        'Solution 3: Use Tolerance',
        'Using a non-zero tolerance value (' || tolerance || ') with ST_VoronoiPolygons',
        'phase5_solutions',
        'preprocessing',
        ST_NumGeometries(problematic_points),
        problematic_points
    ) RETURNING test_id INTO test_id;
    
    -- Run the test with a tolerance value
    BEGIN
        start_time := clock_timestamp();
        voronoi_result := ST_VoronoiPolygons(
            problematic_points,
            tolerance,
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
        'tolerance',
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
        tolerance::TEXT
    );
    
    -- Log the result
    RAISE NOTICE 'Test "Solution 3: Use Tolerance": %', CASE WHEN success THEN 'SUCCESS' ELSE 'FAILURE: ' || error_message END;
    
    -- Solution 4: Expanded envelope
    envelope := ST_Expand(envelope, 100);
    
    -- Insert test data for the original problematic points
    INSERT INTO voronoi_test_points (
        test_name, 
        test_description, 
        test_phase, 
        test_category,
        point_count,
        points
    ) VALUES (
        'Solution 4: Expanded Envelope',
        'Using an expanded envelope to avoid points on the boundary',
        'phase5_solutions',
        'preprocessing',
        ST_NumGeometries(problematic_points),
        problematic_points
    ) RETURNING test_id INTO test_id;
    
    -- Run the test with an expanded envelope
    BEGIN
        start_time := clock_timestamp();
        voronoi_result := ST_VoronoiPolygons(
            problematic_points,
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
    RAISE NOTICE 'Test "Solution 4: Expanded Envelope": %', CASE WHEN success THEN 'SUCCESS' ELSE 'FAILURE: ' || error_message END;
    
    -- Solution 5: Combined approach (deduplication + tolerance + expanded envelope)
    preprocessed_points := ST_UnaryUnion(problematic_points);
    tolerance := 0.1;
    envelope := ST_Expand(ST_Envelope(preprocessed_points), 100);
    
    -- Insert test data for the preprocessed points
    INSERT INTO voronoi_test_points (
        test_name, 
        test_description, 
        test_phase, 
        test_category,
        point_count,
        points
    ) VALUES (
        'Solution 5: Combined Approach',
        'Combining deduplication, tolerance, and expanded envelope',
        'phase5_solutions',
        'preprocessing',
        ST_NumGeometries(preprocessed_points),
        preprocessed_points
    ) RETURNING test_id INTO test_id;
    
    -- Run the test with the combined approach
    BEGIN
        start_time := clock_timestamp();
        voronoi_result := ST_VoronoiPolygons(
            preprocessed_points,
            tolerance,
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
        'combined',
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
        'combined',
        'Combined deduplication, tolerance, and expanded envelope'
    );
    
    -- Store the tolerance parameter
    INSERT INTO voronoi_test_parameters (
        result_id,
        param_name,
        param_value
    ) VALUES (
        result_id,
        'tolerance',
        tolerance::TEXT
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
    RAISE NOTICE 'Test "Solution 5: Combined Approach": %', CASE WHEN success THEN 'SUCCESS' ELSE 'FAILURE: ' || error_message END;
END;
$$ LANGUAGE plpgsql;

-- Execute the test function
SELECT test_voronoi_preprocessing_solutions();

-- Query to view the results
SELECT 
    p.test_name,
    r.success,
    r.error_message,
    r.execution_time,
    pp.preprocessing_type,
    pp.description,
    param.param_name,
    param.param_value
FROM 
    voronoi_test_results r
JOIN 
    voronoi_test_points p ON r.test_id = p.test_id
LEFT JOIN
    voronoi_test_preprocessing pp ON r.result_id = pp.result_id
LEFT JOIN
    voronoi_test_parameters param ON r.result_id = param.result_id
WHERE 
    p.test_phase = 'phase5_solutions' AND p.test_category = 'preprocessing'
ORDER BY 
    p.test_id, param.param_name;

-- Generate a summary of solution effectiveness
SELECT 
    p.test_name,
    r.success,
    r.execution_time,
    CASE 
        WHEN r.success THEN 'EFFECTIVE'
        ELSE 'INEFFECTIVE'
    END AS solution_effectiveness
FROM 
    voronoi_test_results r
JOIN 
    voronoi_test_points p ON r.test_id = p.test_id
WHERE 
    p.test_phase = 'phase5_solutions' AND p.test_category = 'preprocessing'
ORDER BY 
    r.success DESC, r.execution_time ASC;
