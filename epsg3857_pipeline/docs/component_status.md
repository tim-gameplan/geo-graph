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
| Hexagon Obstacle Boundary | **STABLE** | 2025-04-25 | Combines hexagonal grid with precise water obstacle boundaries | None | N/A |
| Voronoi Obstacle Boundary | **STABLE** | 2025-04-26 | Uses Voronoi diagrams for natural connections between terrain and water | None | N/A |
| Reversed Voronoi Obstacle Boundary | **STABLE** | 2025-04-27 | Uses reversed Voronoi approach for more natural connections | None | N/A |
| Delaunay Triangulation | **EXPERIMENTAL** | 2025-04-22 | Uses Delaunay triangulation for terrain representation | Performance issues with large datasets | Standard Pipeline |
| Boundary Hexagon Layer | **STABLE** | 2025-04-30 | Preserves hexagons at water boundaries for better connectivity and uses land portions of water hexagons to connect boundary nodes to water boundary nodes. Now includes terrain edges in the unified graph. | None | N/A |

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
| run_voronoi_connection_test.py | **STABLE** | 2025-04-28 | Runs and visualizes Voronoi connection strategies test | None | N/A |
| run_voronoi_test.sh | **STABLE** | 2025-04-28 | Shell script wrapper for Voronoi connection test | None | N/A |
| run_epsg3857_pipeline.py | **STABLE** | 2025-04-23 | Main pipeline runner | None | N/A |
| run_obstacle_boundary_pipeline.py | **STABLE** | 2025-04-24 | Obstacle boundary pipeline runner | None | N/A |
| run_hexagon_obstacle_boundary_pipeline.py | **STABLE** | 2025-04-25 | Hexagon obstacle boundary pipeline runner | None | N/A |
| run_voronoi_obstacle_boundary_pipeline.py | **STABLE** | 2025-04-26 | Voronoi obstacle boundary pipeline runner | None | N/A |
| run_reversed_voronoi_obstacle_boundary_pipeline.py | **STABLE** | 2025-04-27 | Reversed Voronoi obstacle boundary pipeline runner | None | N/A |
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
| run_boundary_hexagon_pipeline.py | **STABLE** | 2025-04-28 | Boundary hexagon layer pipeline wrapper with integrated visualization | None | N/A |
| run_boundary_hexagon_layer_pipeline.py | **STABLE** | 2025-04-30 | Enhanced boundary hexagon layer pipeline with land portions of water hexagons | None | N/A |
| run_water_obstacle_pipeline_delaunay.py | **EXPERIMENTAL** | 2025-04-22 | Delaunay triangulation pipeline | Performance issues with large datasets | run_water_obstacle_pipeline_improved.py |

## SQL Files

| Component | Status | Last Updated | Description | Known Issues | Recommended Alternative |
|-----------|--------|--------------|-------------|--------------|------------------------|
| voronoi_connection_test.sql | **STABLE** | 2025-04-28 | Tests different connection strategies for water boundaries | None | N/A |
| 01_extract_water_features_3857.sql | **STABLE** | 2025-04-23 | Extracts water features | None | N/A |
| 02_create_water_buffers_3857.sql | **STABLE** | 2025-04-23 | Creates water buffers | None | N/A |
| 03_dissolve_water_buffers_3857.sql | **STABLE** | 2025-04-23 | Dissolves water buffers | Memory issues with large datasets | N/A |
| 04_create_terrain_grid_3857.sql | **STABLE** | 2025-04-23 | Creates terrain grid | None | N/A |
| 04_create_terrain_grid_hexagon.sql | **STABLE** | 2025-04-25 | Creates hexagonal terrain grid with classification | None | N/A |
| 05_create_terrain_edges_3857.sql | **STABLE** | 2025-04-23 | Creates terrain edges | None | N/A |
| 06_create_water_edges_3857.sql | **DEPRECATED** | 2025-04-22 | Original water edge creation | Poor connectivity | 06_create_water_edges_improved_3857.sql |
| 06_create_water_edges_improved_3857.sql | **STABLE** | 2025-04-23 | Improved water edge creation | None | N/A |
| 06_create_water_boundary_edges_3857.sql | **STABLE** | 2025-04-23 | Water boundary edge creation | None | N/A |
| 04_create_terrain_grid_boundary_hexagon.sql | **STABLE** | 2025-04-30 | Creates terrain grid with boundary hexagons and identifies land portions of water hexagons | None | N/A |
| 04a_create_terrain_edges_hexagon.sql | **STABLE** | 2025-04-30 | Creates edges between terrain grid points (land and boundary hexagons) | None | N/A |
| 05_create_boundary_nodes_3857.sql | **STABLE** | 2025-04-28 | Creates boundary nodes with enhanced water boundary and bridge nodes | None | N/A |
| 05_create_boundary_nodes_hexagon.sql | **STABLE** | 2025-04-30 | Creates boundary nodes, water boundary nodes, and land portion nodes | None | N/A |
| 06_create_boundary_edges_3857.sql | **STABLE** | 2025-04-28 | Creates boundary edges with directional filtering and bridge connections | None | N/A |
| 06_create_boundary_edges_hexagon.sql | **STABLE** | 2025-04-30 | Creates connections between boundary nodes, land portion nodes, and water boundary nodes | None | N/A |
| 07_create_unified_boundary_graph_hexagon.sql | **STABLE** | 2025-04-30 | Creates unified boundary graph for the boundary hexagon layer approach | None | N/A |
| 07_create_unified_boundary_graph_3857.sql | **STABLE** | 2025-04-25 | Creates unified boundary graph | None | N/A |
| 07_create_environmental_tables_3857.sql | **STABLE** | 2025-04-23 | Creates environmental tables | None | N/A |
| create_obstacle_boundary_graph.sql | **STABLE** | 2025-04-24 | Creates obstacle boundary graph | None | N/A |
| create_hexagon_obstacle_boundary_graph.sql | **STABLE** | 2025-04-25 | Creates hexagon obstacle boundary graph | None | N/A |
| create_voronoi_obstacle_boundary_graph.sql | **STABLE** | 2025-04-26 | Creates Voronoi obstacle boundary graph | None | N/A |
| create_reversed_voronoi_obstacle_boundary_graph.sql | **STABLE** | 2025-04-27 | Creates Reversed Voronoi obstacle boundary graph | None | N/A |

## Configuration Files

| Component | Status | Last Updated | Description | Known Issues | Recommended Alternative |
|-----------|--------|--------------|-------------|--------------|------------------------|
| crs_standardized_config.json | **STABLE** | 2025-04-23 | Standard configuration | None | N/A |
| crs_standardized_config_improved.json | **STABLE** | 2025-04-23 | Configuration with improved water edge creation | None | N/A |
| crs_standardized_config_boundary.json | **STABLE** | 2025-04-23 | Configuration for water boundary approach | None | N/A |
| crs_standardized_config_boundary_hexagon.json | **STABLE** | 2025-04-25 | Configuration for boundary hexagon layer approach | None | N/A |
| boundary_hexagon_layer_config.json | **STABLE** | 2025-04-30 | Enhanced configuration for boundary hexagon layer approach | None | N/A |
| hexagon_obstacle_boundary_config.json | **STABLE** | 2025-04-25 | Configuration for hexagon obstacle boundary approach | None | N/A |
| voronoi_obstacle_boundary_config.json | **STABLE** | 2025-04-26 | Configuration for Voronoi obstacle boundary approach | None | N/A |
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
| visualize_hexagon_obstacle_boundary.py | **STABLE** | 2025-04-25 | Visualizes the hexagon obstacle boundary graph | None | N/A |
| visualize_hexagon_obstacle_boundary_components.py | **STABLE** | 2025-04-25 | Visualizes the hexagon obstacle boundary components | None | N/A |
| visualize_voronoi_obstacle_boundary.py | **STABLE** | 2025-04-26 | Visualizes the Voronoi obstacle boundary graph | None | N/A |
| visualize_boundary_hexagon_layer.py | **STABLE** | 2025-04-30 | Visualizes the boundary hexagon layer graph with land portions of water hexagons | None | N/A |
| visualize_unified_boundary_graph.py | **STABLE** | 2025-04-30 | Visualizes the unified boundary graph with terrain edges, boundary nodes, and water obstacle edges | None | N/A |
| visualize_delaunay_triangulation.py | **EXPERIMENTAL** | 2025-04-22 | Visualizes Delaunay triangulation | None | N/A |

## Documentation

| Component | Status | Last Updated | Description | Known Issues | Recommended Alternative |
|-----------|--------|--------------|-------------|--------------|------------------------|
| voronoi_connection_test_README.md | **STABLE** | 2025-04-28 | User guide for Voronoi connection strategies test | None | N/A |
| voronoi_connection_strategies_summary.md | **STABLE** | 2025-04-28 | Comprehensive overview of connection strategies | None | N/A |
| README.md | **STABLE** | 2025-04-26 | Main project documentation | None | N/A |
| database_schema.md | **STABLE** | 2025-04-23 | Database schema documentation | None | N/A |
| project_organization.md | **STABLE** | 2025-04-23 | Project structure overview | None | N/A |
| water_edge_creation_proposal.md | **STABLE** | 2025-04-23 | Proposal for improved water edge creation | None | N/A |
| water_boundary_approach.md | **STABLE** | 2025-04-23 | Documentation of water boundary approach | None | N/A |
| direct_water_boundary_conversion.md | **STABLE** | 2025-04-24 | Documentation of direct water boundary conversion | None | N/A |
| hexagon_obstacle_boundary_pipeline.md | **STABLE** | 2025-04-25 | Documentation of hexagon obstacle boundary approach | None | N/A |
| voronoi_connection_strategy.md | **STABLE** | 2025-04-26 | Documentation of Voronoi-based connection strategy | None | N/A |
| reversed_voronoi_connection_strategy.md | **STABLE** | 2025-04-27 | Documentation of Reversed Voronoi-based connection strategy | None | N/A |
| boundary_hexagon_layer_implementation_plan.md | **STABLE** | 2025-04-25 | Documentation of boundary hexagon layer implementation | None | N/A |
| boundary_hexagon_layer_approach.md | **STABLE** | 2025-04-30 | Comprehensive documentation of boundary hexagon layer approach | None | N/A |
| unified_boundary_graph_enhancement_summary.md | **STABLE** | 2025-04-30 | Documentation of the unified boundary graph enhancement | None | N/A |
| pipeline_comparison.md | **STABLE** | 2025-04-26 | Comparison of different pipeline approaches | None | N/A |
| worklog.md | **STABLE** | 2025-04-26 | Development worklog | None | N/A |
| test_plan.md | **STABLE** | 2025-04-22 | Test plan | None | N/A |
| component_status.md | **STABLE** | 2025-04-30 | Component status documentation | None | N/A |
