-- Create Test Tables for Voronoi Diagram Testing
-- This script creates the necessary tables for storing test data and results

-- Enable PostGIS if not already enabled
CREATE EXTENSION IF NOT EXISTS postgis;

-- Table for storing test point sets
DROP TABLE IF EXISTS voronoi_test_points CASCADE;
CREATE TABLE voronoi_test_points (
    test_id SERIAL PRIMARY KEY,
    test_name TEXT NOT NULL,
    test_description TEXT,
    test_phase TEXT NOT NULL,
    test_category TEXT NOT NULL,
    point_count INTEGER,
    points GEOMETRY(MULTIPOINT, 3857),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Table for storing test water obstacles (polygons)
DROP TABLE IF EXISTS voronoi_test_obstacles CASCADE;
CREATE TABLE voronoi_test_obstacles (
    test_id SERIAL PRIMARY KEY,
    test_name TEXT NOT NULL,
    test_description TEXT,
    test_phase TEXT NOT NULL,
    test_category TEXT NOT NULL,
    obstacle_count INTEGER,
    obstacles GEOMETRY(MULTIPOLYGON, 3857),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Table for storing test boundary points (extracted from obstacles)
DROP TABLE IF EXISTS voronoi_test_boundary_points CASCADE;
CREATE TABLE voronoi_test_boundary_points (
    test_id SERIAL PRIMARY KEY,
    obstacle_test_id INTEGER REFERENCES voronoi_test_obstacles(test_id),
    test_name TEXT NOT NULL,
    test_description TEXT,
    test_phase TEXT NOT NULL,
    test_category TEXT NOT NULL,
    point_count INTEGER,
    points GEOMETRY(MULTIPOINT, 3857),
    spacing NUMERIC, -- Spacing used for boundary point extraction
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Table for storing test results
DROP TABLE IF EXISTS voronoi_test_results CASCADE;
CREATE TABLE voronoi_test_results (
    result_id SERIAL PRIMARY KEY,
    test_id INTEGER NOT NULL, -- References either test_points.test_id or test_boundary_points.test_id
    test_type TEXT NOT NULL, -- 'points', 'obstacles', or 'boundary_points'
    success BOOLEAN NOT NULL,
    error_message TEXT,
    execution_time NUMERIC, -- in milliseconds
    voronoi_diagram GEOMETRY(GEOMETRYCOLLECTION, 3857),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Table for storing test parameters
DROP TABLE IF EXISTS voronoi_test_parameters CASCADE;
CREATE TABLE voronoi_test_parameters (
    param_id SERIAL PRIMARY KEY,
    result_id INTEGER REFERENCES voronoi_test_results(result_id),
    param_name TEXT NOT NULL,
    param_value TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Table for storing preprocessing steps
DROP TABLE IF EXISTS voronoi_test_preprocessing CASCADE;
CREATE TABLE voronoi_test_preprocessing (
    preproc_id SERIAL PRIMARY KEY,
    result_id INTEGER REFERENCES voronoi_test_results(result_id),
    step_name TEXT NOT NULL,
    step_description TEXT,
    input_geom GEOMETRY,
    output_geom GEOMETRY,
    success BOOLEAN NOT NULL,
    error_message TEXT,
    execution_time NUMERIC, -- in milliseconds
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Table for storing alternative approaches
DROP TABLE IF EXISTS voronoi_test_alternatives CASCADE;
CREATE TABLE voronoi_test_alternatives (
    alt_id SERIAL PRIMARY KEY,
    result_id INTEGER REFERENCES voronoi_test_results(result_id),
    approach_name TEXT NOT NULL,
    approach_description TEXT,
    success BOOLEAN NOT NULL,
    error_message TEXT,
    execution_time NUMERIC, -- in milliseconds
    result_geom GEOMETRY,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for better performance
CREATE INDEX idx_test_points_phase ON voronoi_test_points(test_phase);
CREATE INDEX idx_test_points_category ON voronoi_test_points(test_category);
CREATE INDEX idx_test_obstacles_phase ON voronoi_test_obstacles(test_phase);
CREATE INDEX idx_test_obstacles_category ON voronoi_test_obstacles(test_category);
CREATE INDEX idx_test_boundary_points_phase ON voronoi_test_boundary_points(test_phase);
CREATE INDEX idx_test_boundary_points_category ON voronoi_test_boundary_points(test_category);
CREATE INDEX idx_test_boundary_points_obstacle_id ON voronoi_test_boundary_points(obstacle_test_id);
CREATE INDEX idx_test_results_test_id ON voronoi_test_results(test_id);
CREATE INDEX idx_test_results_test_type ON voronoi_test_results(test_type);
CREATE INDEX idx_test_results_success ON voronoi_test_results(success);
CREATE INDEX idx_test_parameters_result_id ON voronoi_test_parameters(result_id);
CREATE INDEX idx_test_preprocessing_result_id ON voronoi_test_preprocessing(result_id);
CREATE INDEX idx_test_alternatives_result_id ON voronoi_test_alternatives(result_id);

-- Create spatial indexes
CREATE INDEX idx_test_points_geom ON voronoi_test_points USING GIST(points);
CREATE INDEX idx_test_obstacles_geom ON voronoi_test_obstacles USING GIST(obstacles);
CREATE INDEX idx_test_boundary_points_geom ON voronoi_test_boundary_points USING GIST(points);
CREATE INDEX idx_test_results_voronoi_geom ON voronoi_test_results USING GIST(voronoi_diagram);

-- Create a view for easy querying of test results
CREATE OR REPLACE VIEW voronoi_test_summary AS
SELECT 
    r.result_id,
    CASE 
        WHEN r.test_type = 'points' THEN p.test_name
        WHEN r.test_type = 'obstacles' THEN o.test_name
        WHEN r.test_type = 'boundary_points' THEN bp.test_name
    END AS test_name,
    CASE 
        WHEN r.test_type = 'points' THEN p.test_phase
        WHEN r.test_type = 'obstacles' THEN o.test_phase
        WHEN r.test_type = 'boundary_points' THEN bp.test_phase
    END AS test_phase,
    CASE 
        WHEN r.test_type = 'points' THEN p.test_category
        WHEN r.test_type = 'obstacles' THEN o.test_category
        WHEN r.test_type = 'boundary_points' THEN bp.test_category
    END AS test_category,
    r.test_type,
    r.success,
    r.error_message,
    r.execution_time,
    r.created_at
FROM 
    voronoi_test_results r
LEFT JOIN 
    voronoi_test_points p ON r.test_id = p.test_id AND r.test_type = 'points'
LEFT JOIN 
    voronoi_test_obstacles o ON r.test_id = o.test_id AND r.test_type = 'obstacles'
LEFT JOIN 
    voronoi_test_boundary_points bp ON r.test_id = bp.test_id AND r.test_type = 'boundary_points';

-- Log the creation of tables
SELECT 'Created test tables for Voronoi diagram testing' AS message;
