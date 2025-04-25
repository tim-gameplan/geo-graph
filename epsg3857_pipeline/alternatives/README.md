# Alternative Approaches

This directory contains alternative approaches to the EPSG:3857 terrain graph pipeline.

## Overview

These approaches are stable and functional but are not the primary recommended approach. They are provided for comparison, specific use cases, or historical reference.

## Components

### Standard

The original standard approach with basic water edge creation:

- `run_water_obstacle_pipeline_crs.py`: Standard pipeline runner
- `06_create_water_edges_3857.sql`: Standard water edge creation

### Fixed

An approach with fixed water edge creation:

- `run_water_obstacle_pipeline_fixed.py`: Fixed pipeline runner
- `06_create_water_edges_fixed_3857.sql`: Fixed water edge creation

### Water Boundary

An approach that treats water obstacles as navigable boundaries:

- `run_water_obstacle_pipeline_boundary.py`: Water boundary pipeline runner
- `04_create_terrain_grid_with_water_3857.sql`: Terrain grid with water
- `05_create_terrain_edges_with_water_3857.sql`: Terrain edges with water
- `06_create_water_boundary_edges_3857.sql`: Water boundary edges

### Obstacle Boundary

An approach that directly converts water obstacle polygons to graph elements:

- `run_obstacle_boundary_pipeline.py`: Obstacle boundary pipeline runner
- `run_obstacle_boundary_graph.py`: Obstacle boundary graph creator
- `visualize_obstacle_boundary_graph.py`: Obstacle boundary graph visualizer
- `create_obstacle_boundary_graph.sql`: Obstacle boundary graph SQL

## Usage

See the main README.md file for usage instructions.
