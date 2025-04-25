#!/usr/bin/env python3
"""
Configuration Loader for EPSG:3857 Pipeline

This script loads and validates configuration files for the EPSG:3857 pipeline.
"""

import os
import sys
import json
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('config_loader_3857')

class ConfigLoader:
    """Configuration loader for the EPSG:3857 pipeline."""
    
    def __init__(self, config_file):
        """Initialize the configuration loader."""
        self.config_file = config_file
        self.config = None
        
        # Load the configuration file
        self.load_config()
    
    def load_config(self):
        """Load the configuration file."""
        logger.info(f"Loading configuration file: {self.config_file}")
        
        try:
            with open(self.config_file, 'r') as f:
                self.config = json.load(f)
            
            logger.info(f"Configuration file loaded successfully")
            return True
        except Exception as e:
            logger.error(f"Error loading configuration file: {e}")
            return False
    
    def get_crs(self):
        """Get the coordinate reference system configuration."""
        if not self.config:
            logger.error("Configuration not loaded")
            return None
        
        crs = self.config.get('crs', {})
        storage = crs.get('storage', 3857)
        export = crs.get('export', 4326)
        analysis = crs.get('analysis', 3857)
        
        return storage, export, analysis
    
    def get_water_feature_types(self):
        """Get the water feature types."""
        if not self.config:
            logger.error("Configuration not loaded")
            return [], []
        
        water_features = self.config.get('water_features', {})
        polygon_types = water_features.get('polygon_types', [])
        line_types = water_features.get('line_types', [])
        
        return polygon_types, line_types
    
    def get_water_buffers(self):
        """Get the water buffer sizes."""
        if not self.config:
            logger.error("Configuration not loaded")
            return {}
        
        return self.config.get('water_buffers', {})
    
    def get_terrain_grid(self):
        """Get the terrain grid configuration."""
        if not self.config:
            logger.error("Configuration not loaded")
            return {}
        
        return self.config.get('terrain_grid', {})
    
    def get_terrain_grid_delaunay(self):
        """Get the Delaunay terrain grid configuration."""
        if not self.config:
            logger.error("Configuration not loaded")
            return {}
        
        return self.config.get('terrain_grid_delaunay', {})
    
    def get_environmental_conditions(self):
        """Get the environmental conditions configuration."""
        if not self.config:
            logger.error("Configuration not loaded")
            return {}
        
        return self.config.get('environmental_conditions', {})
    
    def get_simplify_tolerance(self):
        """Get the simplify tolerance."""
        if not self.config:
            logger.error("Configuration not loaded")
            return 5
        
        return self.config.get('simplify_tolerance', 5)
    
    def get_sql_params(self):
        """Get all SQL parameters."""
        if not self.config:
            logger.error("Configuration not loaded")
            return {}
        
        # Get CRS
        storage, export, analysis = self.get_crs()
        
        # Get water buffers
        water_buffers = self.get_water_buffers()
        default_buffer = water_buffers.get('default', 50)
        
        # Get terrain grid
        terrain_grid = self.get_terrain_grid()
        grid_spacing = terrain_grid.get('grid_spacing', 200)
        max_edge_length = terrain_grid.get('max_edge_length', 500)
        
        # Get Delaunay terrain grid
        terrain_grid_delaunay = self.get_terrain_grid_delaunay()
        delaunay_grid_spacing = terrain_grid_delaunay.get('grid_spacing', 200)
        boundary_point_spacing = terrain_grid_delaunay.get('boundary_point_spacing', 100)
        delaunay_simplify_tolerance = terrain_grid_delaunay.get('simplify_tolerance', 5)
        delaunay_max_edge_length = terrain_grid_delaunay.get('max_edge_length', 500)
        
        # Get environmental conditions
        env_conditions = self.get_environmental_conditions()
        default_speed = env_conditions.get('default_speed', 5.0)
        water_speed_factor = env_conditions.get('water_speed_factor', 0.2)
        uphill_speed_factor = env_conditions.get('uphill_speed_factor', 0.8)
        downhill_speed_factor = env_conditions.get('downhill_speed_factor', 1.2)
        
        # Get water crossing parameters
        water_crossing = self.config.get('water_crossing', {})
        connectivity_check_enabled = water_crossing.get('connectivity_check_enabled', True)
        max_crossing_distance = water_crossing.get('max_crossing_distance', 2000)
        
        # Get simplify tolerance
        simplify_tolerance = self.get_simplify_tolerance()
        
        # Create SQL parameters
        params = {
            'storage_srid': storage,
            'export_srid': export,
            'analysis_srid': analysis,
            'default_buffer': default_buffer,
            'grid_spacing': grid_spacing,
            'max_edge_length': max_edge_length,
            'delaunay_grid_spacing': delaunay_grid_spacing,
            'boundary_point_spacing': boundary_point_spacing,
            'delaunay_simplify_tolerance': delaunay_simplify_tolerance,
            'delaunay_max_edge_length': delaunay_max_edge_length,
            'default_speed': default_speed,
            'water_speed_factor': water_speed_factor,
            'uphill_speed_factor': uphill_speed_factor,
            'downhill_speed_factor': downhill_speed_factor,
            'simplify_tolerance': simplify_tolerance,
            'connection_dist': max_edge_length,
            'connectivity_check_enabled': connectivity_check_enabled,
            'max_crossing_distance': max_crossing_distance
        }
        
        # Add water buffer sizes
        for feature_type, buffer_size in water_buffers.items():
            # Add both naming conventions for backward compatibility
            params[f'buffer_{feature_type}'] = buffer_size
            params[f'{feature_type}_buffer'] = buffer_size
        
        return params

def load_config(config_file):
    """Load a configuration file."""
    loader = ConfigLoader(config_file)
    if loader.config:
        return loader
    return None

if __name__ == "__main__":
    # Parse command line arguments
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Load and validate configuration files for the EPSG:3857 pipeline"
    )
    
    parser.add_argument(
        "config_file",
        help="Configuration file to load"
    )
    
    args = parser.parse_args()
    
    # Load the configuration file
    loader = load_config(args.config_file)
    if not loader:
        sys.exit(1)
    
    # Print the configuration
    print(json.dumps(loader.config, indent=2))
    
    # Print the SQL parameters
    print("\nSQL Parameters:")
    for key, value in loader.get_sql_params().items():
        print(f"{key}: {value}")
