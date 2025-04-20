# File Management Utilities

This document provides an overview of the file management utilities in the `utils/file_management.py` module.

## Overview

The file management utilities provide a consistent way to manage file paths and naming conventions for the terrain system project, particularly for visualization outputs. These utilities ensure that all output files follow a consistent naming convention and are stored in the appropriate directories.

## Directory Structure

The file management utilities create and manage the following directory structure:

```
output/
├── exports/
│   └── YYYY-MM-DD_HH-MM-SS_description_param1-value1.graphml
├── logs/
│   └── YYYY-MM-DD_description.log
└── visualizations/
    ├── combined/
    │   └── YYYY-MM-DD_HH-MM-SS_description_param1-value1.png
    ├── graphml/
    │   └── YYYY-MM-DD_HH-MM-SS_description_param1-value1.png
    ├── terrain/
    │   └── YYYY-MM-DD_HH-MM-SS_description_param1-value1.png
    └── water/
        └── YYYY-MM-DD_HH-MM-SS_description_param1-value1.png
```

## Functions

### `get_timestamp()`

Get the current timestamp in YYYY-MM-DD_HH-MM-SS format.

```python
def get_timestamp() -> str:
    """
    Get the current timestamp in YYYY-MM-DD_HH-MM-SS format.
    
    Returns:
        str: Formatted timestamp
    """
    now = datetime.datetime.now()
    return now.strftime("%Y-%m-%d_%H-%M-%S")
```

### `format_parameters(parameters)`

Format parameters for inclusion in filenames.

```python
def format_parameters(parameters: Dict[str, Any]) -> str:
    """
    Format parameters for inclusion in filenames.
    
    Args:
        parameters: Dictionary of parameters
    
    Returns:
        str: Formatted parameter string
    """
    if not parameters:
        return ""
    
    # Format each parameter as key-value
    param_strs = []
    for key, value in parameters.items():
        # Format numeric values with appropriate precision
        if isinstance(value, float):
            # Use 2 decimal places for most values, but more for coordinates
            if key in ['lat', 'lon', 'latitude', 'longitude']:
                param_str = f"{key}{value:.5f}"
            else:
                param_str = f"{key}{value:.2f}"
        else:
            param_str = f"{key}-{value}"
        
        param_strs.append(param_str)
    
    return "_".join(param_strs)
```

### `get_visualization_path(viz_type, description, parameters, extension)`

Get the path for a visualization file.

```python
def get_visualization_path(
    viz_type: str,
    description: str,
    parameters: Optional[Dict[str, Any]] = None,
    extension: str = "png"
) -> str:
    """
    Get the path for a visualization file.
    
    Args:
        viz_type: Type of visualization (graphml, water, terrain, combined)
        description: Description of the visualization
        parameters: Dictionary of parameters used to generate the visualization
        extension: File extension (default: png)
    
    Returns:
        str: Path to the visualization file
    """
    # Validate visualization type
    valid_types = ["graphml", "water", "terrain", "combined"]
    if viz_type not in valid_types:
        raise ValueError(f"Invalid visualization type: {viz_type}. Must be one of {valid_types}")
    
    # Get timestamp
    timestamp = get_timestamp()
    
    # Format parameters
    param_str = format_parameters(parameters) if parameters else ""
    
    # Build filename
    if param_str:
        filename = f"{timestamp}_{description}_{param_str}.{extension}"
    else:
        filename = f"{timestamp}_{description}.{extension}"
    
    # Build path
    path = os.path.join("output", "visualizations", viz_type, filename)
    
    # Ensure directory exists
    os.makedirs(os.path.dirname(path), exist_ok=True)
    
    return path
```

### `get_export_path(description, parameters, extension)`

Get the path for an export file.

```python
def get_export_path(
    description: str,
    parameters: Optional[Dict[str, Any]] = None,
    extension: str = "graphml"
) -> str:
    """
    Get the path for an export file.
    
    Args:
        description: Description of the export
        parameters: Dictionary of parameters used to generate the export
        extension: File extension (default: graphml)
    
    Returns:
        str: Path to the export file
    """
    # Get timestamp
    timestamp = get_timestamp()
    
    # Format parameters
    param_str = format_parameters(parameters) if parameters else ""
    
    # Build filename
    if param_str:
        filename = f"{timestamp}_{description}_{param_str}.{extension}"
    else:
        filename = f"{timestamp}_{description}.{extension}"
    
    # Build path
    path = os.path.join("output", "exports", filename)
    
    # Ensure directory exists
    os.makedirs(os.path.dirname(path), exist_ok=True)
    
    return path
```

### `get_log_path(description)`

Get the path for a log file.

```python
def get_log_path(description: str = "visualization") -> str:
    """
    Get the path for a log file.
    
    Args:
        description: Description of the log
    
    Returns:
        str: Path to the log file
    """
    # Get date
    date = datetime.datetime.now().strftime("%Y-%m-%d")
    
    # Build filename
    filename = f"{date}_{description}.log"
    
    # Build path
    path = os.path.join("output", "logs", filename)
    
    # Ensure directory exists
    os.makedirs(os.path.dirname(path), exist_ok=True)
    
    return path
```

### `create_init_file(directory)`

Create an `__init__.py` file in the specified directory.

```python
def create_init_file(directory: str) -> None:
    """
    Create an __init__.py file in the specified directory.
    
    Args:
        directory: Directory to create the __init__.py file in
    """
    init_path = os.path.join(directory, "__init__.py")
    if not os.path.exists(init_path):
        with open(init_path, "w") as f:
            f.write("# This file is intentionally left empty to make the directory a Python package.\n")
```

### `setup_package_structure()`

Set up the package structure by creating `__init__.py` files.

```python
def setup_package_structure() -> None:
    """
    Set up the package structure by creating __init__.py files.
    """
    # Create __init__.py in utils directory
    create_init_file("utils")
    
    # Create __init__.py in output directory
    create_init_file("output")
```

## Usage Examples

### Visualization Path

```python
# Get a path for a GraphML visualization
graphml_path = get_visualization_path(
    viz_type="graphml",
    description="enhanced_test",
    parameters={"dpi": 300}
)
# Result: output/visualizations/graphml/2025-04-20_14-19-56_enhanced_test_dpi-300.png

# Get a path for a water visualization
water_path = get_visualization_path(
    viz_type="water",
    description="water_obstacles",
    parameters={"dpi": 300}
)
# Result: output/visualizations/water/2025-04-20_14-20-07_water_obstacles_dpi-300.png
```

### Export Path

```python
# Get a path for a GraphML export
export_path = get_export_path(
    description="enhanced_test",
    parameters={"lon": -93.63, "lat": 41.99, "minutes": 60}
)
# Result: output/exports/2025-04-20_14-18-56_enhanced_test_lon-93.63000_lat41.99000_minutes-60.graphml
```

### Log Path

```python
# Get a path for a visualization log
log_path = get_log_path("visualization")
# Result: output/logs/2025-04-20_visualization.log

# Get a path for a unified visualization log
unified_log_path = get_log_path("unified_visualization")
# Result: output/logs/2025-04-20_unified_visualization.log
```

## Integration with Visualization Scripts

The file management utilities are integrated with the visualization scripts to ensure consistent file naming and organization:

### `visualize_graph.py`

```python
from utils.file_management import get_visualization_path

# ...

# Determine the output file path
if output_file is None:
    # Generate a path using the file management utilities
    description = os.path.splitext(os.path.basename(input_file))[0]
    output_file = get_visualization_path(
        viz_type='graphml',
        description=description,
        parameters={'dpi': dpi}
    )
```

### `visualize_unified.py`

```python
from utils.file_management import get_visualization_path, get_log_path

# Configure logging
log_path = get_log_path("unified_visualization")
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(log_path)
    ]
)

# ...

# Build command
cmd = [
    "python", visualize_water_path,
    "--output", args.output if args.output else get_visualization_path(
        viz_type='water',
        description='water_obstacles',
        parameters={'dpi': args.dpi}
    ),
    "--dpi", str(args.dpi)
]
```

## Best Practices

1. **Always use the file management utilities** for generating file paths to ensure consistent naming and organization.
2. **Include relevant parameters** in the file names to make it easier to identify the contents of the file.
3. **Use descriptive descriptions** to make it clear what the file contains.
4. **Use the appropriate visualization type** to ensure the file is stored in the correct directory.
5. **Use the appropriate extension** to ensure the file is recognized correctly by other tools.
