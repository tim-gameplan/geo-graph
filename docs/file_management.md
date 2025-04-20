# Visualization File Management Guide

## Overview

This document outlines the file management strategy for visualization outputs in the terrain graph pipeline project. The goal is to provide a consistent and organized approach to storing and naming visualization files, making it easier to track and manage outputs during development.

## Directory Structure

All visualization outputs are stored in a structured directory hierarchy:

```
output/
├── visualizations/
│   ├── graphml/             # For GraphML visualizations
│   │   └── YYYY-MM-DD_HH-MM-SS_[description]_[parameters].png
│   ├── water/               # For water obstacle visualizations
│   │   └── YYYY-MM-DD_HH-MM-SS_[description]_[parameters].png
│   ├── terrain/             # For terrain grid visualizations
│   │   └── YYYY-MM-DD_HH-MM-SS_[description]_[parameters].png
│   └── combined/            # For combined visualizations
│       └── YYYY-MM-DD_HH-MM-SS_[description]_[parameters].png
├── exports/                 # For exported GraphML files
│   └── YYYY-MM-DD_HH-MM-SS_[description]_[parameters].graphml
└── logs/                    # For visualization and export logs
    └── YYYY-MM-DD_[description].log
```

## Naming Convention

All visualization files follow a consistent naming pattern:

```
YYYY-MM-DD_HH-MM-SS_[description]_[parameters].png
```

Where:
- `YYYY-MM-DD_HH-MM-SS` is the timestamp when the file was created
- `[description]` is a brief description of the visualization
- `[parameters]` are key parameters used to generate the visualization (optional)

Examples:
```
2025-04-20_11-30-00_isochrone_enhanced_lat41.99_lon-93.63_60min.png
2025-04-20_11-35-00_water_obstacles_config-mississippi.png
```

## Utility Functions

The `utils/file_management.py` module provides utility functions for generating file paths according to the naming convention:

### `get_visualization_path()`

```python
def get_visualization_path(
    viz_type: str,
    description: str,
    parameters: Optional[Dict[str, Any]] = None,
    extension: str = "png"
) -> str:
```

This function generates a path for a visualization file with the appropriate timestamp and directory structure.

Parameters:
- `viz_type`: Type of visualization (graphml, water, terrain, combined)
- `description`: Description of the visualization
- `parameters`: Dictionary of parameters used to generate the visualization (optional)
- `extension`: File extension (default: png)

Example:
```python
from utils.file_management import get_visualization_path

# For a GraphML visualization
output_path = get_visualization_path(
    viz_type='graphml',
    description='isochrone_enhanced',
    parameters={'lat': 41.99, 'lon': -93.63, 'minutes': 60}
)
# Result: output/visualizations/graphml/2025-04-20_11-30-00_isochrone_enhanced_lat41.99_lon-93.63_minutes60.png
```

### `get_export_path()`

```python
def get_export_path(
    description: str,
    parameters: Optional[Dict[str, Any]] = None,
    extension: str = "graphml"
) -> str:
```

This function generates a path for an export file with the appropriate timestamp and directory structure.

Parameters:
- `description`: Description of the export
- `parameters`: Dictionary of parameters used to generate the export (optional)
- `extension`: File extension (default: graphml)

Example:
```python
from utils.file_management import get_export_path

# For a GraphML export
export_path = get_export_path(
    description='iowa_central',
    parameters={'minutes': 60}
)
# Result: output/exports/2025-04-20_11-30-00_iowa_central_minutes60.graphml
```

### `get_log_path()`

```python
def get_log_path(description: str = "visualization") -> str:
```

This function generates a path for a log file with the appropriate date and directory structure.

Parameters:
- `description`: Description of the log (default: visualization)

Example:
```python
from utils.file_management import get_log_path

# For a visualization log
log_path = get_log_path("water_visualization")
# Result: output/logs/2025-04-20_water_visualization.log
```

## Using the Visualization Scripts

The visualization scripts have been updated to use the new file management utilities:

### `visualize_graph.py`

```bash
# Basic usage (output file will be auto-generated with timestamp)
python visualize_graph.py slice.graphml

# With custom output path
python visualize_graph.py slice.graphml --output custom_path.png

# With additional parameters
python visualize_graph.py slice.graphml --title "Iowa Central Region" --dpi 600 --show-labels
```

### `visualize_unified.py`

```bash
# Visualize a GraphML file (output file will be auto-generated with timestamp)
python visualize_unified.py --mode graphml --input slice.graphml

# Visualize water obstacles (output file will be auto-generated with timestamp)
python visualize_unified.py --mode water

# Create a combined visualization (output files will be auto-generated with timestamp)
python visualize_unified.py --mode combined --input slice.graphml
```

### `planning/scripts/visualize_water_obstacles.py`

```bash
# Basic usage (output file will be auto-generated with timestamp)
python planning/scripts/visualize_water_obstacles.py

# With custom output path
python planning/scripts/visualize_water_obstacles.py --output custom_path.png

# With additional parameters
python planning/scripts/visualize_water_obstacles.py --title "Water Obstacles" --dpi 600 --description "mississippi_water"
```

## Best Practices

1. **Let the system generate filenames**: Whenever possible, let the system generate filenames with timestamps automatically. This ensures consistency and makes it easier to track when visualizations were created.

2. **Use descriptive descriptions**: Choose clear, descriptive names for the `description` parameter to make it easier to identify the purpose of each visualization.

3. **Include relevant parameters**: When generating visualizations with specific parameters (e.g., coordinates, time limits), include these in the `parameters` dictionary to make them part of the filename.

4. **Use the appropriate visualization type**: Choose the correct `viz_type` for each visualization to ensure it's stored in the appropriate directory.

5. **Check logs for issues**: If a visualization fails or looks incorrect, check the log files in the `output/logs` directory for error messages and warnings.

## Conclusion

By following this file management strategy, we can maintain a clean, organized collection of visualization outputs that are easy to track and manage. The timestamp-based naming convention ensures that we can see the progression of visualizations over time, which is valuable for development and debugging.
