-- Simple test for ST_VoronoiPolygons with a small set of points
-- This script creates a small set of points and generates a Voronoi diagram

-- Create a test table for points
DROP TABLE IF EXISTS test_points;
CREATE TABLE test_points (
    id SERIAL PRIMARY KEY,
    geom GEOMETRY(POINT, 3857)
);

-- Insert a small set of well-distributed points
INSERT INTO test_points (geom)
VALUES 
    (ST_SetSRID(ST_MakePoint(0, 0), 3857)),
    (ST_SetSRID(ST_MakePoint(100, 0), 3857)),
    (ST_SetSRID(ST_MakePoint(0, 100), 3857)),
    (ST_SetSRID(ST_MakePoint(100, 100), 3857)),
    (ST_SetSRID(ST_MakePoint(50, 50), 3857));

-- Create a table for the Voronoi diagram
DROP TABLE IF EXISTS test_voronoi;
CREATE TABLE test_voronoi (
    id SERIAL PRIMARY KEY,
    geom GEOMETRY(POLYGON, 3857)
);

-- Generate Voronoi diagram
DO $$
DECLARE
    points_collection GEOMETRY;
    voronoi_polygons GEOMETRY;
    study_area_envelope GEOMETRY;
BEGIN
    -- Create a collection of points
    SELECT ST_Collect(geom) INTO points_collection FROM test_points;
    
    -- Create a study area envelope with some padding
    SELECT ST_Envelope(ST_Buffer(ST_Extent(geom), 50)) INTO study_area_envelope 
    FROM test_points;
    
    -- Generate Voronoi polygons
    SELECT ST_VoronoiPolygons(
        points_collection,
        0.0, -- tolerance
        study_area_envelope -- envelope to clip the result
    ) INTO voronoi_polygons;
    
    -- Insert the Voronoi polygons into the test_voronoi table
    INSERT INTO test_voronoi (geom)
    SELECT (ST_Dump(voronoi_polygons)).geom;
    
    -- Log the results
    RAISE NOTICE 'Generated % Voronoi polygons', (SELECT COUNT(*) FROM test_voronoi);
END $$;

-- Display the results
SELECT 'Number of points: ' || COUNT(*) FROM test_points;
SELECT 'Number of Voronoi polygons: ' || COUNT(*) FROM test_voronoi;

-- Verify that each Voronoi cell contains exactly one point
SELECT 
    v.id AS voronoi_id,
    COUNT(p.id) AS point_count
FROM 
    test_voronoi v
LEFT JOIN 
    test_points p ON ST_Contains(v.geom, p.geom)
GROUP BY 
    v.id
ORDER BY 
    v.id;
