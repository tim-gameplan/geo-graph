-- Query OSM Attributes in the PostGIS Database
-- This script provides examples of SQL queries to explore OSM attributes

-- 1. List all tables in the database
SELECT table_name 
FROM information_schema.tables 
WHERE table_schema = 'public'
ORDER BY table_name;

-- 2. List all columns in the planet_osm_line table
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_name = 'planet_osm_line'
ORDER BY ordinal_position;

-- 3. List all columns in the planet_osm_polygon table
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_name = 'planet_osm_polygon'
ORDER BY ordinal_position;

-- 4. Count the number of different highway types
SELECT highway, COUNT(*) as count
FROM planet_osm_line
WHERE highway IS NOT NULL
GROUP BY highway
ORDER BY count DESC;

-- 5. Count the number of different water types
SELECT 
    CASE
        WHEN water IS NOT NULL THEN 'water=' || water
        WHEN "natural" = 'water' THEN 'natural=water'
        WHEN landuse = 'reservoir' THEN 'landuse=reservoir'
        ELSE 'other'
    END AS water_type,
    COUNT(*) as count
FROM planet_osm_polygon
WHERE water IS NOT NULL
   OR "natural" = 'water'
   OR landuse = 'reservoir'
GROUP BY water_type
ORDER BY count DESC;

-- 6. Find roads with names
SELECT name, highway, osm_id, ST_Length(way) as length
FROM planet_osm_line
WHERE name IS NOT NULL AND highway IS NOT NULL
ORDER BY length DESC
LIMIT 10;

-- 7. Find water features with names
SELECT name, water, "natural", landuse, osm_id, ST_Area(way) as area
FROM planet_osm_polygon
WHERE name IS NOT NULL 
  AND (water IS NOT NULL OR "natural" = 'water' OR landuse = 'reservoir')
ORDER BY area DESC
LIMIT 10;

-- 8. Count the number of roads by surface type
SELECT surface, COUNT(*) as count
FROM planet_osm_line
WHERE highway IS NOT NULL AND surface IS NOT NULL
GROUP BY surface
ORDER BY count DESC;

-- 9. Count the number of roads by maximum speed
SELECT maxspeed, COUNT(*) as count
FROM planet_osm_line
WHERE highway IS NOT NULL AND maxspeed IS NOT NULL
GROUP BY maxspeed
ORDER BY count DESC;

-- 10. Count the number of one-way roads
SELECT oneway, COUNT(*) as count
FROM planet_osm_line
WHERE highway IS NOT NULL AND oneway IS NOT NULL
GROUP BY oneway
ORDER BY count DESC;

-- 11. Count the number of bridges and tunnels
SELECT 
    CASE
        WHEN bridge IS NOT NULL THEN 'bridge'
        WHEN tunnel IS NOT NULL THEN 'tunnel'
        ELSE 'neither'
    END AS structure_type,
    COUNT(*) as count
FROM planet_osm_line
WHERE highway IS NOT NULL
GROUP BY structure_type
ORDER BY count DESC;

-- 12. Find roads with the most lanes
SELECT name, highway, lanes, osm_id, ST_Length(way) as length
FROM planet_osm_line
WHERE lanes IS NOT NULL AND highway IS NOT NULL
ORDER BY lanes::integer DESC, length DESC
LIMIT 10;

-- 13. Count the number of roads by access type
SELECT access, COUNT(*) as count
FROM planet_osm_line
WHERE highway IS NOT NULL AND access IS NOT NULL
GROUP BY access
ORDER BY count DESC;

-- 14. Count the number of intermittent water features
SELECT intermittent, COUNT(*) as count
FROM planet_osm_polygon
WHERE (water IS NOT NULL OR "natural" = 'water' OR landuse = 'reservoir')
  AND intermittent IS NOT NULL
GROUP BY intermittent
ORDER BY count DESC;

-- 15. List all attributes in the road_edges table
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_name = 'road_edges'
ORDER BY ordinal_position;

-- 16. List all attributes in the water_polys table
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_name = 'water_polys'
ORDER BY ordinal_position;

-- 17. Compare the number of attributes in the original OSM tables vs. the derived tables
SELECT 
    'planet_osm_line' as table_name,
    COUNT(*) as column_count
FROM information_schema.columns
WHERE table_name = 'planet_osm_line'
UNION ALL
SELECT 
    'road_edges' as table_name,
    COUNT(*) as column_count
FROM information_schema.columns
WHERE table_name = 'road_edges'
UNION ALL
SELECT 
    'planet_osm_polygon' as table_name,
    COUNT(*) as column_count
FROM information_schema.columns
WHERE table_name = 'planet_osm_polygon'
UNION ALL
SELECT 
    'water_polys' as table_name,
    COUNT(*) as column_count
FROM information_schema.columns
WHERE table_name = 'water_polys'
ORDER BY table_name;

-- 18. List all attributes in the unified_edges table
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_name = 'unified_edges'
ORDER BY ordinal_position;

-- 19. Count the number of edges in each edge table
SELECT 'road_edges' as table_name, COUNT(*) as edge_count FROM road_edges
UNION ALL
SELECT 'water_edges' as table_name, COUNT(*) as edge_count FROM water_edges
UNION ALL
SELECT 'terrain_edges' as table_name, COUNT(*) as edge_count FROM terrain_edges
UNION ALL
SELECT 'unified_edges' as table_name, COUNT(*) as edge_count FROM unified_edges
ORDER BY table_name;

-- 20. Find the bounding box of the data
SELECT 
    ST_XMin(ST_Extent(way)) as min_x,
    ST_YMin(ST_Extent(way)) as min_y,
    ST_XMax(ST_Extent(way)) as max_x,
    ST_YMax(ST_Extent(way)) as max_y
FROM planet_osm_line;
