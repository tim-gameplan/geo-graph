# Water Obstacle Pipeline

This document describes the water obstacle pipeline, which processes OpenStreetMap (OSM) water features to create water obstacles for terrain-aware routing.

## Overview

The water obstacle pipeline processes OSM water features (polygons and lines) to create water obstacles that can be used in terrain-aware routing. The pipeline:

1. Extracts water features from OSM data
2. Creates buffers around water features based on their type and attributes
3. Dissolves overlapping water buffers to simplify analysis
4. Creates a terrain grid for the study area
5. Creates terrain edges connecting grid cells
6. Creates water edges representing water obstacles
7. Adds environmental conditions to the water edges

## Pipeline Architecture

```
                 ┌───────────────────────────────┐
                 │  Geofabrik PBF (Iowa)         │
                 └──────────────┬────────────────┘
                                ▼
                    (1) osm2pgsql --flex
                                ▼
                ┌───────────────────────────────┐
                │   PostGIS Database            │
                │  • planet_osm_polygon         │
                │  • planet_osm_line            │
                └─────────┬─────────────────────┘
                          ▼
                 (2) Extract Water Features
                          ▼
                ┌───────────────────────────────┐
                │   water_features              │
                └─────────┬─────────────────────┘
                          ▼
                 (3) Create Water Buffers
                          ▼
                ┌───────────────────────────────┐
                │   water_buf                   │
                └─────────┬─────────────────────┘
                          ▼
                 (4) Dissolve Water Buffers
                          ▼
                ┌───────────────────────────────┐
                │   water_buf_dissolved         │
                └─────────┬─────────────────────┘
                          ▼
                 (5) Create Terrain Grid
                          ▼
                ┌───────────────────────────────┐
                │   terrain_grid                │
                └─────────┬─────────────────────┘
                          ▼
                 (6) Create Terrain Edges
                          ▼
                ┌───────────────────────────────┐
                │   terrain_edges               │
                └─────────┬─────────────────────┘
                          ▼
                 (7) Create Water Edges
                          ▼
                ┌───────────────────────────────┐
                │   water_edges                 │
                └─────────┬─────────────────────┘
                          ▼
                 (8) Add Environmental Conditions
                          ▼
                ┌───────────────────────────────┐
                │   Final Terrain Graph         │
                └───────────────────────────────┘
```

## Key Components

### 1. SQL Scripts

The pipeline uses a series of SQL scripts to process the data:

- `01_extract_water_features.sql`: Extracts water features from OSM data
- `02_create_water_buffers.sql`: Creates buffers around water features
- `03_dissolve_water_buffers.sql`: Dissolves overlapping water buffers
- `04_create_terrain_grid.sql`: Creates a terrain grid for the study area
- `05_create_terrain_edges.sql`: Creates terrain edges connecting grid cells
- `06_create_water_edges.sql`: Creates water edges representing water obstacles
- `07_create_environmental_tables.sql`: Adds environmental conditions to the water edges

### 2. Configuration

The pipeline is configured using JSON files in the `planning/config/` directory:

- `default_config.json`: Default configuration for the pipeline
- `mississippi_config.json`: Configuration for the Mississippi River area
- `desert_config.json`: Configuration for desert areas

The configuration includes parameters for:

- Water feature types to extract
- Buffer sizes for different water feature types
- Crossability values for different water feature types
- Terrain grid cell size and connection distance
- Environmental conditions (rainfall, snow depth, temperature)

### 3. Runner Scripts

The pipeline includes several runner scripts:

- `run_water_obstacle_pipeline.py`: Runs the original water obstacle pipeline
- `run_water_obstacle_pipeline_fixed.py`: Runs the fixed water obstacle pipeline with improved dissolve step
- `test_water_obstacle_pipeline.py`: Tests the water obstacle pipeline on a small subset of data
- `visualize_water_obstacles.py`: Visualizes the water obstacles

## Recent Improvements

### Improved Water Buffer Dissolve

The original water buffer dissolve step had issues with simplification when processing large datasets like the full Iowa PBF. We've made several improvements:

1. **Coordinate System Transformation**:
   - Now transforms geometries to EPSG:3857 (Web Mercator) before simplification
   - Allows for meter-based tolerance values instead of degrees
   - Provides much more consistent simplification across different latitudes

2. **Appropriate Simplification Tolerance**:
   - Reduced the simplification tolerance from 0.1 degrees (approximately 11km at Iowa's latitude) to just 5 meters
   - Preserves much more detail in the water features while still providing necessary simplification

3. **Performance Optimizations**:
   - Increased work memory to 256MB for complex spatial operations
   - Enabled parallel query execution with 4 workers
   - Maintained the area constraint and bounding box clipping to prevent extremely large polygons

These improvements are implemented in the `03_dissolve_water_buffers_improved.sql` file and are used by default in the `run_water_obstacle_pipeline_fixed.py` script.

## Running the Pipeline

### Prerequisites

- PostgreSQL with PostGIS and pgRouting extensions
- OSM data loaded into PostgreSQL using osm2pgsql
- Python 3.6+ with required packages (psycopg2, etc.)

### Running the Pipeline on the Full Iowa Dataset

```bash
# Reset derived tables
python scripts/reset_database.py --reset-derived

# Run the pipeline with the improved dissolve step
python planning/scripts/run_water_obstacle_pipeline_fixed.py \
  --config planning/config/default_config.json \
  --sql-dir planning/sql \
  --verbose
```

### Visualizing the Results

```bash
# Visualize the water obstacles
python planning/scripts/visualize_water_obstacles.py \
  --output output/visualizations/water/iowa_water_obstacles.png \
  --title "Iowa Water Obstacles" \
  --dpi 300
```

## Troubleshooting

### Common Issues

- **Memory errors during dissolve step**: Increase the `work_mem` parameter in the SQL script
- **Slow performance**: Enable parallel query execution and optimize the SQL queries
- **Simplification issues**: Adjust the simplification tolerance in the SQL script
- **Missing water features**: Check the water feature extraction parameters in the configuration

### Debugging

- Use the `--verbose` flag with the runner scripts to see more detailed output
- Check the SQL queries in the SQL scripts to ensure they are correctly extracting and processing the data
- Use the visualization script to visualize the results and check if they look correct

## Future Improvements

- **Further performance optimizations**: Investigate additional ways to optimize the SQL queries
- **Support for additional water feature types**: Add support for additional water feature types (e.g., wetlands)
- **Integration with terrain data**: Incorporate terrain data (elevation, slope) into the water obstacle analysis
- **Dynamic buffer sizes based on water feature attributes**: Adjust buffer sizes based on additional water feature attributes (e.g., width, depth)
