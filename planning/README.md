# Water Obstacle Modeling Pipeline

This directory contains a pipeline for modeling water obstacles in the terrain graph system. The pipeline extracts water features from OpenStreetMap data, creates buffers around them, and assigns crossability scores based on water type and environmental conditions.

## Key Features

- **Parameterized water buffers**: Buffer sizes are determined based on water feature type, attributes, and configuration
- **Crossability scoring**: Water features are assigned crossability scores (0-100) based on type and environmental conditions
- **Decision tracking**: Each water feature includes attributes that track the decisions made during modeling
- **Environmental adaptability**: Crossability scores can be adjusted based on rainfall, temperature, and snow depth
- **Visualization**: The pipeline includes a visualization script to display water obstacles and terrain grid

## Directory Structure

- `config/`: Configuration files for different scenarios
  - `default_config.json`: Default configuration
  - `mississippi_config.json`: Configuration for large rivers
  - `desert_config.json`: Configuration for ephemeral streams
- `sql/`: SQL scripts for the pipeline
  - `01_extract_water_features.sql`: Extract water features from OSM data
  - `02_create_water_buffers.sql`: Create buffers around water features
  - `03_dissolve_water_buffers.sql`: Merge overlapping water buffers
  - `04_create_terrain_grid.sql`: Create a hexagonal grid covering the area
  - `05_create_terrain_edges.sql`: Create edges between terrain grid cells
  - `06_create_water_edges.sql`: Create edges along water buffer boundaries
  - `07_create_environmental_tables.sql`: Create tables for environmental conditions
- `scripts/`: Python scripts for running the pipeline
  - `config_loader.py`: Load configuration from JSON files
  - `run_water_obstacle_pipeline.py`: Run the complete pipeline
  - `update_environmental_conditions.py`: Update environmental conditions
  - `visualize_water_obstacles.py`: Visualize water obstacles and terrain grid
  - `test_water_obstacle_pipeline.py`: Test script for the pipeline

## Decision Tracking Attributes

The pipeline now includes attributes that track the decisions made for each water feature:

1. **Buffer decision tracking**:
   - `buffer_size_m`: The actual buffer size used
   - `buffer_rule_applied`: Which rule determined the buffer size (e.g., "width_attribute", "river_type", "lake_name")

2. **Crossability decision tracking**:
   - `crossability_rule_applied`: Which rule determined the crossability (e.g., "intermittent_stream", "permanent_river")

3. **Dissolved buffer tracking**:
   - `buffer_rules_applied`: Aggregated list of buffer rules applied to features in the group
   - `crossability_rules_applied`: Aggregated list of crossability rules applied to features in the group
   - `avg_buffer_size_m`: Average buffer size for features in the group

## Configuration Parameters

The configuration file (`config/default_config.json`) includes the following parameters:

- `water_features`: Parameters for extracting water features
  - `polygon_types`: Types of polygon water features to extract
  - `line_types`: Types of line water features to extract
  - `min_area_sqm`: Minimum area for polygon water features
  - `include_intermittent`: Whether to include intermittent water features
- `buffer_sizes`: Buffer sizes for different water feature types
- `crossability`: Crossability scores for different water feature types
- `terrain_grid`: Parameters for the terrain grid
- `environmental_conditions`: Default environmental conditions

## Running the Pipeline

### Testing with Iowa Subset

To test the pipeline with the Iowa subset data:

```bash
# Run the complete test
./planning/scripts/test_water_obstacle_pipeline.py

# Skip database reset and import
./planning/scripts/test_water_obstacle_pipeline.py --skip-reset

# Skip environmental condition updates
./planning/scripts/test_water_obstacle_pipeline.py --skip-environmental

# Use a different configuration
./planning/scripts/test_water_obstacle_pipeline.py --config planning/config/mississippi_config.json
```

### Running Individual Steps

You can also run individual steps of the pipeline:

```bash
# Reset the database and import the Iowa subset
python scripts/reset_database.py --reset-all
python scripts/reset_database.py --reset-derived --import data/subsets/iowa-latest.osm_ia-central_r10.0km.osm.pbf

# Run the water obstacle pipeline
python planning/scripts/run_water_obstacle_pipeline.py --config planning/config/default_config.json --sql-dir planning/sql

# Update environmental conditions
python planning/scripts/update_environmental_conditions.py --rainfall 0.8 --temperature 20.0

# Visualize the results
python planning/scripts/visualize_water_obstacles.py --output water_obstacles.png
```

## Analyzing Results

The test script includes SQL queries to analyze the water features and the decisions made during modeling. You can run these queries manually:

```sql
-- Analyze water features extraction
SELECT feature_type, water_type, COUNT(*) 
FROM water_features 
GROUP BY feature_type, water_type 
ORDER BY feature_type, water_type;

-- Analyze buffer decisions
SELECT 
    buffer_rule_applied, 
    COUNT(*), 
    AVG(buffer_size_m) as avg_buffer_size,
    MIN(buffer_size_m) as min_buffer_size,
    MAX(buffer_size_m) as max_buffer_size
FROM water_buf 
GROUP BY buffer_rule_applied 
ORDER BY buffer_rule_applied;

-- Analyze crossability decisions
SELECT 
    crossability_rule_applied, 
    COUNT(*), 
    AVG(crossability) as avg_crossability,
    MIN(crossability) as min_crossability,
    MAX(crossability) as max_crossability
FROM water_buf 
GROUP BY crossability_rule_applied 
ORDER BY crossability_rule_applied;

-- Analyze dissolved buffers
SELECT 
    crossability_group, 
    buffer_rules_applied,
    crossability_rules_applied,
    COUNT(*) as count,
    MIN(crossability) as min_crossability,
    MAX(crossability) as max_crossability
FROM water_buf_dissolved 
GROUP BY crossability_group, buffer_rules_applied, crossability_rules_applied
ORDER BY crossability_group;
```

## Visualization

The visualization script creates a map showing:

- Water buffers colored by crossability
- Terrain grid cells
- Terrain edges
- Water edges colored by cost
- Environmental conditions
- Decision tracking information

You can customize the visualization with command-line options:

```bash
python planning/scripts/visualize_water_obstacles.py --help
```

## Integration with Terrain Graph Pipeline

The water obstacle modeling pipeline can be integrated with the existing terrain graph pipeline by:

1. Using the water edges from this pipeline instead of the current water buffer creation
2. Ensuring that the unified edges table includes the water edges with crossability information
3. Testing the integrated pipeline with different configurations

## Future Improvements

- **Improved crossability models**: Develop more sophisticated models for water crossability based on additional attributes
- **Seasonal variations**: Add support for seasonal variations in water features
- **Machine learning integration**: Use machine learning to predict crossability based on historical data
- **Real-time updates**: Add support for real-time updates based on weather data
