#!/usr/bin/env python3
"""
Configuration loader for the water obstacle modeling system.

This module provides utilities for loading and validating JSON configuration files
that control the behavior of the water obstacle modeling pipeline.
"""

import json
import os
from typing import Dict, Any, Optional, List, Union


class ConfigLoader:
    """Load and validate configuration from JSON files."""

    def __init__(self, config_path: str):
        """
        Load configuration from a JSON file.
        
        Args:
            config_path: Path to the JSON configuration file
        
        Raises:
            FileNotFoundError: If the configuration file doesn't exist
            ValueError: If the configuration is invalid
        """
        if not os.path.exists(config_path):
            raise FileNotFoundError(f"Configuration file not found: {config_path}")
        
        with open(config_path, 'r') as f:
            self.config = json.load(f)
        
        self.validate_config()
    
    def validate_config(self):
        """
        Validate the configuration structure.
        
        Raises:
            ValueError: If required sections or keys are missing
        """
        required_sections = [
            'water_features', 
            'buffer_sizes', 
            'crossability', 
            'terrain_grid', 
            'environmental_conditions'
        ]
        
        for section in required_sections:
            if section not in self.config:
                raise ValueError(f"Missing required configuration section: {section}")
        
        # Validate water_features section
        water_features = self.config['water_features']
        required_water_keys = ['polygon_types', 'line_types', 'min_area_sqm']
        for key in required_water_keys:
            if key not in water_features:
                raise ValueError(f"Missing required key in water_features: {key}")
        
        # Validate buffer_sizes section
        buffer_sizes = self.config['buffer_sizes']
        required_buffer_keys = ['default']
        for key in required_buffer_keys:
            if key not in buffer_sizes:
                raise ValueError(f"Missing required key in buffer_sizes: {key}")
        
        # Validate crossability section
        crossability = self.config['crossability']
        required_cross_keys = ['default']
        for key in required_cross_keys:
            if key not in crossability:
                raise ValueError(f"Missing required key in crossability: {key}")
        
        # Validate terrain_grid section
        terrain_grid = self.config['terrain_grid']
        required_terrain_keys = ['cell_size', 'connection_distance']
        for key in required_terrain_keys:
            if key not in terrain_grid:
                raise ValueError(f"Missing required key in terrain_grid: {key}")
        
        # Validate environmental_conditions section
        env_conditions = self.config['environmental_conditions']
        required_env_keys = ['rainfall', 'snow_depth', 'temperature']
        for key in required_env_keys:
            if key not in env_conditions:
                raise ValueError(f"Missing required key in environmental_conditions: {key}")
    
    def get_value(self, section: str, key: str, default: Optional[Any] = None) -> Any:
        """
        Get a configuration value with an optional default.
        
        Args:
            section: Configuration section name
            key: Configuration key within the section
            default: Default value to return if the key doesn't exist
        
        Returns:
            The configuration value or the default
        
        Raises:
            ValueError: If the section or key doesn't exist and no default is provided
        """
        if section not in self.config:
            if default is not None:
                return default
            raise ValueError(f"Configuration section not found: {section}")
        
        if key not in self.config[section]:
            if default is not None:
                return default
            raise ValueError(f"Configuration key not found: {section}.{key}")
        
        return self.config[section][key]
    
    def get_section(self, section: str) -> Dict[str, Any]:
        """
        Get an entire configuration section.
        
        Args:
            section: Configuration section name
        
        Returns:
            The configuration section as a dictionary
        
        Raises:
            ValueError: If the section doesn't exist
        """
        if section not in self.config:
            raise ValueError(f"Configuration section not found: {section}")
        
        return self.config[section]
    
    def get_sql_params(self) -> Dict[str, Any]:
        """
        Convert configuration to SQL parameters.
        
        Returns:
            A dictionary of SQL parameters derived from the configuration
        """
        params = {}
        
        # Water features parameters
        water_features = self.config['water_features']
        params['polygon_types'] = water_features.get('polygon_types', [])
        params['line_types'] = water_features.get('line_types', [])
        params['min_area_sqm'] = water_features.get('min_area_sqm', 10000)
        params['include_intermittent'] = water_features.get('include_intermittent', True)
        
        # Buffer sizes
        buffer_sizes = self.config['buffer_sizes']
        for water_type, size in buffer_sizes.items():
            params[f'buffer_{water_type}'] = size
        
        # Crossability values
        crossability = self.config['crossability']
        for water_type, value in crossability.items():
            params[f'cross_{water_type}'] = value
        
        # Terrain grid parameters
        terrain_grid = self.config['terrain_grid']
        params['cell_size'] = terrain_grid.get('cell_size', 200)
        params['connection_distance'] = terrain_grid.get('connection_distance', 300)
        
        # Environmental conditions
        env_conditions = self.config['environmental_conditions']
        for condition, value in env_conditions.items():
            params[f'env_{condition}'] = value
        
        return params
    
    def save_to_file(self, output_path: str):
        """
        Save the current configuration to a file.
        
        Args:
            output_path: Path to save the configuration to
        """
        with open(output_path, 'w') as f:
            json.dump(self.config, f, indent=2)
    
    def update_section(self, section: str, updates: Dict[str, Any]):
        """
        Update a configuration section with new values.
        
        Args:
            section: Configuration section name
            updates: Dictionary of updates to apply
        
        Raises:
            ValueError: If the section doesn't exist
        """
        if section not in self.config:
            raise ValueError(f"Configuration section not found: {section}")
        
        self.config[section].update(updates)


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Test configuration loader")
    parser.add_argument("config", help="Path to configuration file")
    parser.add_argument("--validate", action="store_true", help="Validate the configuration")
    parser.add_argument("--show-params", action="store_true", help="Show SQL parameters")
    
    args = parser.parse_args()
    
    try:
        config = ConfigLoader(args.config)
        print(f"Successfully loaded configuration from {args.config}")
        
        if args.validate:
            print("Configuration is valid")
        
        if args.show_params:
            params = config.get_sql_params()
            print("\nSQL Parameters:")
            for key, value in params.items():
                print(f"  {key}: {value}")
    
    except (FileNotFoundError, ValueError) as e:
        print(f"Error: {e}")
