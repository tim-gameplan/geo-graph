/*
 * Water Edges Diagnostic Script
 * 
 * This script diagnoses issues with water edge creation by examining
 * the spatial relationship between terrain grid points and water obstacles.
 */

-- Parameters:
-- :storage_srid - SRID for storage (default: 3857)

-- Check if required tables exist
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'water_obstacles') THEN
        RAISE EXCEPTION 'Table water_obstacles does not exist';
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'terrain_grid_points') THEN
        RAISE EXCEPTION 'Table terrain_grid_points does not exist';
    END IF;
END;
$$ LANGUAGE plpgsql;

-- 1. Count water obstacles and terrain grid points
SELECT 'Water obstacles count: ' || COUNT(*) FROM water_obstacles;
SELECT 'Terrain grid points count: ' || COUNT(*) FROM terrain_grid_points;

-- 2. Check water obstacle geometries
SELECT 
    ST_GeometryType(geom) AS geometry_type,
    COUNT(*) AS count
FROM 
    water_obstacles
GROUP BY 
    ST_GeometryType(geom);

-- 3. Calculate statistics about water obstacles
SELECT 
    MIN(ST_Area(geom)) AS min_area,
    AVG(ST_Area(geom)) AS avg_area,
    MAX(ST_Area(geom)) AS max_area,
    MIN(ST_Perimeter(geom)) AS min_perimeter,
    AVG(ST_Perimeter(geom)) AS avg_perimeter,
    MAX(ST_Perimeter(geom)) AS max_perimeter
FROM 
    water_obstacles;

-- 4. Calculate distances between terrain grid points
SELECT 
    MIN(ST_Distance(t1.geom, t2.geom)) AS min_distance,
    AVG(ST_Distance(t1.geom, t2.geom)) AS avg_distance,
    MAX(ST_Distance(t1.geom, t2.geom)) AS max_distance
FROM 
    terrain_grid_points t1,
    terrain_grid_points t2
WHERE 
    t1.id < t2.id AND
    ST_DWithin(t1.geom, t2.geom, 2000)
LIMIT 1000;

-- 5. Find terrain grid points near water obstacles
WITH terrain_near_water AS (
    SELECT 
        tgp.id AS terrain_point_id,
        wo.id AS water_obstacle_id,
        ST_Distance(tgp.geom, wo.geom) AS distance
    FROM 
        terrain_grid_points tgp,
        water_obstacles wo
    WHERE 
        ST_DWithin(tgp.geom, wo.geom, 1000)
)
SELECT 
    COUNT(DISTINCT terrain_point_id) AS terrain_points_near_water,
    COUNT(DISTINCT water_obstacle_id) AS water_obstacles_with_nearby_terrain,
    MIN(distance) AS min_distance,
    AVG(distance) AS avg_distance,
    MAX(distance) AS max_distance
FROM 
    terrain_near_water;

-- 6. Test the water boundary points extraction
WITH water_boundary_points AS (
    -- Get points along the boundary of water obstacles
    SELECT 
        wo.id AS water_obstacle_id,
        (ST_DumpPoints(ST_Boundary(wo.geom))).geom AS geom
    FROM 
        water_obstacles wo
)
SELECT 
    COUNT(*) AS total_boundary_points,
    COUNT(DISTINCT water_obstacle_id) AS water_obstacles_with_boundary_points
FROM 
    water_boundary_points;

-- 7. Test the nearest terrain points calculation
WITH water_boundary_points AS (
    -- Get points along the boundary of water obstacles
    SELECT 
        wo.id AS water_obstacle_id,
        (ST_DumpPoints(ST_Boundary(wo.geom))).geom AS geom
    FROM 
        water_obstacles wo
    LIMIT 100 -- Limit for performance
),
nearest_terrain_points AS (
    -- For each water boundary point, find the nearest terrain grid point
    SELECT DISTINCT ON (wbp.geom)
        wbp.water_obstacle_id,
        wbp.geom AS water_point,
        tg.id AS terrain_point_id,
        tg.geom AS terrain_point,
        ST_Distance(wbp.geom, tg.geom) AS distance
    FROM 
        water_boundary_points wbp
    CROSS JOIN 
        terrain_grid_points tg
    ORDER BY 
        wbp.geom, ST_Distance(wbp.geom, tg.geom)
)
SELECT 
    COUNT(*) AS total_nearest_points,
    MIN(distance) AS min_distance,
    AVG(distance) AS avg_distance,
    MAX(distance) AS max_distance,
    COUNT(DISTINCT water_obstacle_id) AS water_obstacles_with_nearest_points
FROM 
    nearest_terrain_points;

-- 8. Test the water edge creation with different distance thresholds
WITH water_boundary_points AS (
    -- Get points along the boundary of water obstacles
    SELECT 
        wo.id AS water_obstacle_id,
        (ST_DumpPoints(ST_Boundary(wo.geom))).geom AS geom
    FROM 
        water_obstacles wo
    LIMIT 100 -- Limit for performance
),
nearest_terrain_points AS (
    -- For each water boundary point, find the nearest terrain grid point
    SELECT DISTINCT ON (wbp.geom)
        wbp.water_obstacle_id,
        wbp.geom AS water_point,
        tg.id AS terrain_point_id,
        tg.geom AS terrain_point,
        ST_Distance(wbp.geom, tg.geom) AS distance
    FROM 
        water_boundary_points wbp
    CROSS JOIN 
        terrain_grid_points tg
    ORDER BY 
        wbp.geom, ST_Distance(wbp.geom, tg.geom)
)
SELECT 
    threshold,
    COUNT(*) AS potential_edges
FROM (
    SELECT 
        1000 AS threshold,
        ntp1.terrain_point_id AS source_id,
        ntp2.terrain_point_id AS target_id
    FROM 
        nearest_terrain_points ntp1
    JOIN 
        nearest_terrain_points ntp2 ON ntp1.water_obstacle_id = ntp2.water_obstacle_id
    WHERE 
        ntp1.terrain_point_id < ntp2.terrain_point_id AND
        ST_DWithin(ntp1.terrain_point, ntp2.terrain_point, 1000) AND
        EXISTS (
            SELECT 1
            FROM water_obstacles wo
            WHERE 
                wo.id = ntp1.water_obstacle_id AND
                ST_Intersects(wo.geom, ST_MakeLine(ntp1.terrain_point, ntp2.terrain_point))
        )
    UNION ALL
    SELECT 
        2000 AS threshold,
        ntp1.terrain_point_id AS source_id,
        ntp2.terrain_point_id AS target_id
    FROM 
        nearest_terrain_points ntp1
    JOIN 
        nearest_terrain_points ntp2 ON ntp1.water_obstacle_id = ntp2.water_obstacle_id
    WHERE 
        ntp1.terrain_point_id < ntp2.terrain_point_id AND
        ST_DWithin(ntp1.terrain_point, ntp2.terrain_point, 2000) AND
        EXISTS (
            SELECT 1
            FROM water_obstacles wo
            WHERE 
                wo.id = ntp1.water_obstacle_id AND
                ST_Intersects(wo.geom, ST_MakeLine(ntp1.terrain_point, ntp2.terrain_point))
        )
    UNION ALL
    SELECT 
        3000 AS threshold,
        ntp1.terrain_point_id AS source_id,
        ntp2.terrain_point_id AS target_id
    FROM 
        nearest_terrain_points ntp1
    JOIN 
        nearest_terrain_points ntp2 ON ntp1.water_obstacle_id = ntp2.water_obstacle_id
    WHERE 
        ntp1.terrain_point_id < ntp2.terrain_point_id AND
        ST_DWithin(ntp1.terrain_point, ntp2.terrain_point, 3000) AND
        EXISTS (
            SELECT 1
            FROM water_obstacles wo
            WHERE 
                wo.id = ntp1.water_obstacle_id AND
                ST_Intersects(wo.geom, ST_MakeLine(ntp1.terrain_point, ntp2.terrain_point))
        )
) AS potential_edges
GROUP BY 
    threshold
ORDER BY 
    threshold;

-- 9. Test the intersection requirement
WITH water_boundary_points AS (
    -- Get points along the boundary of water obstacles
    SELECT 
        wo.id AS water_obstacle_id,
        (ST_DumpPoints(ST_Boundary(wo.geom))).geom AS geom
    FROM 
        water_obstacles wo
    LIMIT 100 -- Limit for performance
),
nearest_terrain_points AS (
    -- For each water boundary point, find the nearest terrain grid point
    SELECT DISTINCT ON (wbp.geom)
        wbp.water_obstacle_id,
        wbp.geom AS water_point,
        tg.id AS terrain_point_id,
        tg.geom AS terrain_point,
        ST_Distance(wbp.geom, tg.geom) AS distance
    FROM 
        water_boundary_points wbp
    CROSS JOIN 
        terrain_grid_points tg
    ORDER BY 
        wbp.geom, ST_Distance(wbp.geom, tg.geom)
)
SELECT 
    'With intersection requirement' AS test,
    COUNT(*) AS potential_edges
FROM (
    SELECT 
        ntp1.terrain_point_id AS source_id,
        ntp2.terrain_point_id AS target_id
    FROM 
        nearest_terrain_points ntp1
    JOIN 
        nearest_terrain_points ntp2 ON ntp1.water_obstacle_id = ntp2.water_obstacle_id
    WHERE 
        ntp1.terrain_point_id < ntp2.terrain_point_id AND
        ST_DWithin(ntp1.terrain_point, ntp2.terrain_point, 2000) AND
        EXISTS (
            SELECT 1
            FROM water_obstacles wo
            WHERE 
                wo.id = ntp1.water_obstacle_id AND
                ST_Intersects(wo.geom, ST_MakeLine(ntp1.terrain_point, ntp2.terrain_point))
        )
) AS with_intersection
UNION ALL
SELECT 
    'Without intersection requirement' AS test,
    COUNT(*) AS potential_edges
FROM (
    SELECT 
        ntp1.terrain_point_id AS source_id,
        ntp2.terrain_point_id AS target_id
    FROM 
        nearest_terrain_points ntp1
    JOIN 
        nearest_terrain_points ntp2 ON ntp1.water_obstacle_id = ntp2.water_obstacle_id
    WHERE 
        ntp1.terrain_point_id < ntp2.terrain_point_id AND
        ST_DWithin(ntp1.terrain_point, ntp2.terrain_point, 2000)
) AS without_intersection;
