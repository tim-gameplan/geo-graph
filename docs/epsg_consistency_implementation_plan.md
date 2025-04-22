# EPSG Consistency Implementation Plan

**Date:** April 21, 2025  
**Author:** Cline  
**Project:** Terrain System - Geo-Graph  

## Overview

This document outlines a comprehensive plan for implementing EPSG consistency across the entire terrain system pipeline. Building on the work already completed for the water obstacle pipeline, this plan extends the CRS standardization to all components of the system.

## Goals

1. Ensure consistent use of EPSG:3857 (Web Mercator) for all internal processing
2. Convert to EPSG:4326 (WGS84) only for export and visualization
3. Improve accuracy and performance of spatial operations
4. Maintain backward compatibility with existing code

## Implementation Phases

### Phase 1: Terrain Grid and Edges (Week 1)

#### 1.1 Terrain Grid Script

Create `planning/sql/04_create_terrain_grid_3857.sql`:

```sql
-- Create terrain grid in EPSG:3857
DROP TABLE IF EXISTS terrain_grid;
CREATE TABLE terrain_grid AS
SELECT 
    (ST_HexagonGrid(:cell_size, ST_Transform(ST_Extent(geom), 3857))).*
FROM water_buf_dissolved;

-- Add cost column
ALTER TABLE terrain_grid ADD COLUMN cost double precision;
UPDATE terrain_grid SET cost = 1.0; -- placeholder for slope cost

-- Create spatial index
CREATE INDEX ON terrain_grid USING GIST(geom);

-- Add SRID metadata
ALTER TABLE terrain_grid 
ALTER COLUMN geom TYPE geometry(Geometry, 3857) 
USING ST_SetSRID(geom, 3857);
```

#### 1.2 Terrain Edges Script

Create `planning/sql/05_create_terrain_edges_3857.sql`:

```sql
-- Create terrain edges in EPSG:3857
DROP TABLE IF EXISTS terrain_edges;
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
    JOIN points b ON ST_DWithin(a.geom, b.geom, :connection_distance)
    WHERE a.id < b.id -- Avoid duplicate edges
)
SELECT 
    id,
    NULL::bigint AS source,
    NULL::bigint AS target,
    cost,
    geom
FROM edges;

-- Create spatial index
CREATE INDEX ON terrain_edges USING GIST(geom);

-- Add SRID metadata
ALTER TABLE terrain_edges 
ALTER COLUMN geom TYPE geometry(Geometry, 3857) 
USING ST_SetSRID(geom, 3857);
```

#### 1.3 Update Configuration

Update `planning/config/crs_standardized_config.json` with terrain grid parameters:

```json
{
    "terrain_grid": {
        "cell_size": 200,
        "connection_distance": 300,
        "cost_function": "flat" // Options: flat, slope, custom
    }
}
```

### Phase 2: Water Edges and Environmental Tables (Week 1)

#### 2.1 Water Edges Script

Create `planning/sql/06_create_water_edges_3857.sql`:

```sql
-- Create water edges in EPSG:3857
DROP TABLE IF EXISTS water_edges;
CREATE TABLE water_edges AS
SELECT 
    id,
    NULL::bigint AS source,
    NULL::bigint AS target,
    CASE
        WHEN crossability < 20 THEN 1000.0  -- Very difficult to cross
        WHEN crossability < 50 THEN 500.0   -- Moderately difficult to cross
        ELSE 200.0                         -- Easier to cross
    END AS cost,
    crossability,
    avg_buffer_size_m,
    water_type,
    crossability_group,
    buffer_rules_applied,
    crossability_rules_applied,
    ST_Boundary(geom) AS geom,
    'water' AS edge_type
FROM water_buf_dissolved;

-- Create spatial index
CREATE INDEX ON water_edges USING GIST(geom);

-- Add SRID metadata
ALTER TABLE water_edges 
ALTER COLUMN geom TYPE geometry(Geometry, 3857) 
USING ST_SetSRID(geom, 3857);
```

#### 2.2 Environmental Tables Script

Create `planning/sql/07_create_environmental_tables_3857.sql`:

```sql
-- Create environmental conditions table
DROP TABLE IF EXISTS environmental_conditions;
CREATE TABLE environmental_conditions (
    condition_name text PRIMARY KEY,
    value double precision,
    last_updated timestamp DEFAULT CURRENT_TIMESTAMP
);

-- Insert default conditions
INSERT INTO environmental_conditions (condition_name, value) VALUES
    ('rainfall', :rainfall),
    ('snow_depth', :snow_depth),
    ('temperature', :temperature)
ON CONFLICT (condition_name) DO UPDATE
    SET value = EXCLUDED.value,
        last_updated = CURRENT_TIMESTAMP;

-- Apply environmental conditions to water edges
UPDATE water_edges
SET cost = cost * 
    CASE
        -- Increase cost for heavy rainfall
        WHEN (SELECT value FROM environmental_conditions WHERE condition_name = 'rainfall') > 50 THEN 1.5
        -- Increase cost for deep snow
        WHEN (SELECT value FROM environmental_conditions WHERE condition_name = 'snow_depth') > 30 THEN 2.0
        -- Decrease cost for frozen water (below freezing temperature)
        WHEN (SELECT value FROM environmental_conditions WHERE condition_name = 'temperature') < 0 THEN 0.5
        ELSE 1.0
    END;
```

### Phase 3: Unified Edges and Topology (Week 2)

#### 3.1 Unified Edges Script

Create `sql/create_unified_edges_3857.sql`:

```sql
-- Create unified edges table in EPSG:3857
BEGIN;
DROP TABLE IF EXISTS unified_edges CASCADE;
CREATE TABLE unified_edges AS
SELECT 
    id, 
    source, 
    target, 
    cost, 
    geom,
    'road' AS edge_type
FROM road_edges
UNION ALL
SELECT 
    id, 
    source, 
    target, 
    cost, 
    geom,
    'water' AS edge_type
FROM water_edges
UNION ALL
SELECT 
    id, 
    source, 
    target, 
    cost, 
    geom,
    'terrain' AS edge_type
FROM terrain_edges;

-- Create spatial index
CREATE INDEX ON unified_edges USING GIST(geom);

-- Add SRID metadata
ALTER TABLE unified_edges 
ALTER COLUMN geom TYPE geometry(Geometry, 3857) 
USING ST_SetSRID(geom, 3857);
COMMIT;
```

#### 3.2 Topology Script

Create `sql/refresh_topology_3857.sql`:

```sql
-- Refresh topology for unified edges in EPSG:3857
BEGIN;
-- Create vertices table
DROP TABLE IF EXISTS unified_vertices_tmp;
CREATE TABLE unified_vertices_tmp AS
WITH vertices AS (
    -- Extract unique start and end points
    SELECT ST_StartPoint(geom) AS geom FROM unified_edges
    UNION
    SELECT ST_EndPoint(geom) AS geom FROM unified_edges
),
-- Deduplicate vertices with a small tolerance (1cm)
deduplicated AS (
    SELECT DISTINCT ON (ST_SnapToGrid(geom, 0.01)) geom
    FROM vertices
)
SELECT 
    ROW_NUMBER() OVER () AS id,
    geom
FROM deduplicated;

-- Create spatial index on vertices
CREATE INDEX ON unified_vertices_tmp USING GIST(geom);

-- Add SRID metadata to vertices
ALTER TABLE unified_vertices_tmp 
ALTER COLUMN geom TYPE geometry(Point, 3857) 
USING ST_SetSRID(geom, 3857);

-- Update source and target columns in unified_edges
UPDATE unified_edges e
SET source = v.id
FROM unified_vertices_tmp v
WHERE ST_DWithin(ST_StartPoint(e.geom), v.geom, 0.01);

UPDATE unified_edges e
SET target = v.id
FROM unified_vertices_tmp v
WHERE ST_DWithin(ST_EndPoint(e.geom), v.geom, 0.01);

-- Create final vertices table
DROP TABLE IF EXISTS unified_vertices;
CREATE TABLE unified_vertices AS
SELECT * FROM unified_vertices_tmp;

-- Create spatial index on final vertices
CREATE INDEX ON unified_vertices USING GIST(geom);

-- Drop temporary table
DROP TABLE unified_vertices_tmp;
COMMIT;
```

### Phase 4: Export and Visualization (Week 2)

#### 4.1 Export Script

Create `tools/export_slice_3857.py`:

```python
#!/usr/bin/env python3
"""
Export a slice of the unified graph around a specific coordinate.
Uses EPSG:3857 for internal processing and EPSG:4326 for export.
"""
import os
import sys
import argparse
import logging
import geopandas as gpd
import networkx as nx
from sqlalchemy import create_engine
from pathlib import Path

# Add the parent directory to the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.file_management import get_export_path

def connect():
    """Connect to the database."""
    return create_engine(os.getenv("PG_URL", "postgresql://gis:gis@localhost:5432/gis"))

def main(
    longitude: float,
    latitude: float,
    minutes: int = 60,
    outfile: str = None,
    include_attributes: bool = True,
    include_geometry: bool = True
):
    """
    Export a slice of the unified graph around the specified coordinates.
    
    Args:
        longitude: Longitude coordinate (EPSG:4326)
        latitude: Latitude coordinate (EPSG:4326)
        minutes: Travel time in minutes
        outfile: Output GraphML file
        include_attributes: Whether to include attributes in the export
        include_geometry: Whether to include geometry in the export
    """
    engine = connect()
    
    # Transform the input coordinates to EPSG:3857
    with engine.connect() as conn:
        result = conn.execute(
            f"SELECT ST_Transform(ST_SetSRID(ST_MakePoint({longitude}, {latitude}), 4326), 3857)"
        ).fetchone()
        point_3857 = result[0]
    
    # Find the nearest vertex to the input coordinates
    with engine.connect() as conn:
        result = conn.execute(f"""
            SELECT id
            FROM unified_vertices
            ORDER BY geom <-> ST_GeomFromText('{point_3857}', 3857)
            LIMIT 1
        """).fetchone()
        source_id = result[0]
    
    # Calculate the driving distance from the source vertex
    with engine.connect() as conn:
        result = conn.execute(f"""
            SELECT node
            FROM pgr_drivingDistance(
                'SELECT id, source, target, cost FROM unified_edges',
                {source_id},
                {minutes * 60}, -- Convert minutes to seconds
                false
            )
        """)
        reachable_nodes = [row[0] for row in result]
    
    if not reachable_nodes:
        logging.error(f"No reachable nodes found within {minutes} minutes of ({longitude}, {latitude})")
        return
    
    # Create a convex hull of the reachable nodes to approximate an isochrone
    with engine.connect() as conn:
        result = conn.execute(f"""
            SELECT ST_ConvexHull(ST_Collect(geom))
            FROM unified_vertices
            WHERE id IN ({','.join(map(str, reachable_nodes))})
        """)
        isochrone = result.fetchone()[0]
    
    # Extract edges that intersect with the isochrone
    query = f"""
        SELECT
            e.id,
            e.source,
            e.target,
            e.cost,
            e.edge_type
    """
    
    # Include additional attributes if requested
    if include_attributes:
        query += """
            ,
            r.name,
            r.highway,
            r.ref,
            r.oneway,
            r.surface,
            r.bridge,
            r.tunnel,
            r.layer,
            r.access,
            r.service,
            r.junction,
            w.water_type,
            w.crossability,
            w.avg_buffer_size_m,
            w.buffer_rules_applied,
            w.crossability_rules_applied
        """
    
    # Include geometry if requested
    if include_geometry:
        query += """
            ,
            ST_AsText(ST_Transform(e.geom, 4326)) AS wkt
        """
    
    query += f"""
        FROM unified_edges e
        LEFT JOIN road_edges r ON e.id = r.id AND e.edge_type = 'road'
        LEFT JOIN water_edges w ON e.id = w.id AND e.edge_type = 'water'
        WHERE ST_Intersects(e.geom, ST_GeomFromText('{isochrone}', 3857))
    """
    
    # Execute the query
    edges = gpd.read_postgis(
        query,
        engine,
        geom_col='wkt' if include_geometry else None
    )
    
    # Extract node positions
    with engine.connect() as conn:
        result = conn.execute(f"""
            SELECT
                id,
                ST_X(ST_Transform(geom, 4326)) AS x,
                ST_Y(ST_Transform(geom, 4326)) AS y
            FROM unified_vertices
            WHERE id IN (
                SELECT source FROM unified_edges
                WHERE ST_Intersects(geom, ST_GeomFromText('{isochrone}', 3857))
                UNION
                SELECT target FROM unified_edges
                WHERE ST_Intersects(geom, ST_GeomFromText('{isochrone}', 3857))
            )
        """)
        nodes = {row[0]: {'x': row[1], 'y': row[2]} for row in result}
    
    # Create a graph from the edges
    G = nx.DiGraph()
    
    # Add nodes with positions
    for node_id, attrs in nodes.items():
        G.add_node(node_id, **attrs)
    
    # Add edges with attributes
    for _, row in edges.iterrows():
        attrs = {col: row[col] for col in row.index if col not in ['id', 'source', 'target', 'wkt']}
        G.add_edge(row['source'], row['target'], **attrs)
    
    # Determine the output file path
    if outfile is None:
        outfile = get_export_path(
            description="isochrone",
            parameters={
                "lon": longitude,
                "lat": latitude,
                "minutes": minutes
            }
        )
    
    # Write the graph to a GraphML file
    nx.write_graphml(G, outfile)
    print(f'GraphML written to {outfile}')
    
    return outfile

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Export a slice of the unified graph")
    parser.add_argument("--lon", type=float, required=True, help="Longitude coordinate")
    parser.add_argument("--lat",
