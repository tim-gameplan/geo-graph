# Boundary Hexagon Layer Enhancement Plan

## Overview

This document outlines the plan to enhance the Boundary Hexagon Layer approach in the EPSG:3857 Terrain Graph Pipeline. The enhancements address two key issues:

1. **Excessive Boundary-to-Obstacle Connections**: The current implementation creates too many connections between boundary nodes and water obstacle nodes, resulting in redundant edges.

2. **Gaps Between Land/Boundary and Water Nodes**: When a hexagon has a node in water, it's discounted, creating connectivity gaps.

## Goals

1. Reduce the number of boundary-to-water connections while maintaining effective pathfinding capabilities
2. Fill gaps between land/boundary nodes and water nodes to improve connectivity
3. Maintain the core benefits of the Boundary Hexagon Layer approach
4. Ensure the graph accurately models travel times and distances for off-road vehicles
5. Optimize the graph structure by eliminating redundant edges

## Technical Approach

### Phase 1: Enhanced Terrain Grid Creation

**File to Modify**: `04_create_terrain_grid_boundary_3857.sql`

**Changes**:

1. Extend the definition of boundary hexagons to include strategic water hexagons:
   ```sql
   CREATE TABLE classified_hex_grid AS
   SELECT
       hg.geom,
       CASE
           WHEN EXISTS (
               SELECT 1
               FROM water_obstacles wo
               WHERE ST_Contains(wo.geom, ST_Buffer(hg.geom, -1))
           ) THEN 'water'
           WHEN EXISTS (
               SELECT 1
               FROM water_obstacles wo
               WHERE ST_Intersects(wo.geom, hg.geom)
           ) THEN 'boundary'
           WHEN EXISTS (
               SELECT 1
               FROM water_obstacles wo
               JOIN complete_hex_grid chg ON ST_Intersects(wo.geom, chg.geom)
               WHERE ST_DWithin(hg.geom, chg.geom, :boundary_extension_distance)
               AND ST_Touches(hg.geom, chg.geom)
           ) THEN 'boundary_extension'  -- New classification
           ELSE 'land'
       END AS hex_type
   FROM complete_hex_grid hg;
   ```

2. Identify water hexagons that are adjacent to land or boundary hexagons:
   ```sql
   CREATE TABLE adjacent_water_hexagons AS
   SELECT
       wh.geom AS water_hex_geom,
       array_agg(lh.hex_type) AS adjacent_types
   FROM
       classified_hex_grid wh
   JOIN
       classified_hex_grid lh ON ST_Touches(wh.geom, lh.geom)
   WHERE
       wh.hex_type = 'water'
       AND lh.hex_type IN ('land', 'boundary', 'boundary_extension')
   GROUP BY
       wh.geom;
   ```

3. Create a new table to store potential land portions within water hexagons:
   ```sql
   CREATE TABLE water_hex_land_portions AS
   SELECT
       wh.water_hex_geom,
       ST_Difference(wh.water_hex_geom, ST_Union(wo.geom)) AS land_portion
   FROM
       adjacent_water_hexagons wh
   JOIN
       water_obstacles wo ON ST_Intersects(wh.water_hex_geom, wo.geom)
   GROUP BY
       wh.water_hex_geom
   HAVING
       ST_Area(ST_Difference(wh.water_hex_geom, ST_Union(wo.geom))) > 0;
   ```

4. Update the terrain grid to include these new classifications:
   ```sql
   CREATE TABLE terrain_grid AS
   SELECT 
       ROW_NUMBER() OVER () AS id,
       geom, 
       hex_type
   FROM 
       classified_hex_grid
   WHERE 
       hex_type IN ('land', 'boundary', 'boundary_extension')
   UNION ALL
   SELECT
       ROW_NUMBER() OVER () + (SELECT COUNT(*) FROM classified_hex_grid WHERE hex_type IN ('land', 'boundary', 'boundary_extension')) AS id,
       water_hex_geom AS geom,
       'water_with_land' AS hex_type
   FROM
       water_hex_land_portions;
   ```

### Phase 2: Enhanced Boundary Node Creation

**File to Modify**: `05_create_boundary_nodes_3857.sql`

**Changes**:

1. Create boundary nodes for the extended boundary hexagons:
   ```sql
   -- Create land portions of boundary hexagons (including extended boundaries)
   CREATE TABLE boundary_land_portions AS
   SELECT
       hg.id AS hex_id,
       hg.geom AS hex_geom,
       CASE
           WHEN hg.hex_type IN ('boundary', 'boundary_extension') THEN 
               ST_Difference(hg.geom, ST_Union(wo.geom))
           ELSE hg.geom
       END AS land_portion
   FROM
       terrain_grid hg
   LEFT JOIN
       water_obstacles wo ON ST_Intersects(hg.geom, wo.geom)
   WHERE
       hg.hex_type IN ('boundary', 'boundary_extension')
   GROUP BY
       hg.id, hg.geom, hg.hex_type;
   ```

2. Create boundary nodes for water hexagons with land portions:
   ```sql
   -- Create boundary nodes for water hexagons with land portions
   INSERT INTO boundary_nodes (hex_id, node_type, geom)
   SELECT
       hg.id AS hex_id,
       'water_boundary' AS node_type,
       CASE
           WHEN ST_Area(whlp.land_portion) > 0 THEN ST_PointOnSurface(whlp.land_portion)
           ELSE ST_Centroid(hg.geom)
       END AS geom
   FROM
       terrain_grid hg
   JOIN
       water_hex_land_portions whlp ON ST_Equals(hg.geom, whlp.water_hex_geom)
   WHERE
       hg.hex_type = 'water_with_land'
       AND ST_Area(whlp.land_portion) > 0;
   ```

3. Create bridge nodes across narrow water features:
   ```sql
   -- Identify narrow water crossings
   CREATE TABLE narrow_water_crossings AS
   WITH land_pairs AS (
       SELECT
           l1.id AS land1_id,
           l2.id AS land2_id,
           l1.geom AS land1_geom,
           l2.geom AS land2_geom,
           ST_ShortestLine(l1.geom, l2.geom) AS crossing_line
       FROM
           terrain_grid_points l1
       JOIN
           terrain_grid_points l2 ON ST_DWithin(l1.geom, l2.geom, :max_bridge_distance)
       WHERE
           l1.id < l2.id
           AND l1.hex_type IN ('land', 'boundary', 'boundary_extension')
           AND l2.hex_type IN ('land', 'boundary', 'boundary_extension')
           AND EXISTS (
               SELECT 1
               FROM water_obstacles wo
               WHERE ST_Intersects(ST_MakeLine(l1.geom, l2.geom), wo.geom)
           )
   )
   SELECT
       land1_id,
       land2_id,
       crossing_line,
       ST_Length(crossing_line) AS crossing_length
   FROM
       land_pairs
   WHERE
       ST_Length(crossing_line) <= :max_bridge_length;

   -- Create bridge nodes
   INSERT INTO boundary_nodes (node_type, geom)
   SELECT
       'bridge' AS node_type,
       ST_LineInterpolatePoint(crossing_line, 0.5) AS geom
   FROM
       narrow_water_crossings;
   ```

### Phase 3: Optimized Edge Creation

**File to Modify**: `06_create_boundary_edges_3857.sql`

**Changes**:

1. Implement a directional connection strategy for boundary-to-water edges:
   ```sql
   -- Create boundary-to-water edges with directional filtering
   CREATE TABLE boundary_water_edges AS
   WITH directional_sectors AS (
       SELECT
           b.node_id AS boundary_node_id,
           w.node_id AS water_node_id,
           ST_Azimuth(b.geom, w.geom) AS azimuth,
           FLOOR(ST_Azimuth(b.geom, w.geom) / (2 * PI() / :direction_count)) AS direction_sector,
           ST_Distance(b.geom, w.geom) AS distance,
           ST_MakeLine(b.geom, w.geom) AS geom
       FROM
           boundary_nodes b
       JOIN
           water_boundary_nodes w ON ST_DWithin(b.geom, w.geom, :max_edge_length)
       WHERE
           NOT EXISTS (
               SELECT 1
               FROM water_obstacles
               WHERE ST_Contains(water_obstacles.geom, b.geom)
           )
   )
   SELECT
       boundary_node_id AS source_id,
       water_node_id AS target_id,
       distance AS length,
       distance / (5.0 * :water_speed_factor) AS cost,
       'boundary_water' AS edge_type,
       geom
   FROM (
       SELECT 
           boundary_node_id, water_node_id, distance, geom,
           ROW_NUMBER() OVER (PARTITION BY boundary_node_id, direction_sector ORDER BY distance) AS rank
       FROM
           directional_sectors
   ) AS ranked_connections
   WHERE
       rank <= :max_connections_per_direction;
   ```

2. Create edges to connect the new boundary nodes in water hexagons:
   ```sql
   -- Create edges to connect water boundary nodes to regular boundary nodes
   INSERT INTO boundary_boundary_edges (source_id, target_id, length, cost, edge_type, geom)
   SELECT
       wb.node_id AS source_id,
       b.node_id AS target_id,
       ST_Length(ST_MakeLine(wb.geom, b.geom)) AS length,
       ST_Length(ST_MakeLine(wb.geom, b.geom)) / 5.0 AS cost,
       'water_boundary_to_boundary' AS edge_type,
       ST_MakeLine(wb.geom, b.geom) AS geom
   FROM
       boundary_nodes wb
   JOIN
       boundary_nodes b ON ST_DWithin(wb.geom, b.geom, :max_edge_length)
   WHERE
       wb.node_type = 'water_boundary'
       AND b.node_type = 'boundary'
       AND wb.node_id != b.node_id
       AND NOT EXISTS (
           SELECT 1
           FROM water_obstacles
           WHERE ST_Intersects(water_obstacles.geom, ST_MakeLine(wb.geom, b.geom))
       );
   ```

3. Create edges to connect bridge nodes:
   ```sql
   -- Create edges to connect bridge nodes to other nodes
   INSERT INTO boundary_boundary_edges (source_id, target_id, length, cost, edge_type, geom)
   SELECT
       br.node_id AS source_id,
       b.node_id AS target_id,
       ST_Length(ST_MakeLine(br.geom, b.geom)) AS length,
       ST_Length(ST_MakeLine(br.geom, b.geom)) / 5.0 AS cost,
       'bridge_to_boundary' AS edge_type,
       ST_MakeLine(br.geom, b.geom) AS geom
   FROM
       boundary_nodes br
   JOIN
       boundary_nodes b ON ST_DWithin(br.geom, b.geom, :max_edge_length)
   WHERE
       br.node_type = 'bridge'
       AND b.node_type IN ('boundary', 'water_boundary')
       AND br.node_id != b.node_id
       AND NOT EXISTS (
           SELECT 1
           FROM water_obstacles
           WHERE ST_Intersects(water_obstacles.geom, ST_MakeLine(br.geom, b.geom))
       );
   ```

### Phase 4: Configuration Updates

**File to Modify**: `epsg3857_pipeline/config/crs_standardized_config_boundary_hexagon.json`

**Changes**:

Add new configuration parameters:

```json
{
  "crs": {
    "storage": 3857,
    "export": 4326,
    "analysis": 3857
  },
  "terrain_grid": {
    "grid_spacing": 200,
    "max_edge_length": 500
  },
  "boundary_hexagon_layer": {
    "boundary_node_spacing": 100,
    "boundary_edge_max_length": 200,
    "water_speed_factor": 0.2,
    "boundary_extension_distance": 50,
    "max_bridge_distance": 300,
    "max_bridge_length": 150,
    "direction_count": 8,
    "max_connections_per_direction": 2
  }
}
```

### Phase 5: Runner Script Updates

**File to Modify**: `epsg3857_pipeline/core/scripts/run_water_obstacle_pipeline_boundary_hexagon.py`

**Changes**:

Update the script to pass the new configuration parameters to the SQL scripts:

```python
# Add boundary hexagon layer parameters to the params dictionary
boundary_hexagon_layer = config_loader.config.get('boundary_hexagon_layer', {})
params['boundary_node_spacing'] = boundary_hexagon_layer.get('boundary_node_spacing', 100)
params['boundary_edge_max_length'] = boundary_hexagon_layer.get('boundary_edge_max_length', 200)
params['water_speed_factor'] = boundary_hexagon_layer.get('water_speed_factor', 0.2)
params['max_edge_length'] = config_loader.config.get('terrain_grid', {}).get('max_edge_length', 500)
params['boundary_extension_distance'] = boundary_hexagon_layer.get('boundary_extension_distance', 50)
params['max_bridge_distance'] = boundary_hexagon_layer.get('max_bridge_distance', 300)
params['max_bridge_length'] = boundary_hexagon_layer.get('max_bridge_length', 150)
params['direction_count'] = boundary_hexagon_layer.get('direction_count', 8)
params['max_connections_per_direction'] = boundary_hexagon_layer.get('max_connections_per_direction', 2)
```

### Phase 6: Visualization Updates

**File to Modify**: `epsg3857_pipeline/core/scripts/visualize_boundary_hexagon_layer.py`

**Changes**:

Update the visualization script to display the new node and edge types:

```python
# Add new node types to the visualization
for wkt in water_boundary_nodes_geoms:
    coords = parse_wkt_point(wkt)
    plt.scatter(coords[0], coords[1], color='cyan', s=10, alpha=0.8)

for wkt in bridge_nodes_geoms:
    coords = parse_wkt_point(wkt)
    plt.scatter(coords[0], coords[1], color='magenta', s=10, alpha=0.8)

# Add new edge types to the visualization
for wkt in unified_boundary_edges_geoms['water_boundary_to_boundary']:
    coords = parse_wkt_linestring(wkt)
    plt.plot(coords[:, 0], coords[:, 1], color='teal', linewidth=0.5, alpha=0.5)

for wkt in unified_boundary_edges_geoms['bridge_to_boundary']:
    coords = parse_wkt_linestring(wkt)
    plt.plot(coords[:, 0], coords[:, 1], color='magenta', linewidth=0.5, alpha=0.5)

# Update the legend
legend_elements.extend([
    plt.Line2D([0], [0], marker='o', color='w', markerfacecolor='cyan', markersize=8, label='Water Boundary Node'),
    plt.Line2D([0], [0], marker='o', color='w', markerfacecolor='magenta', markersize=8, label='Bridge Node'),
    plt.Line2D([0], [0], color='teal', linewidth=1, label='Water Boundary to Boundary Edge'),
    plt.Line2D([0], [0], color='magenta', linewidth=1, label='Bridge to Boundary Edge')
])
```

## Implementation Timeline

1. **Week 1: Development and Testing**
   - Day 1-2: Implement Phase 1 (Enhanced Terrain Grid Creation)
   - Day 3-4: Implement Phase 2 (Enhanced Boundary Node Creation)
   - Day 5: Implement Phase 3 (Optimized Edge Creation)

2. **Week 2: Configuration, Visualization, and Integration**
   - Day 1: Implement Phase 4 (Configuration Updates)
   - Day 2: Implement Phase 5 (Runner Script Updates)
   - Day 3: Implement Phase 6 (Visualization Updates)
   - Day 4-5: Integration testing and bug fixes

3. **Week 3: Validation and Documentation**
   - Day 1-2: Comprehensive testing with various datasets
   - Day 3-4: Performance optimization
   - Day 5: Documentation updates and final review

## Expected Outcomes

1. **Reduced Connection Density**: The directional connection strategy should significantly reduce the number of boundary-to-water connections while maintaining effective pathfinding capabilities.

2. **Improved Connectivity**: The addition of boundary nodes in water hexagons and bridge nodes should fill the gaps between land/boundary nodes and water nodes, improving overall connectivity.

3. **More Natural Graph Structure**: The enhanced approach should create a more natural-looking graph that better represents the terrain and water features.

4. **Optimized Performance**: By reducing redundant edges, the graph should be more efficient for pathfinding algorithms.

5. **Better Travel Time Estimation**: The improved graph structure should provide more accurate travel time and distance estimates for off-road vehicles.

## Conclusion

The proposed enhancements to the Boundary Hexagon Layer approach address the two key issues identified: excessive boundary-to-obstacle connections and gaps between land/boundary and water nodes. By implementing these changes, we expect to create a more efficient and natural-looking terrain graph that better serves the needs of off-road vehicle pathfinding.
