#!/bin/bash
# Run tests for the water obstacle modeling pipeline

# Set up error handling
set -e
trap 'echo "Error: Command failed with exit code $?"; exit 1' ERR

# Create output directory if it doesn't exist
mkdir -p output

# Print header
echo "====================================================="
echo "  Water Obstacle Modeling Pipeline Test Runner"
echo "====================================================="
echo

# Check if the Iowa subset exists
SUBSET_PATH="data/subsets/iowa-latest.osm_ia-central_r10.0km.osm.pbf"
if [ ! -f "$SUBSET_PATH" ]; then
    echo "Error: Iowa subset not found at $SUBSET_PATH"
    echo "Please make sure the file exists before running the tests."
    exit 1
fi

# Run import tests
echo "Running import tests..."
./planning/tests/test_script_imports.py
echo "Import tests passed!"
echo

# Ask if the user wants to run the full pipeline
read -p "Do you want to run the full pipeline test? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    # Run the full pipeline test
    echo "Running full pipeline test..."
    ./planning/scripts/test_water_obstacle_pipeline.py --verbose
    
    # Check if the test was successful
    if [ $? -eq 0 ]; then
        echo "Full pipeline test completed successfully!"
        echo "Visualizations saved to the output directory."
    else
        echo "Error: Full pipeline test failed."
        exit 1
    fi
else
    echo "Skipping full pipeline test."
fi

echo
echo "====================================================="
echo "  Test Runner Completed"
echo "====================================================="
