# Running the Latest Pipeline

This document explains how to run the most recent pipeline to create derived tables in PostGIS from the loaded OSM data.

## Overview

The latest pipeline is the renamed tables pipeline, which implements the Pipeline Stage Prefixing naming convention for tables in the Boundary Hexagon Layer Pipeline. This pipeline creates derived tables in PostGIS from the loaded OSM data, with table names that follow the new naming convention.

## Prerequisites

Before running the pipeline, make sure you have:

1. Loaded OSM data into the PostGIS database
2. Docker and Docker Compose installed
3. The PostGIS container running

## Running the Pipeline

To run the latest pipeline, use the following command:

```bash
python epsg3857_pipeline/run_latest_pipeline.py
```

This will run the renamed tables pipeline, which creates derived tables in PostGIS from the loaded OSM data.

### Command-line Options

The pipeline supports the following command-line options:

- `--verbose`: Print verbose output
- `--no-compatibility-views`: Do not create backward compatibility views
- `--container`: Name of the Docker container (default: `db`)

Example:

```bash
python epsg3857_pipeline/run_latest_pipeline.py --verbose
```

## Pipeline Stages

The pipeline consists of the following stages:

1. **Extract Water Features**: Extract water features from OSM data
2. **Create Water Buffers**: Create buffers around water features
3. **Dissolve Water Buffers**: Dissolve water buffers and create water obstacles
4. **Create Terrain Grid**: Create a hexagonal grid and classify cells
5. **Create Terrain Edges**: Create edges between terrain grid cells
6. **Create Boundary Nodes**: Create nodes at the boundary of water and land
7. **Create Boundary Edges**: Create edges between boundary nodes
8. **Create Unified Boundary Graph**: Create a unified graph of boundary nodes and edges

## Output Tables

The pipeline creates the following tables:

- `s01_water_features_polygon`: Polygon water features
- `s01_water_features_line`: Line water features
- `s02_water_buffers`: Buffers around water features
- `s03_water_buffers_dissolved`: Dissolved water buffers
- `s03_water_obstacles`: Water obstacles
- `s04_grid_hex_complete`: Complete hexagonal grid
- `s04_grid_hex_classified`: Classified hexagonal grid
- `s04_grid_water_with_land`: Water hexagons with land
- `s04_grid_water_land_portions`: Water hexagon land portions
- `s04_grid_terrain`: Terrain grid
- `s04_grid_terrain_points`: Terrain grid points
- `s04a_edges_terrain`: Terrain edges
- `s05_nodes_boundary`: Boundary nodes
- `s05_nodes_water_boundary`: Water boundary nodes
- `s05_nodes_land_portion`: Land portion nodes
- `s06_edges_boundary_boundary`: Boundary-boundary edges
- `s06_edges_boundary_land_portion`: Boundary-land portion edges
- `s06_edges_land_portion_water_boundary`: Land portion-water boundary edges
- `s06_edges_water_boundary_water_boundary`: Water boundary-water boundary edges
- `s06_edges_boundary_water_boundary`: Boundary-water boundary edges
- `s06_edges_land_portion_land`: Land portion-land edges
- `s06_edges_all_boundary`: All boundary edges
- `s07_graph_unified_nodes`: Unified boundary nodes
- `s07_graph_unified_edges`: Unified boundary edges
- `s07_graph_unified`: Unified boundary graph

## Backward Compatibility

By default, the pipeline creates backward compatibility views that allow existing code to continue working with the old table names. These views are created after all the tables have been created with the new naming convention.

If you don't want to create these views, you can use the `--no-compatibility-views` option:

```bash
python epsg3857_pipeline/run_latest_pipeline.py --no-compatibility-views
```

## Troubleshooting

If you encounter issues running the pipeline, try the following:

1. Make sure the PostGIS container is running
2. Make sure OSM data has been loaded into the database
3. Run the pipeline with the `--verbose` option to see more detailed output
4. Check the logs for error messages

## Further Information

For more information about the renamed tables pipeline, see the [Renamed Tables Pipeline](renamed_tables_pipeline.md) document.

For a complete mapping of old table names to new table names, see the [Table Naming Convention](table_naming_convention.md) document.