#!/usr/bin/env python3
"""
File Management Utilities

This module provides utilities for managing file paths and naming conventions
for the terrain system project, particularly for visualization outputs.
"""

import os
import datetime
from pathlib import Path
from typing import Dict, Any, Optional


def get_timestamp() -> str:
    """
    Get the current timestamp in YYYY-MM-DD_HH-MM-SS format.
    
    Returns:
        str: Formatted timestamp
    """
    now = datetime.datetime.now()
    return now.strftime("%Y-%m-%d_%H-%M-%S")


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


def setup_package_structure() -> None:
    """
    Set up the package structure by creating __init__.py files.
    """
    # Create __init__.py in utils directory
    create_init_file("utils")
    
    # Create __init__.py in output directory
    create_init_file("output")
