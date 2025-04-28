-- Cleanup Script for Voronoi Diagram Testing
-- This script drops all tables and views created for the Voronoi testing

-- Drop the view first
DROP VIEW IF EXISTS voronoi_test_summary;

-- Drop tables in reverse order of dependencies
DROP TABLE IF EXISTS voronoi_test_alternatives CASCADE;
DROP TABLE IF EXISTS voronoi_test_preprocessing CASCADE;
DROP TABLE IF EXISTS voronoi_test_parameters CASCADE;
DROP TABLE IF EXISTS voronoi_test_results CASCADE;
DROP TABLE IF EXISTS voronoi_test_boundary_points CASCADE;
DROP TABLE IF EXISTS voronoi_test_obstacles CASCADE;
DROP TABLE IF EXISTS voronoi_test_points CASCADE;

-- Log the cleanup
SELECT 'Cleaned up all Voronoi test tables and views' AS message;
