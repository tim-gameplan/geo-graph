# Backward Compatibility Views Implementation

This document outlines the implementation plan for the backward compatibility views script.

## Overview

The backward compatibility views script (`create_backward_compatibility_views.sql`) will create views with the old table names that point to the new tables. This ensures that existing code continues to work with the new naming convention.

## Implementation Steps

### 1. Create the Script

Create a new SQL script file `create_backward_compatibility_views.sql` in the `epsg3857_pipeline/core/sql` directory:

```sql
/*
 * Script: create_backward_compatibility_views.sql
 * Purpose: Create backward compatibility views for the renamed tables
 * 
 * This script creates views with the old table names that point to the new tables.
 * This ensures backward compatibility with existing code.
 */

-- Stage 1: Water Features
DROP VIEW IF EXISTS water_features_polygon CASCADE;
DROP VIEW IF EXISTS water_features_line CASCADE;
DROP VIEW IF EXISTS water_features CASCADE;

CREATE VIEW water_features_polygon AS SELECT * FROM s01_water_features_polygon;
CREATE VIEW water_features_line AS SELECT * FROM s01_water_features_line;
CREATE VIEW water_features AS SELECT * FROM s01_water_features_view;

-- Stage 2: Water Buffers
DROP VIEW IF EXISTS water_buffers CASCADE;
CREATE VIEW water_buffers AS SELECT * FROM s02_water_buffers;

-- Stage 3: Dissolved Water Buffers and Water Obstacles
DROP VIEW IF EXISTS dissolved_water_buffers CASCADE;
DROP VIEW IF EXISTS water_obstacles CASCADE;

CREATE VIEW dissolved_water_buffers AS SELECT * FROM s03_water_buffers_dissolved;
CREATE VIEW water_obstacles AS SELECT * FROM s03_water_obstacles;

-- Stage 4: Terrain Grid
DROP VIEW IF EXISTS complete_hex_grid CASCADE;
DROP VIEW IF EXISTS classified_hex_grid CASCADE;
DROP VIEW IF EXISTS water_hexagons_with_land CASCADE;
DROP VIEW IF EXISTS water_hex_land_portions CASCADE;
DROP VIEW IF EXISTS terrain_grid CASCADE;
DROP VIEW IF EXISTS terrain_grid_points CASCADE;

CREATE VIEW complete_hex_grid AS SELECT * FROM s04_grid_hex_complete;
CREATE VIEW classified_hex_grid AS SELECT * FROM s04_grid_hex_classified;
CREATE VIEW water_hexagons_with_land AS SELECT * FROM s04_grid_water_with_land;
CREATE VIEW water_hex_land_portions AS SELECT * FROM s04_grid_water_land_portions;
CREATE VIEW terrain_grid AS SELECT * FROM s04_grid_terrain;
CREATE VIEW terrain_grid_points AS SELECT * FROM s04_grid_terrain_points;

-- Stage 4a: Terrain Edges
DROP VIEW IF EXISTS terrain_edges CASCADE;
CREATE VIEW terrain_edges AS SELECT * FROM s04a_edges_terrain;

-- Stage 5: Boundary Nodes
DROP VIEW IF EXISTS boundary_nodes CASCADE;
DROP VIEW IF EXISTS water_boundary_nodes CASCADE;
DROP VIEW IF EXISTS land_portion_nodes CASCADE;

CREATE VIEW boundary_nodes AS SELECT * FROM s05_nodes_boundary;
CREATE VIEW water_boundary_nodes AS SELECT * FROM s05_nodes_water_boundary;
CREATE VIEW land_portion_nodes AS SELECT * FROM s05_nodes_land_portion;

-- Stage 6: Boundary Edges
DROP VIEW IF EXISTS boundary_boundary_edges CASCADE;
DROP VIEW IF EXISTS boundary_land_portion_edges CASCADE;
DROP VIEW IF EXISTS land_portion_water_boundary_edges CASCADE;
DROP VIEW IF EXISTS water_boundary_water_boundary_edges CASCADE;
DROP VIEW IF EXISTS boundary_water_boundary_edges CASCADE;
DROP VIEW IF EXISTS land_portion_land_edges CASCADE;
DROP VIEW IF EXISTS all_boundary_edges CASCADE;

CREATE VIEW boundary_boundary_edges AS SELECT * FROM s06_edges_boundary_boundary;
CREATE VIEW boundary_land_portion_edges AS SELECT * FROM s06_edges_boundary_land_portion;
CREATE VIEW land_portion_water_boundary_edges AS SELECT * FROM s06_edges_land_portion_water_boundary;
CREATE VIEW water_boundary_water_boundary_edges AS SELECT * FROM s06_edges_water_boundary_water_boundary;
CREATE VIEW boundary_water_boundary_edges AS SELECT * FROM s06_edges_boundary_water_boundary;
CREATE VIEW land_portion_land_edges AS SELECT * FROM s06_edges_land_portion_land;
CREATE VIEW all_boundary_edges AS SELECT * FROM s06_edges_all_boundary;

-- Stage 7: Unified Boundary Graph
DROP VIEW IF EXISTS unified_boundary_nodes CASCADE;
DROP VIEW IF EXISTS unified_boundary_edges CASCADE;
DROP VIEW IF EXISTS unified_boundary_graph CASCADE;

CREATE VIEW unified_boundary_nodes AS SELECT * FROM s07_graph_unified_nodes;
CREATE VIEW unified_boundary_edges AS SELECT * FROM s07_graph_unified_edges;
CREATE VIEW unified_boundary_graph AS SELECT * FROM s07_graph_unified;

-- Log the creation of backward compatibility views
DO $$
BEGIN
    RAISE NOTICE 'Created backward compatibility views for all tables';
END $$;
```

### 2. Update the Pipeline Runner

Update the pipeline runner to run the backward compatibility views script after all other scripts:

```python
def run_pipeline(config_path, sql_dir, container_name='db', verbose=False, use_renamed_tables=True):
    """
    Run the water obstacle pipeline with the enhanced boundary hexagon layer approach.
    
    Args:
        config_path (str): Path to the configuration file
        sql_dir (str): Path to the directory containing SQL scripts
        container_name (str): Name of the Docker container
        verbose (bool): Whether to print verbose output
        use_renamed_tables (bool): Whether to use the renamed tables
    
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Load configuration
        config_loader = load_config(config_path)
        if config_loader is None:
            logger.error(f"Failed to load configuration from {config_path}")
            return False
            
        # Get SQL parameters
        params = config_loader.get_sql_params()
        
        if verbose:
            logger.info(f"Loaded configuration from {config_path}")
            logger.info(f"Parameters: {json.dumps(params, indent=2)}")
        
        # Define SQL scripts to run
        sql_scripts = [
            "01_extract_water_features_3857.sql",
            "02_create_water_buffers_3857.sql",
            "03_dissolve_water_buffers_3857.sql",
            "04_create_terrain_grid_boundary_hexagon.sql",
            "04a_create_terrain_edges_hexagon.sql",
            "05_create_boundary_nodes_hexagon.sql",
            "06_create_boundary_edges_hexagon_enhanced.sql",  # Use the enhanced version
            "07_create_unified_boundary_graph_hexagon.sql"
        ]
        
        # Add backward compatibility views script if using renamed tables
        if use_renamed_tables:
            sql_scripts.append("create_backward_compatibility_views.sql")
        
        # ... rest of the function ...
```

### 3. Test the Implementation

Test the implementation to ensure that the backward compatibility views work correctly:

1. Reset the database to a clean state
2. Run the pipeline with the renamed tables
3. Verify that the views are created correctly
4. Run queries using both the views and the new tables, and compare the results
5. Run existing code that uses the old table names and verify that it works correctly

### 4. Handle Write Operations

If the existing code performs write operations (INSERT, UPDATE, DELETE) on the tables, additional work may be needed to make the views updatable. This can be done by creating INSTEAD OF triggers on the views:

```sql
-- Example of an INSTEAD OF trigger for INSERT operations
CREATE OR REPLACE FUNCTION insert_water_features_polygon()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO s01_water_features_polygon (id, geom)
    VALUES (NEW.id, NEW.geom);
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER insert_water_features_polygon_trigger
INSTEAD OF INSERT ON water_features_polygon
FOR EACH ROW EXECUTE FUNCTION insert_water_features_polygon();
```

### 5. Document the Implementation

Document the implementation in the project documentation:

1. Explain the purpose of the backward compatibility views
2. List all the views that are created
3. Provide examples of how to use the views
4. Explain any limitations or considerations

## Implementation Timeline

The implementation of the backward compatibility views will be completed as part of Phase 1 (SQL Script Modification) of the overall implementation plan:

1. **Day 1**: Create the backward compatibility views script
2. **Day 2**: Update the pipeline runner to run the script
3. **Day 3**: Test the implementation
4. **Day 4**: Handle any write operations if needed
5. **Day 5**: Document the implementation

## Conclusion

The backward compatibility views provide a way to maintain compatibility with existing code while implementing the new table naming convention. By creating views with the old table names that point to the new tables, we can ensure a smooth transition to the new naming convention without breaking existing functionality.