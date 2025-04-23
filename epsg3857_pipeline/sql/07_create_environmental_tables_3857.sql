-- Create environmental tables with EPSG:3857 coordinates
-- Parameters:
-- :storage_srid - SRID for storage (default: 3857)
-- :default_speed - Default speed in m/s (default: 5.0)
-- :water_speed_factor - Speed factor for water edges (default: 0.2)
-- :uphill_speed_factor - Speed factor for uphill edges (default: 0.8)
-- :downhill_speed_factor - Speed factor for downhill edges (default: 1.2)

-- Create environmental conditions table
DROP TABLE IF EXISTS environmental_conditions CASCADE;
CREATE TABLE environmental_conditions (
    id SERIAL PRIMARY KEY,
    edge_id INTEGER REFERENCES unified_edges(id),
    condition_type TEXT,
    speed_factor NUMERIC,
    description TEXT
);

-- Add water conditions
INSERT INTO environmental_conditions (edge_id, condition_type, speed_factor, description)
SELECT 
    id,
    'water',
    :water_speed_factor,
    'Water obstacle'
FROM 
    unified_edges
WHERE 
    edge_type = 'water';

-- Create a table for elevation data
DROP TABLE IF EXISTS elevation_data CASCADE;
CREATE TABLE elevation_data (
    id SERIAL PRIMARY KEY,
    point_id INTEGER,
    elevation NUMERIC,
    geom GEOMETRY(POINT, :storage_srid)
);

-- Insert elevation data for terrain grid points
-- In a real implementation, this would query an elevation service
-- For this example, we'll use a simple function to generate synthetic elevation data
INSERT INTO elevation_data (point_id, elevation, geom)
SELECT 
    id,
    -- Generate synthetic elevation data based on coordinates
    -- This is just for demonstration purposes
    (ST_X(geom) * 0.00001 + ST_Y(geom) * 0.00002) % 1000,
    geom
FROM 
    terrain_grid;

-- Create spatial index
CREATE INDEX elevation_data_geom_idx ON elevation_data USING GIST (geom);

-- Add elevation-based conditions
WITH edge_elevations AS (
    -- Calculate elevation change for each edge
    SELECT 
        ue.id AS edge_id,
        ue.source_id,
        ue.target_id,
        ed1.elevation AS source_elevation,
        ed2.elevation AS target_elevation,
        ed2.elevation - ed1.elevation AS elevation_change,
        ue.length
    FROM 
        unified_edges ue
    JOIN 
        elevation_data ed1 ON ue.source_id = ed1.point_id
    JOIN 
        elevation_data ed2 ON ue.target_id = ed2.point_id
    WHERE 
        ue.edge_type = 'terrain'
)
INSERT INTO environmental_conditions (edge_id, condition_type, speed_factor, description)
SELECT 
    edge_id,
    CASE
        WHEN elevation_change > 0 THEN 'uphill'
        WHEN elevation_change < 0 THEN 'downhill'
        ELSE 'flat'
    END AS condition_type,
    CASE
        WHEN elevation_change > 0 THEN :uphill_speed_factor
        WHEN elevation_change < 0 THEN :downhill_speed_factor
        ELSE 1.0
    END AS speed_factor,
    CASE
        WHEN elevation_change > 0 THEN 'Uphill slope: ' || ROUND(elevation_change / length * 100, 2) || '%'
        WHEN elevation_change < 0 THEN 'Downhill slope: ' || ROUND(ABS(elevation_change) / length * 100, 2) || '%'
        ELSE 'Flat terrain'
    END AS description
FROM 
    edge_elevations;

-- Create a table for the final graph
DROP TABLE IF EXISTS graph_edges CASCADE;
CREATE TABLE graph_edges (
    id SERIAL PRIMARY KEY,
    source_id INTEGER,
    target_id INTEGER,
    length NUMERIC,
    travel_time NUMERIC,
    edge_type TEXT,
    conditions TEXT[],
    geom GEOMETRY(LINESTRING, :storage_srid)
);

-- Insert edges with environmental conditions
INSERT INTO graph_edges (source_id, target_id, length, travel_time, edge_type, conditions, geom)
SELECT 
    ue.source_id,
    ue.target_id,
    ue.length,
    ue.length / (:default_speed * COALESCE(
        (SELECT MIN(speed_factor) FROM environmental_conditions WHERE edge_id = ue.id),
        1.0
    )),
    ue.edge_type,
    ARRAY(
        SELECT condition_type 
        FROM environmental_conditions 
        WHERE edge_id = ue.id
    ),
    ue.geom
FROM 
    unified_edges ue;

-- Create spatial index
CREATE INDEX graph_edges_geom_idx ON graph_edges USING GIST (geom);
CREATE INDEX graph_edges_source_id_idx ON graph_edges (source_id);
CREATE INDEX graph_edges_target_id_idx ON graph_edges (target_id);

-- Create a table for graph vertices
DROP TABLE IF EXISTS graph_vertices CASCADE;
CREATE TABLE graph_vertices (
    id SERIAL PRIMARY KEY,
    original_id INTEGER,
    elevation NUMERIC,
    geom GEOMETRY(POINT, :storage_srid)
);

-- Insert vertices
INSERT INTO graph_vertices (original_id, elevation, geom)
SELECT 
    tg.id,
    COALESCE(ed.elevation, 0),
    tg.geom
FROM 
    terrain_grid tg
LEFT JOIN 
    elevation_data ed ON tg.id = ed.point_id;

-- Create spatial index
CREATE INDEX graph_vertices_geom_idx ON graph_vertices USING GIST (geom);

-- Log the results
SELECT 'Created ' || COUNT(*) || ' environmental conditions' FROM environmental_conditions;
SELECT 'Created ' || COUNT(*) || ' graph edges' FROM graph_edges;
SELECT 'Created ' || COUNT(*) || ' graph vertices' FROM graph_vertices;

-- Create a topology for the graph
DROP TABLE IF EXISTS graph_topology CASCADE;
CREATE TABLE graph_topology (
    id SERIAL PRIMARY KEY,
    source_id INTEGER REFERENCES graph_vertices(id),
    target_id INTEGER REFERENCES graph_vertices(id),
    edge_id INTEGER REFERENCES graph_edges(id),
    cost NUMERIC,
    reverse_cost NUMERIC
);

-- Insert topology
INSERT INTO graph_topology (source_id, target_id, edge_id, cost, reverse_cost)
SELECT 
    gv1.id AS source_id,
    gv2.id AS target_id,
    ge.id AS edge_id,
    ge.travel_time AS cost,
    ge.travel_time AS reverse_cost
FROM 
    graph_edges ge
JOIN 
    graph_vertices gv1 ON ge.source_id = gv1.original_id
JOIN 
    graph_vertices gv2 ON ge.target_id = gv2.original_id;

-- Create indexes
CREATE INDEX graph_topology_source_id_idx ON graph_topology (source_id);
CREATE INDEX graph_topology_target_id_idx ON graph_topology (target_id);
CREATE INDEX graph_topology_edge_id_idx ON graph_topology (edge_id);

-- Log the results
SELECT 'Created ' || COUNT(*) || ' topology entries' FROM graph_topology;
