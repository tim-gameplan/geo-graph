-- Enhanced version of create_edge_tables.sql
-- Preserves additional attributes from water_polys when creating water_edges

-- Create water_edges table from water_buf and water_polys
DROP TABLE IF EXISTS water_edges CASCADE;
CREATE TABLE water_edges AS
SELECT 
    wb.id,
    NULL::bigint AS source,
    NULL::bigint AS target,
    1000.0 AS cost, -- High cost to discourage crossing water
    ST_Boundary(wb.geom) AS geom,
    wp.name,
    wp.width,
    wp.intermittent,
    wp.water_type
FROM water_buf wb
JOIN water_polys wp ON wb.id = wp.id;

-- Create terrain_edges table from terrain_grid
DROP TABLE IF EXISTS terrain_edges CASCADE;
CREATE TABLE terrain_edges AS
WITH 
points AS (
    SELECT 
        ROW_NUMBER() OVER () AS id,
        ST_Centroid(geom) AS geom,
        cost
    FROM terrain_grid
),
edges AS (
    SELECT 
        ROW_NUMBER() OVER () AS id,
        a.id AS source_id,
        b.id AS target_id,
        (a.cost + b.cost) / 2 AS cost,
        ST_MakeLine(a.geom, b.geom) AS geom
    FROM points a
    JOIN points b ON ST_DWithin(a.geom, b.geom, 300) -- Connect points within 300m
    WHERE a.id < b.id -- Avoid duplicate edges
)
SELECT 
    id,
    NULL::bigint AS source,
    NULL::bigint AS target,
    cost,
    geom
FROM edges;

-- Create indexes
CREATE INDEX ON water_edges USING GIST(geom);
CREATE INDEX ON terrain_edges USING GIST(geom);
