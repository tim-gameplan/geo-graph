# How to Run the Most Recent Pipeline

This document provides a concise guide on how to run the most recent pipeline to create derived tables in PostGIS from the loaded OSM data.

## Quick Start

To run the most recent pipeline, use the following command:

```bash
python epsg3857_pipeline/run_latest_pipeline.py
```

This will run the renamed tables pipeline, which creates all the derived tables in PostGIS from the loaded OSM data.

## Command-line Options

The pipeline supports the following command-line options:

- `--verbose`: Print verbose output
- `--no-compatibility-views`: Do not create backward compatibility views
- `--container`: Specify a different Docker container name (default: `db`)

Example with verbose output:

```bash
python epsg3857_pipeline/run_latest_pipeline.py --verbose
```

## Prerequisites

Before running the pipeline, make sure you have:

1. Loaded OSM data into the PostGIS database
2. Docker and Docker Compose installed
3. The PostGIS container running

## Pipeline Stages

The pipeline runs the following SQL scripts in order:

1. `01_extract_water_features_3857.sql`: Extract water features from OSM data
2. `02_create_water_buffers_3857.sql`: Create buffers around water features
3. `03_dissolve_water_buffers_3857.sql`: Dissolve water buffers and create water obstacles
4. `04_create_terrain_grid_boundary_hexagon.sql`: Create a hexagonal grid and classify cells
5. `04a_create_terrain_edges_hexagon.sql`: Create edges between terrain grid cells
6. `05_create_boundary_nodes_hexagon.sql`: Create nodes at the boundary of water and land
7. `06_create_boundary_edges_hexagon_enhanced.sql`: Create edges between boundary nodes
8. `07_create_unified_boundary_graph_hexagon.sql`: Create a unified graph of boundary nodes and edges
9. `create_backward_compatibility_views.sql`: Create views for backward compatibility

## Troubleshooting

If you encounter issues running the pipeline:

1. Make sure the PostGIS container is running:
   ```bash
   docker compose ps
   ```

2. Make sure OSM data has been loaded into the database:
   ```bash
   docker compose exec db psql -U gis -d gis -c "SELECT COUNT(*) FROM planet_osm_polygon"
   ```

3. Reset the derived tables before running the pipeline:
   ```bash
   python epsg3857_pipeline/tools/database/reset_non_osm_tables.py
   ```

4. Run the pipeline with the `--verbose` option to see more detailed output:
   ```bash
   python epsg3857_pipeline/run_latest_pipeline.py --verbose
   ```

## Further Information

For more detailed information about the pipeline, see:

- `epsg3857_pipeline/docs/running_latest_pipeline.md`: Detailed guide on running the pipeline
- `epsg3857_pipeline/docs/renamed_tables_pipeline.md`: Information about the renamed tables pipeline
- `epsg3857_pipeline/docs/table_naming_convention.md`: Information about the table naming convention