# Backward Compatibility Views

This document outlines the backward compatibility views that will be created to maintain compatibility with existing code after implementing the Pipeline Stage Prefixing naming convention.

## Purpose

The backward compatibility views serve the following purposes:

1. Allow existing code to continue working without modification
2. Provide a transition period for updating code references
3. Ensure that the implementation of the new naming convention doesn't break existing functionality

## Implementation Approach

For each table that is renamed, a view will be created with the old table name that points to the new table. This allows existing code to continue referencing the old table name while the actual data is stored in the new table.

## SQL Script

The backward compatibility views will be created by a dedicated SQL script: `create_backward_compatibility_views.sql`. This script will be run after all the other SQL scripts in the pipeline.

```sql
-- create_backward_compatibility_views.sql
-- This script creates views with the old table names that point to the new tables.
-- This ensures backward compatibility with existing code.

-- Stage 1: Water Features
CREATE OR REPLACE VIEW water_features_polygon AS SELECT * FROM s01_water_features_polygon;
CREATE OR REPLACE VIEW water_features_line AS SELECT * FROM s01_water_features_line;
CREATE OR REPLACE VIEW water_features AS SELECT * FROM s01_water_features_view;

-- Stage 2: Water Buffers
CREATE OR REPLACE VIEW water_buffers AS SELECT * FROM s02_water_buffers;

-- Stage 3: Dissolved Water Buffers and Water Obstacles
CREATE OR REPLACE VIEW dissolved_water_buffers AS SELECT * FROM s03_water_buffers_dissolved;
CREATE OR REPLACE VIEW water_obstacles AS SELECT * FROM s03_water_obstacles;

-- Stage 4: Terrain Grid
CREATE OR REPLACE VIEW complete_hex_grid AS SELECT * FROM s04_grid_hex_complete;
CREATE OR REPLACE VIEW classified_hex_grid AS SELECT * FROM s04_grid_hex_classified;
CREATE OR REPLACE VIEW water_hexagons_with_land AS SELECT * FROM s04_grid_water_with_land;
CREATE OR REPLACE VIEW water_hex_land_portions AS SELECT * FROM s04_grid_water_land_portions;
CREATE OR REPLACE VIEW terrain_grid AS SELECT * FROM s04_grid_terrain;
CREATE OR REPLACE VIEW terrain_grid_points AS SELECT * FROM s04_grid_terrain_points;

-- Stage 4a: Terrain Edges
CREATE OR REPLACE VIEW terrain_edges AS SELECT * FROM s04a_edges_terrain;

-- Stage 5: Boundary Nodes
CREATE OR REPLACE VIEW boundary_nodes AS SELECT * FROM s05_nodes_boundary;
CREATE OR REPLACE VIEW water_boundary_nodes AS SELECT * FROM s05_nodes_water_boundary;
CREATE OR REPLACE VIEW land_portion_nodes AS SELECT * FROM s05_nodes_land_portion;

-- Stage 6: Boundary Edges
CREATE OR REPLACE VIEW boundary_boundary_edges AS SELECT * FROM s06_edges_boundary_boundary;
CREATE OR REPLACE VIEW boundary_land_portion_edges AS SELECT * FROM s06_edges_boundary_land_portion;
CREATE OR REPLACE VIEW land_portion_water_boundary_edges AS SELECT * FROM s06_edges_land_portion_water_boundary;
CREATE OR REPLACE VIEW water_boundary_water_boundary_edges AS SELECT * FROM s06_edges_water_boundary_water_boundary;
CREATE OR REPLACE VIEW boundary_water_boundary_edges AS SELECT * FROM s06_edges_boundary_water_boundary;
CREATE OR REPLACE VIEW land_portion_land_edges AS SELECT * FROM s06_edges_land_portion_land;
CREATE OR REPLACE VIEW all_boundary_edges AS SELECT * FROM s06_edges_all_boundary;

-- Stage 7: Unified Boundary Graph
CREATE OR REPLACE VIEW unified_boundary_nodes AS SELECT * FROM s07_graph_unified_nodes;
CREATE OR REPLACE VIEW unified_boundary_edges AS SELECT * FROM s07_graph_unified_edges;
CREATE OR REPLACE VIEW unified_boundary_graph AS SELECT * FROM s07_graph_unified;

-- Log the creation of backward compatibility views
DO $$
BEGIN
    RAISE NOTICE 'Created backward compatibility views for all tables';
END $$;
```

## View vs. Table Considerations

Using views instead of tables for backward compatibility has the following advantages:

1. **No Data Duplication**: Views don't store data, they just provide a different way to access the same data
2. **Automatic Updates**: When the underlying table is updated, the view automatically reflects those changes
3. **Minimal Performance Impact**: Views have minimal performance impact compared to duplicating data

However, there are some considerations:

1. **Write Operations**: If the existing code performs write operations (INSERT, UPDATE, DELETE) on the tables, additional work may be needed to make the views updatable
2. **Performance**: Complex views may have some performance impact, especially if they involve joins or aggregations
3. **Permissions**: Ensure that the permissions on the views match the permissions on the original tables

## Testing Backward Compatibility

To ensure that the backward compatibility views work correctly, the following tests will be performed:

1. **Read Operations**: Verify that queries using the old table names return the same results as queries using the new table names
2. **Write Operations**: If applicable, verify that write operations on the views correctly update the underlying tables
3. **Existing Code**: Run existing code that uses the old table names and verify that it works correctly
4. **Performance**: Compare the performance of queries using the views vs. queries using the tables directly

## Transition Plan

While the backward compatibility views provide a way to maintain compatibility with existing code, the long-term goal is to update all code to use the new table names directly. The following transition plan will be followed:

1. **Phase 1**: Implement the new naming convention and create backward compatibility views
2. **Phase 2**: Update all code references to use the new table names
3. **Phase 3**: Monitor usage of the backward compatibility views
4. **Phase 4**: Eventually deprecate and remove the backward compatibility views when they are no longer needed

## Conclusion

The backward compatibility views provide a way to maintain compatibility with existing code while implementing the new table naming convention. By creating views with the old table names that point to the new tables, we can ensure a smooth transition to the new naming convention without breaking existing functionality.