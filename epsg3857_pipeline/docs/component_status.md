# Component Status

This document provides a reference for the status of each component in the EPSG:3857 Terrain Graph Pipeline project. It helps engineers quickly understand which components are stable, experimental, or deprecated.

## Status Definitions

- **STABLE**: Production-ready components that are well-tested and recommended for use
- **EXPERIMENTAL**: Components that are under development and may change significantly
- **DEPRECATED**: Components that are no longer recommended for use and may be removed in the future
- **PLANNED**: Components that are planned for future development

## Pipeline Approaches

| Component | Status | Last Updated | Description | Known Issues | Recommended Alternative |
|-----------|--------|--------------|-------------|--------------|------------------------|
| Standard Pipeline | **STABLE** | 2025-04-23 | Basic pipeline with hexagonal grid and improved water edge creation | None | N/A |
| Water Boundary Approach | **STABLE** | 2025-04-23 | Treats water obstacles as navigable boundaries | None | N/A |
| Obstacle Boundary Approach | **STABLE** | 2025-04-24 | Directly converts water obstacle polygons to graph elements | None | N/A |
| Delaunay Triangulation | **EXPERIMENTAL** | 2025-04-22 | Uses Delaunay triangulation for terrain representation | Performance issues with large datasets | Standard Pipeline |
| Boundary Hexagon Layer | **STABLE** | 2025-04-25 | Preserves hexagons at water boundaries for better connectivity | None | N/A |

## Core Components

| Component | Status | Last Updated | Description | Known Issues | Recommended Alternative |
|-----------|--------|--------------|-------------|--------------|------------------------|
| Water Feature Extraction | **STABLE** | 2025-04-23 | Extracts water features from OSM data | None | N/A |
| Water Buffer Creation | **STABLE** | 2025-04-23 | Creates buffers around water features | None | N/A |
| Water Buffer Dissolving | **STABLE** | 2025-04-23 | Dissolves overlapping water buffers | Memory issues with large datasets | N/A |
| Terrain Grid Creation | **STABLE** | 2025-04-23 | Creates a hexagonal terrain grid | None | N/A |
| Terrain Edge Creation | **STABLE** | 2025-04-23 | Creates edges between terrain grid points | None | N/A |
| Improved Water Edge Creation | **STABLE** | 2025-04-23 | Creates water crossing edges with better connectivity | None | N/A |
| Environmental Table Creation | **STABLE** | 2025-04-23 | Adds environmental conditions to edges | None | N/A |

## Scripts

| Component | Status | Last Updated | Description | Known Issues | Recommended Alternative |
|-----------|--------|--------------|-------------|--------------|------------------------|
| run_epsg3857_pipeline.py | **STABLE** | 2025-04-23 | Main pipeline runner | None | N/A |
| run_obstacle_boundary_pipeline.py | **STABLE** | 2025-04-24 | Obstacle boundary pipeline runner | None | N/A |
| import_osm_data.py | **STABLE** | 2025-04-24 | Imports OSM data into the database | None | N/A |
| export_slice.py | **STABLE** | 2025-04-23 | Exports a graph slice | None | N/A |
| visualize.py | **STABLE** | 2025-04-23 | Visualizes the graph | None | N/A |
| reset_database.py | **DEPRECATED** | 2025-04-24 | Resets the database | Misleading name, drops all tables | reset_derived_tables.py or reset_non_osm_tables.py |
| reset_derived_tables.py | **STABLE** | 2025-04-24 | Resets only derived tables | None | N/A |
| reset_non_osm_tables.py | **STABLE** | 2025-04-24 | Resets all non-OSM tables | None | N/A |
| reset_all_tables.py | **STABLE** | 2025-04-24 | Resets all tables | None | N/A |
| run_water_obstacle_pipeline_crs.py | **DEPRECATED** | 2025-04-22 | Original water obstacle pipeline | Path issues, parameter naming mismatch | run_water_obstacle_pipeline_improved.py |
| run_water_obstacle_pipeline_improved.py | **STABLE** | 2025-04-23 | Improved water obstacle pipeline | None | N/A |
| run_water_obstacle_pipeline_boundary.py | **STABLE** | 2025-04-23 | Water boundary approach pipeline | None | N/A |
| run_water_obstacle_pipeline_boundary_hexagon.py | **STABLE** | 2025-04-25 | Boundary hexagon layer pipeline | None | N/A |
| run_boundary_hexagon_pipeline.py | **STABLE** | 2025-04-25 | Boundary hexagon layer pipeline wrapper | None | N/A |
| run_water_obstacle_pipeline_delaunay.py | **EXPERIMENTAL** | 2025-04-22 | Delaunay triangulation pipeline | Performance issues with large datasets | run_water_obstacle_pipeline_improved.py |

## SQL Files

| Component | Status | Last Updated | Description | Known Issues | Recommended Alternative |
|-----------|--------|--------------|-------------|--------------|------------------------|
| 01_extract_water_features_3857.sql | **STABLE** | 2025-04-23 | Extracts water features | None | N/A |
| 02_create_water_buffers_3857.sql | **STABLE** | 2025-04-23 | Creates water buffers | None | N/A |
| 03_dissolve_water_buffers_3857.sql | **STABLE** | 2025-04-23 | Dissolves water buffers | Memory issues with large datasets | N/A |
| 04_create_terrain_grid_3857.sql | **STABLE** | 2025-04-23 | Creates terrain grid | None | N/A |
| 05_create_terrain_edges_3857.sql | **STABLE** | 2025-04-23 | Creates terrain edges | None | N/A |
| 06_create_water_edges_3857.sql | **DEPRECATED** | 2025-04-22 | Original water edge creation | Poor connectivity | 06_create_water_edges_improved_3857.sql |
| 06_create_water_edges_improved_3857.sql | **STABLE** | 2025-04-23 | Improved water edge creation | None | N/A |
| 06_create_water_boundary_edges_3857.sql | **STABLE** | 2025-04-23 | Water boundary edge creation | None | N/A |
| 04_create_terrain_grid_boundary_hexagon.sql | **STABLE** | 2025-04-25 | Creates terrain grid with boundary hexagons | None | N/A |
| 05_create_boundary_nodes.sql | **STABLE** | 2025-04-25 | Creates boundary nodes | None | N/A |
| 06_create_water_boundary_nodes.sql | **STABLE** | 2025-04-25 | Creates water boundary nodes | None | N/A |
| 07_create_boundary_hexagon_edges.sql | **STABLE** | 2025-04-25 | Creates boundary hexagon edges | None | N/A |
| 07_create_environmental_tables_3857.sql | **STABLE** | 2025-04-23 | Creates environmental tables | None | N/A |
| create_obstacle_boundary_graph.sql | **STABLE** | 2025-04-24 | Creates obstacle boundary graph | None | N/A |

## Configuration Files

| Component | Status | Last Updated | Description | Known Issues | Recommended Alternative |
|-----------|--------|--------------|-------------|--------------|------------------------|
| crs_standardized_config.json | **STABLE** | 2025-04-23 | Standard configuration | None | N/A |
| crs_standardized_config_improved.json | **STABLE** | 2025-04-23 | Configuration with improved water edge creation | None | N/A |
| crs_standardized_config_boundary.json | **STABLE** | 2025-04-23 | Configuration for water boundary approach | None | N/A |
| crs_standardized_config_boundary_hexagon.json | **STABLE** | 2025-04-25 | Configuration for boundary hexagon layer approach | None | N/A |
| delaunay_config.json | **EXPERIMENTAL** | 2025-04-22 | Configuration for Delaunay triangulation | None | N/A |

## Utilities

| Component | Status | Last Updated | Description | Known Issues | Recommended Alternative |
|-----------|--------|--------------|-------------|--------------|------------------------|
| config_loader_3857.py | **STABLE** | 2025-04-23 | Loads configuration files | None | N/A |
| logging_utils.py | **STABLE** | 2025-04-23 | Logging utilities | None | N/A |

## Visualization Tools

| Component | Status | Last Updated | Description | Known Issues | Recommended Alternative |
|-----------|--------|--------------|-------------|--------------|------------------------|
| visualize.py | **STABLE** | 2025-04-23 | Visualizes the graph | None | N/A |
| visualize_obstacle_boundary_graph.py | **STABLE** | 2025-04-24 | Visualizes the obstacle boundary graph | None | N/A |
| visualize_boundary_hexagon_layer.py | **STABLE** | 2025-04-25 | Visualizes the boundary hexagon layer graph | None | N/A |
| visualize_delaunay_triangulation.py | **EXPERIMENTAL** | 2025-04-22 | Visualizes Delaunay triangulation | None | N/A |

## Documentation

| Component | Status | Last Updated | Description | Known Issues | Recommended Alternative |
|-----------|--------|--------------|-------------|--------------|------------------------|
| README.md | **STABLE** | 2025-04-25 | Main project documentation | None | N/A |
| database_schema.md | **STABLE** | 2025-04-23 | Database schema documentation | None | N/A |
| project_organization.md | **STABLE** | 2025-04-23 | Project structure overview | None | N/A |
| water_edge_creation_proposal.md | **STABLE** | 2025-04-23 | Proposal for improved water edge creation | None | N/A |
| water_boundary_approach.md | **STABLE** | 2025-04-23 | Documentation of water boundary approach | None | N/A |
| direct_water_boundary_conversion.md | **STABLE** | 2025-04-24 | Documentation of direct water boundary conversion | None | N/A |
| boundary_hexagon_layer_implementation_plan.md | **STABLE** | 2025-04-25 | Documentation of boundary hexagon layer implementation | None | N/A |
| worklog.md | **STABLE** | 2025-04-24 | Development worklog | None | N/A |
| test_plan.md | **STABLE** | 2025-04-22 | Test plan | None | N/A |
| component_status.md | **STABLE** | 2025-04-25 | Component status documentation | None | N/A |
