# Table Naming Convention: Pipeline Stage Prefixing

This document defines the table naming convention for the terrain system pipeline.

## Overview

The Pipeline Stage Prefixing naming convention is designed to improve the organization and maintainability of the database schema by clearly indicating the pipeline stage that each table belongs to and its purpose within that stage.

## Naming Pattern

The naming pattern follows this structure:

```
s{stage_number}_{entity_type}_{entity_name}[_{qualifier}]
```

Where:
- `s{stage_number}`: Indicates the pipeline stage (e.g., `s01`, `s02`, etc.)
- `{entity_type}`: Describes the type of entity (e.g., `water`, `grid`, `nodes`, `edges`, `graph`)
- `{entity_name}`: Describes the specific entity (e.g., `features`, `buffers`, `terrain`, `boundary`)
- `{qualifier}`: Optional qualifier to further specify the entity (e.g., `polygon`, `line`, `dissolved`)

## Examples

### Stage 1: Water Features Extraction

- `s01_water_features_polygon`: Water feature polygons extracted from OSM
- `s01_water_features_line`: Water feature lines extracted from OSM
- `s01_water_features_view`: View combining polygon and line water features

### Stage 2: Water Buffers Creation

- `s02_water_buffers`: Buffers created around water features

### Stage 3: Water Buffers Dissolution

- `s03_water_buffers_dissolved`: Dissolved water buffers
- `s03_water_obstacles`: Water obstacles extracted from dissolved buffers

### Stage 4: Terrain Grid Creation

- `s04_grid_hex_complete`: Complete hexagon grid
- `s04_grid_hex_classified`: Classified hexagon grid
- `s04_grid_water_with_land`: Water hexagons with land
- `s04_grid_water_land_portions`: Water hexagon land portions
- `s04_grid_terrain`: Terrain grid
- `s04_grid_terrain_points`: Terrain grid points

### Stage 4a: Terrain Edges Creation

- `s04a_edges_terrain`: Terrain edges

### Stage 5: Boundary Nodes Creation

- `s05_nodes_boundary`: Boundary nodes
- `s05_nodes_water_boundary`: Water boundary nodes
- `s05_nodes_land_portion`: Land portion nodes

### Stage 6: Boundary Edges Creation

- `s06_edges_boundary_boundary`: Edges between boundary nodes
- `s06_edges_boundary_land_portion`: Edges between boundary and land portion nodes
- `s06_edges_land_portion_water_boundary`: Edges between land portion and water boundary nodes
- `s06_edges_water_boundary_water_boundary`: Edges between water boundary nodes
- `s06_edges_boundary_water_boundary`: Edges between boundary and water boundary nodes
- `s06_edges_land_portion_land`: Edges between land portion nodes
- `s06_edges_all_boundary`: All boundary edges

### Stage 7: Unified Boundary Graph Creation

- `s07_graph_unified_nodes`: Unified boundary graph nodes
- `s07_graph_unified_edges`: Unified boundary graph edges
- `s07_graph_unified`: Unified boundary graph

## Benefits

This naming convention provides several benefits:

1. **Clear Pipeline Stage**: The stage prefix (`s01`, `s02`, etc.) clearly indicates which pipeline stage the table belongs to.
2. **Entity Type Identification**: The entity type (`water`, `grid`, `nodes`, etc.) clearly indicates what type of data the table contains.
3. **Consistent Ordering**: Tables are naturally ordered by pipeline stage in database tools and listings.
4. **Improved Maintainability**: The consistent naming pattern makes it easier to understand the purpose of each table.
5. **Better Documentation**: The naming convention serves as implicit documentation of the pipeline structure.

## Implementation Guidelines

When implementing this naming convention, follow these guidelines:

1. **Consistency**: Apply the naming convention consistently across all tables.
2. **Backward Compatibility**: Create views with the old table names that point to the new tables to maintain backward compatibility.
3. **Documentation**: Update all documentation to use the new table names.
4. **Code References**: Update all code references to use the new table names.

## Mapping from Old to New Names

| Current Table Name | New Table Name |
|-------------------|----------------|
| water_features_polygon | s01_water_features_polygon |
| water_features_line | s01_water_features_line |
| water_features (view) | s01_water_features_view |
| water_buffers | s02_water_buffers |
| dissolved_water_buffers | s03_water_buffers_dissolved |
| water_obstacles | s03_water_obstacles |
| complete_hex_grid | s04_grid_hex_complete |
| classified_hex_grid | s04_grid_hex_classified |
| water_hexagons_with_land | s04_grid_water_with_land |
| water_hex_land_portions | s04_grid_water_land_portions |
| terrain_grid | s04_grid_terrain |
| terrain_grid_points | s04_grid_terrain_points |
| terrain_edges | s04a_edges_terrain |
| boundary_nodes | s05_nodes_boundary |
| water_boundary_nodes | s05_nodes_water_boundary |
| land_portion_nodes | s05_nodes_land_portion |
| boundary_boundary_edges | s06_edges_boundary_boundary |
| boundary_land_portion_edges | s06_edges_boundary_land_portion |
| land_portion_water_boundary_edges | s06_edges_land_portion_water_boundary |
| water_boundary_water_boundary_edges | s06_edges_water_boundary_water_boundary |
| boundary_water_boundary_edges | s06_edges_boundary_water_boundary |
| land_portion_land_edges | s06_edges_land_portion_land |
| all_boundary_edges | s06_edges_all_boundary |
| unified_boundary_nodes | s07_graph_unified_nodes |
| unified_boundary_edges | s07_graph_unified_edges |
| unified_boundary_graph | s07_graph_unified |

## Conclusion

The Pipeline Stage Prefixing naming convention provides a clear and consistent way to name tables in the terrain system pipeline. By following this convention, we can improve the organization and maintainability of the database schema, making it easier to understand and work with the pipeline.