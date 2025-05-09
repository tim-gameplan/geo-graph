# Deprecated Files

This directory contains files that were part of earlier versions of the terrain system pipeline but are no longer used in the current implementation.

## Contents

- `config/`: Deprecated configuration files
- `scripts/`: Deprecated pipeline scripts
- `sql/`: Deprecated SQL scripts

These files were moved here as part of a project cleanup on May 8, 2025, to focus on the Enhanced Boundary Hexagon Layer Pipeline, which is the current production pipeline.

## Current Pipeline

The current production pipeline is implemented in:
- `epsg3857_pipeline/pipelines/run_boundary_hexagon_layer_enhanced_pipeline.py`

This pipeline uses the configuration file:
- `epsg3857_pipeline/config/crs_standardized_config_boundary_hexagon.json`

And the following SQL scripts:
- `01_extract_water_features_3857.sql`
- `02_create_water_buffers_3857.sql`
- `03_dissolve_water_buffers_3857.sql`
- `04_create_terrain_grid_boundary_hexagon.sql`
- `04a_create_terrain_edges_hexagon.sql`
- `05_create_boundary_nodes_hexagon.sql`
- `06_create_boundary_edges_hexagon_enhanced.sql`
- `07_create_unified_boundary_graph_hexagon.sql`