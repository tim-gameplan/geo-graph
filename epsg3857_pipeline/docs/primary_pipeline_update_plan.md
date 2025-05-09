# Primary Pipeline Update Plan

This document outlines the plan for updating the primary pipeline (`run_boundary_hexagon_layer_enhanced_pipeline.py`) to support both the old and new table naming conventions.

## Current Pipeline Structure

The current pipeline runner (`run_boundary_hexagon_layer_enhanced_pipeline.py`) performs the following operations:

1. Loads configuration from a specified file
2. Extracts SQL parameters from the configuration
3. Defines a list of SQL scripts to run
4. Executes each SQL script in sequence
5. Logs the results

## Update Approach

The pipeline will be updated to support both the old and new table naming conventions by:

1. Adding a command-line flag to control whether to use the renamed tables
2. Updating the `run_pipeline` function to use the renamed SQL scripts when the flag is set
3. Creating a wrapper script for the renamed tables pipeline

## Implementation Steps

### 1. Update the `run_pipeline` Function

Update the `run_pipeline` function in `run_boundary_hexagon_layer_enhanced_pipeline.py` to accept a new parameter `use_renamed_tables`:

```python
def run_pipeline(config_path, sql_dir, container_name='db', verbose=False, use_renamed_tables=False):
    """
    Run the water obstacle pipeline with the enhanced boundary hexagon layer approach.
    
    Args:
        config_path (str): Path to the configuration file
        sql_dir (str): Path to the directory containing SQL scripts
        container_name (str): Name of the Docker container
        verbose (bool): Whether to print verbose output
        use_renamed_tables (bool): Whether to use the renamed tables
    
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Load configuration
        config_loader = load_config(config_path)
        if config_loader is None:
            logger.error(f"Failed to load configuration from {config_path}")
            return False
            
        # Get SQL parameters
        params = config_loader.get_sql_params()
        
        if verbose:
            logger.info(f"Loaded configuration from {config_path}")
            logger.info(f"Parameters: {json.dumps(params, indent=2)}")
        
        # Define SQL scripts to run
        sql_scripts = [
            "01_extract_water_features_3857.sql",
            "02_create_water_buffers_3857.sql",
            "03_dissolve_water_buffers_3857.sql",
            "04_create_terrain_grid_boundary_hexagon.sql",
            "04a_create_terrain_edges_hexagon.sql",
            "05_create_boundary_nodes_hexagon.sql",
            "06_create_boundary_edges_hexagon_enhanced.sql",  # Use the enhanced version
            "07_create_unified_boundary_graph_hexagon.sql"
        ]
        
        # Determine the SQL directory to use
        actual_sql_dir = os.path.join(sql_dir, "renamed") if use_renamed_tables else sql_dir
        
        # Add backward compatibility views script if using renamed tables
        if use_renamed_tables:
            sql_scripts.append("create_backward_compatibility_views.sql")
        
        # Run each SQL script
        for script in sql_scripts:
            script_path = os.path.join(actual_sql_dir, script)
            
            if not os.path.exists(script_path):
                logger.error(f"SQL script not found: {script_path}")
                return False
            
            if verbose:
                logger.info(f"Running SQL script: {script}")
            
            # Execute the SQL script
            result = execute_sql_script(script_path, params, container_name, verbose)
            
            if not result:
                logger.error(f"Failed to execute SQL script: {script}")
                return False
        
        logger.info("Pipeline completed successfully")
        return True
    
    except Exception as e:
        logger.error(f"Error running pipeline: {str(e)}")
        return False
```

### 2. Update the Command-Line Interface

Update the command-line interface in `run_boundary_hexagon_layer_enhanced_pipeline.py` to add a new flag `--use-renamed-tables`:

```python
def main():
    """
    Main function to run the pipeline from the command line.
    """
    parser = argparse.ArgumentParser(description='Run the water obstacle pipeline with the enhanced boundary hexagon layer approach.')
    parser.add_argument('--config', type=str, default='epsg3857_pipeline/config/crs_standardized_config_boundary_hexagon.json', help='Path to the configuration file')
    parser.add_argument('--sql-dir', type=str, default='epsg3857_pipeline/core/sql', help='Path to the directory containing SQL scripts')
    parser.add_argument('--container-name', type=str, default='db', help='Name of the Docker container')
    parser.add_argument('--verbose', action='store_true', help='Print verbose output')
    parser.add_argument('--use-renamed-tables', action='store_true', help='Use the renamed tables')
    
    args = parser.parse_args()
    
    # Run the pipeline
    success = run_pipeline(args.config, args.sql_dir, args.container_name, args.verbose, args.use_renamed_tables)
    
    # Exit with appropriate status code
    sys.exit(0 if success else 1)
```

### 3. Create a Wrapper Script for the Renamed Tables Pipeline

Create a new script `run_renamed_tables_pipeline.py` that wraps the primary pipeline with the `--use-renamed-tables` flag set:

```python
#!/usr/bin/env python3
"""
Run the water obstacle pipeline with the enhanced boundary hexagon layer approach using the renamed tables.
"""

import sys
import os
import argparse

# Add the parent directory to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from epsg3857_pipeline.run_boundary_hexagon_layer_enhanced_pipeline import run_pipeline

def main():
    """
    Main function to run the pipeline from the command line.
    """
    parser = argparse.ArgumentParser(description='Run the water obstacle pipeline with the enhanced boundary hexagon layer approach using the renamed tables.')
    parser.add_argument('--config', type=str, default='epsg3857_pipeline/config/crs_standardized_config_boundary_hexagon.json', help='Path to the configuration file')
    parser.add_argument('--sql-dir', type=str, default='epsg3857_pipeline/core/sql', help='Path to the directory containing SQL scripts')
    parser.add_argument('--container-name', type=str, default='db', help='Name of the Docker container')
    parser.add_argument('--verbose', action='store_true', help='Print verbose output')
    
    args = parser.parse_args()
    
    # Run the pipeline with the renamed tables
    success = run_pipeline(args.config, args.sql_dir, args.container_name, args.verbose, use_renamed_tables=True)
    
    # Exit with appropriate status code
    sys.exit(0 if success else 1)

if __name__ == '__main__':
    main()
```

### 4. Update the Documentation

Update the documentation to reflect the changes to the pipeline:

1. Update the README.md file to explain the new `--use-renamed-tables` flag
2. Create a new document explaining how to use the renamed tables pipeline
3. Update any other documentation that references the pipeline

## Testing Plan

The updated pipeline will be tested to ensure it works correctly with both the old and new table naming conventions:

1. Test the pipeline with the `--use-renamed-tables` flag set to `False` (default)
   - Verify that the original SQL scripts are used
   - Verify that the original tables are created
   - Verify that the backward compatibility views script is not run

2. Test the pipeline with the `--use-renamed-tables` flag set to `True`
   - Verify that the renamed SQL scripts are used
   - Verify that the renamed tables are created
   - Verify that the backward compatibility views script is run
   - Verify that the backward compatibility views are created

3. Test the wrapper script `run_renamed_tables_pipeline.py`
   - Verify that it runs the pipeline with the `--use-renamed-tables` flag set to `True`
   - Verify that it produces the same results as running the primary pipeline with the flag set

## Deployment Plan

The updated pipeline will be deployed in the following steps:

1. Create the directory structure for the renamed SQL scripts
2. Implement the renamed SQL scripts
3. Update the primary pipeline as described above
4. Create the wrapper script for the renamed tables pipeline
5. Test the updated pipeline
6. Deploy the updated pipeline

## Conclusion

This plan provides a comprehensive approach for updating the primary pipeline to support both the old and new table naming conventions. By following this plan, we can ensure a smooth transition to the new naming convention while maintaining backward compatibility with existing code.