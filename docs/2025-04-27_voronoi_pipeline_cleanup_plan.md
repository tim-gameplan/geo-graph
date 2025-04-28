# Voronoi Pipeline Cleanup Plan

*2025-04-27 08:52 AM*

## 1. Current Functional Pipeline Overview

The Voronoi Obstacle Boundary pipeline is a stable component of our terrain system that uses Voronoi diagrams to create natural connections between two graphs:

1. A graph defined using the geometry of buffers created around water features
2. A graph created from a hexagonal polygon pattern applied across the geographic project area

The Voronoi approach creates edge connections between these two graphs in a more natural and evenly distributed manner than previous approaches.

## 2. Core Voronoi Pipeline Components

The following files are essential for the Voronoi pipeline and should be maintained:

### 2.1 Main Runner Scripts
- `epsg3857_pipeline/run_voronoi_obstacle_boundary_pipeline.py` - Main wrapper script
- `epsg3857_pipeline/core/scripts/run_voronoi_obstacle_boundary_pipeline.py` - Core implementation

### 2.2 SQL Implementation
- `epsg3857_pipeline/core/obstacle_boundary/create_voronoi_obstacle_boundary_graph.sql` - Voronoi graph creation
- `epsg3857_pipeline/core/sql/04_create_terrain_grid_hexagon.sql` - Hexagonal terrain grid creation
- Standard SQL scripts used in the pipeline:
  - `epsg3857_pipeline/core/sql/01_extract_water_features_3857.sql`
  - `epsg3857_pipeline/core/sql/02_create_water_buffers_3857.sql`
  - `epsg3857_pipeline/core/sql/03_dissolve_water_buffers_3857.sql`
  - `epsg3857_pipeline/core/sql/05_create_terrain_edges_3857.sql`

### 2.3 Visualization and Testing
- `epsg3857_pipeline/core/scripts/visualize_voronoi_obstacle_boundary.py` - Visualization script
- `epsg3857_pipeline/core/tests/test_voronoi_obstacle_boundary.py` - Test script

### 2.4 Configuration
- `epsg3857_pipeline/config/voronoi_obstacle_boundary_config.json` - Configuration file

### 2.5 Documentation
- `epsg3857_pipeline/docs/voronoi_connection_strategy.md` - Documentation of the Voronoi approach

## 3. Files to be Deprecated

During development and testing of the Voronoi approach, several temporary files were created that are no longer needed and should be moved to the deprecated directory:

### 3.1 Temporary SQL Files
- `temp_04_create_terrain_grid_boundary_3857.sql` - Temporary file for testing boundary grid creation
- `temp_04_create_terrain_grid_boundary_3857_fixed.sql` - Fixed version of the temporary file
- `temp_04_create_terrain_grid_boundary_3857_fixed2.sql` - Second fixed version
- `temp_04_create_terrain_grid_boundary_3857_fixed3.sql` - Third fixed version
- `temp_1745532263.sql` - Temporary SQL file generated during pipeline execution

### 3.2 Older Obstacle Boundary Implementation
The original obstacle boundary implementation has been superseded by the Voronoi approach and should be deprecated:
- `deprecated/scripts/run_obstacle_boundary_graph.py` - Already moved to deprecated

## 4. Migration Plan

To clean up our directory structure and reduce confusion, we will:

1. **Move Temporary Files to Deprecated**:
   ```bash
   mv temp_04_create_terrain_grid_boundary_3857.sql deprecated/sql/
   mv temp_04_create_terrain_grid_boundary_3857_fixed.sql deprecated/sql/
   mv temp_04_create_terrain_grid_boundary_3857_fixed2.sql deprecated/sql/
   mv temp_04_create_terrain_grid_boundary_3857_fixed3.sql deprecated/sql/
   mv temp_1745532263.sql deprecated/sql/
   ```

2. **Update Documentation**:
   - Update `epsg3857_pipeline/docs/component_status.md` to reflect the current status of all components
   - Ensure `epsg3857_pipeline/docs/pipeline_comparison.md` accurately compares the Voronoi approach with other approaches

3. **Verify Pipeline Functionality**:
   - Run the Voronoi pipeline to ensure it still works after cleanup:
     ```bash
     python epsg3857_pipeline/run_voronoi_obstacle_boundary_pipeline.py
     ```
   - Run tests to verify functionality:
     ```bash
     python epsg3857_pipeline/core/tests/test_voronoi_obstacle_boundary.py
     ```

## 5. Pipeline Execution Flow

The Voronoi Obstacle Boundary pipeline executes in the following sequence:

1. **Database Preparation**:
   - Reset derived tables (if not skipped)
   - Load configuration parameters

2. **Water Feature Processing**:
   - Extract water features from OSM data
   - Create buffers around water features
   - Dissolve overlapping water buffers

3. **Terrain Grid Creation**:
   - Create a hexagonal terrain grid
   - Classify hexagons as land, boundary, or water
   - Create terrain edges connecting grid cells

4. **Voronoi Boundary Creation**:
   - Extract boundary nodes from water obstacles
   - Create edges between adjacent boundary nodes
   - Create Voronoi cells for boundary nodes
   - Connect terrain grid points to boundary nodes using Voronoi partitioning
   - Create a unified graph combining terrain edges, boundary edges, and connection edges

5. **Visualization** (optional):
   - Visualize the Voronoi obstacle boundary graph
   - Show terrain grid, water obstacles, boundary nodes, and connections

## 6. Conclusion

The Voronoi Obstacle Boundary approach provides a stable and effective method for connecting terrain and water graphs. By cleaning up temporary and deprecated files, we can maintain a cleaner codebase and reduce confusion for developers working on the project.

This cleanup plan will help ensure that only the necessary files are kept in the main directory structure, while preserving historical files in the deprecated directory for reference if needed.
