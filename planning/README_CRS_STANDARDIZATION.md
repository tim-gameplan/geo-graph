# CRS Standardization for Terrain System

This README provides an overview of the Coordinate Reference System (CRS) standardization implemented in the Terrain System project.

## Overview

The CRS standardization aims to ensure consistent use of EPSG:3857 (Web Mercator) for all internal processing and EPSG:4326 (WGS84) for export and visualization. This ensures accurate and consistent spatial operations across the entire pipeline.

## Directory Structure

```
planning/
├── config/
│   └── crs_standardized_config.json  # Configuration for CRS standardization
├── scripts/
│   └── run_water_obstacle_pipeline_crs.py  # CRS-standardized water obstacle pipeline
├── sql/
│   ├── 01_extract_water_features_3857.sql  # Extract water features in EPSG:3857
│   ├── 02_create_water_buffers_3857.sql    # Create water buffers in EPSG:3857
│   ├── 03_dissolve_water_buffers_3857.sql  # Dissolve water buffers in EPSG:3857
│   ├── 04_create_terrain_grid_3857.sql     # Create terrain grid in EPSG:3857
│   ├── 05_create_terrain_edges_3857.sql    # Create terrain edges in EPSG:3857
│   ├── 06_create_water_edges_3857.sql      # Create water edges in EPSG:3857
│   └── 07_create_environmental_tables_3857.sql  # Create environmental tables in EPSG:3857
└── tests/
    ├── test_crs_consistency.py  # Unit tests for CRS consistency
    └── test_pipeline_integration.py  # Integration tests for the pipeline
```

## Key Components

### Configuration

The CRS standardization uses a new configuration file, `planning/config/crs_standardized_config.json`, which includes parameters for the CRS-standardized components:

```json
{
    "crs": 3857,
    "water_features": {
        "river_buffer_m": 50,
        "lake_buffer_m": 100,
        "stream_buffer_m": 25
    },
    "terrain_grid": {
        "cell_size": 200,
        "connection_distance": 300
    }
}
```

### SQL Scripts

The SQL scripts have been updated to use EPSG:3857 for all internal processing. Key changes include:

- Using `ST_Transform(geom, 3857)` to transform geometries to EPSG:3857
- Specifying buffer distances in meters
- Using `ST_Transform(geom, 4326)` only when exporting data

### Python Scripts

The Python scripts have been updated to support CRS standardization:

- `planning/scripts/run_water_obstacle_pipeline_crs.py`: Runs the water obstacle pipeline with CRS standardization
- `scripts/run_unified_pipeline_3857.py`: Runs the unified pipeline with CRS standardization
- `tools/export_slice_3857.py`: Exports a slice of the graph with CRS standardization
- `visualize_graph_3857.py`: Visualizes a graph with CRS standardization
- `planning/scripts/visualize_water_obstacles_3857.py`: Visualizes water obstacles with CRS standardization

## Usage

### Running the Water Obstacle Pipeline

```bash
# Run the water obstacle pipeline with CRS standardization
python planning/scripts/run_water_obstacle_pipeline_crs.py --config planning/config/crs_standardized_config.json
```

### Running the Unified Pipeline

```bash
# Run the unified pipeline with CRS standardization
python scripts/run_unified_pipeline_3857.py --config planning/config/crs_standardized_config.json
```

### Exporting a Graph Slice

```bash
# Export a slice with CRS standardization
python tools/export_slice_3857.py --lon -93.63 --lat 41.99 --minutes 60 --outfile test_slice_3857.graphml
```

### Visualizing the Results

```bash
# Visualize a graph with CRS standardization
python visualize_graph_3857.py test_slice_3857.graphml

# Visualize water obstacles with CRS standardization
python planning/scripts/visualize_water_obstacles_3857.py
```

## Testing

The CRS standardization includes unit tests and integration tests:

```bash
# Run unit tests for CRS consistency
python planning/tests/test_crs_consistency.py

# Run integration tests for the pipeline
python planning/tests/test_pipeline_integration.py
```

## Documentation

For more detailed information on the CRS standardization, see the following documents:

- [EPSG Consistency Implementation Plan](../docs/epsg_consistency_implementation_plan.md)
- [EPSG Consistency Visualization and Unified Pipeline](../docs/epsg_consistency_visualization_and_unified.md)
- [EPSG Consistency Testing and Integration](../docs/epsg_consistency_testing_and_integration.md)
- [EPSG Consistency Integration and Conclusion](../docs/epsg_consistency_integration_and_conclusion.md)
- [EPSG Consistency Training and Conclusion](../docs/epsg_consistency_training_and_conclusion.md)
- [EPSG Consistency Summary](../docs/epsg_consistency_summary.md)

## Benefits

The CRS standardization provides several benefits:

1. **Improved accuracy**: Using EPSG:3857 for internal processing ensures that all spatial operations are performed in a metric coordinate system, which is more accurate for distance and area calculations.
2. **Consistent buffer sizes**: Buffer sizes are now specified in meters, which is more intuitive and consistent across different latitudes.
3. **Better performance**: Using a single CRS throughout the pipeline reduces the need for coordinate transformations, which can improve performance.
4. **Simplified code**: Using a consistent CRS makes the code simpler and easier to maintain.

## Best Practices

1. **Always specify buffer distances in meters**: When using EPSG:3857, buffer distances should always be specified in meters.
2. **Use the CRS parameter**: Always specify the CRS parameter when running scripts to ensure consistent behavior.
3. **Transform to EPSG:4326 for visualization**: When visualizing data, transform to EPSG:4326 for better compatibility with mapping libraries.
4. **Check SRID metadata**: When creating new tables, always add SRID metadata to ensure proper CRS handling.

## Troubleshooting

### Common Issues

1. **Incorrect buffer sizes**: If buffer sizes appear incorrect, check that you're using meters as units and that the CRS is set to EPSG:3857.
2. **Misaligned features**: If features appear misaligned, check that all tables have the same CRS.
3. **Performance issues**: If performance is slow, check that you're not performing unnecessary coordinate transformations.

### Debugging

1. **Check SRID metadata**: Use `SELECT ST_SRID(geom) FROM table_name LIMIT 1` to check the SRID of a geometry column.
2. **Verify transformations**: Use `SELECT ST_AsText(ST_Transform(geom, 4326)) FROM table_name LIMIT 1` to verify that transformations are working correctly.
3. **Run tests**: Use the test scripts in `planning/tests/` to verify that the CRS standardization is working correctly.
