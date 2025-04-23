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
    
    def load(self):
        """Load the configuration file."""
        logger.info(f"Loading configuration from {self.config_file}")
        
        try:
            with open(self.config_file, 'r') as f:
                self.config = json.load(f)
            
            logger.info(f"Configuration loaded successfully")
            return True
        except Exception as e:
            logger.error(f"Error loading configuration: {e}")
            return False
    
    def validate(self):
        """Validate the configuration."""
        if not self.config:
            logger.error("Configuration not loaded")
            return False
        
        # Check required sections
        required_sections = ['crs', 'water_features', 'water_buffers']
        for section in required_sections:
            if section not in self.config:
                logger.error(f"Missing required section: {section}")
                return False
        
        # Check CRS section
        crs_section = self.config['crs']
        required_crs_fields = ['storage', 'export', 'analysis']
        for field in required_crs_fields:
            if field not in crs_section:
                logger.error(f"Missing required CRS field: {field}")
                return False
        
        # Check water features section
        water_features_section = self.config['water_features']
        required_water_features_fields = ['polygon_types', 'line_types']
        for field in required_water_features_fields:
            if field not in water_features_section:
                logger.error(f"Missing required water features field: {field}")
                return False
        
        # Check water buffers section
        water_buffers_section = self.config['water_buffers']
        required_water_buffers_fields = ['default', 'lake', 'river', 'stream']
        for field in required_water_buffers_fields:
            if field not in water_buffers_section:
                logger.error(f"Missing required water buffers field: {field}")
                return False
        
        # Check Delaunay triangulation section if present
        if 'terrain_grid_delaunay' in self.config:
            delaunay_section = self.config['terrain_grid_delaunay']
            required_delaunay_fields = ['grid_spacing', 'boundary_point_spacing', 'simplify_tolerance']
            for field in required_delaunay_fields:
                if field not in delaunay_section:
                    logger.error(f"Missing required Delaunay field: {field}")
                    return False
        
        logger.info("Configuration validated successfully")
        return True
    
    def get_sql_params(self):
        """Get SQL parameters from the configuration."""
        if not self.config:
            logger.error("Configuration not loaded")
            return {}
        
        params = {}
        
        # CRS parameters
        params['storage_srid'] = self.config['crs']['storage']
        params['export_srid'] = self.config['crs']['export']
        params['analysis_srid'] = self.config['crs']['analysis']
        
        # Water buffer parameters
        params['default_buffer'] = self.config['water_buffers']['default']
        params['lake_buffer'] = self.config['water_buffers']['lake']
        params['river_buffer'] = self.config['water_buffers']['river']
        params['stream_buffer'] = self.config['water_buffers']['stream']
        
        # Simplification parameters
        params['simplify_tolerance'] = self.config.get('simplify_tolerance', 5)
        
        # Terrain grid parameters
        params['grid_spacing'] = self.config.get('grid_spacing', 200)
        params['max_edge_length'] = self.config.get('max_edge_length', 500)
        
        # Environmental parameters
        params['default_speed'] = self.config.get('default_speed', 5.0)
        params['water_speed_factor'] = self.config.get('water_speed_factor', 0.2)
        params['uphill_speed_factor'] = self.config.get('uphill_speed_factor', 0.8)
        params['downhill_speed_factor'] = self.config.get('downhill_speed_factor', 1.2)
        
        # Delaunay triangulation parameters
        if 'terrain_grid_delaunay' in self.config:
            delaunay_section = self.config['terrain_grid_delaunay']
            params['grid_spacing'] = delaunay_section.get('grid_spacing', 200)
            params['boundary_point_spacing'] = delaunay_section.get('boundary_point_spacing', 100)
            params['simplify_tolerance'] = delaunay_section.get('simplify_tolerance', 5)
            params['connection_dist'] = delaunay_section.get('max_edge_length', 500)
        
        return params
    
    def get_water_feature_types(self):
        """Get water feature types from the configuration."""
        if not self.config:
            logger.error("Configuration not loaded")
            return [], []
        
        polygon_types = self.config['water_features']['polygon_types']
        line_types = self.config['water_features']['line_types']
        
        return polygon_types, line_types

def load_config(config_file):
    """Load and validate a configuration file."""
    loader = ConfigLoader(config_file)
    
    if not loader.load():
        return None
    
    if not loader.validate():
        return None
    
    return loader

if __name__ == "__main__":
    # Example usage
    if len(sys.argv) < 2:
        print("Usage: python config_loader_3857.py <config_file>")
        sys.exit(1)
    
    config_file = sys.argv[1]
    loader = load_config(config_file)
    
    if loader:
        print("Configuration loaded and validated successfully")
        print("SQL parameters:")
        for key, value in loader.get_sql_params().items():
            print(f"  {key}: {value}")
        
        polygon_types, line_types = loader.get_water_feature_types()
        print("Water polygon types:", polygon_types)
        print("Water line types:", line_types)
    else:
        print("Failed to load or validate configuration")
        sys.exit(1)
