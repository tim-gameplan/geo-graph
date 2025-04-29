#!/bin/bash
# Run Voronoi Connection Test
# This script runs the Voronoi Connection Test and visualizes the results.

# Set default values
CONTAINER="geo-graph-db-1"
OUTPUT="voronoi_connection_test_results.png"
VERBOSE=false
NO_VISUALIZATION=false

# Parse command line arguments
while [[ $# -gt 0 ]]; do
  case $1 in
    --container)
      CONTAINER="$2"
      shift 2
      ;;
    --output)
      OUTPUT="$2"
      shift 2
      ;;
    --verbose)
      VERBOSE=true
      shift
      ;;
    --no-visualization)
      NO_VISUALIZATION=true
      shift
      ;;
    --help)
      echo "Usage: $0 [options]"
      echo "Options:"
      echo "  --container NAME       Docker container name (default: geo-graph-db-1)"
      echo "  --output FILE          Output file name (default: voronoi_connection_test_results.png)"
      echo "  --verbose              Enable verbose output"
      echo "  --no-visualization     Skip visualization and only run the SQL test"
      echo "  --help                 Show this help message"
      exit 0
      ;;
    *)
      echo "Unknown option: $1"
      echo "Use --help for usage information"
      exit 1
      ;;
  esac
done

# Get the directory of this script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Make sure the Python script is executable
chmod +x "$SCRIPT_DIR/run_voronoi_connection_test.py"

# Build the command
CMD="$SCRIPT_DIR/run_voronoi_connection_test.py --container $CONTAINER --output $OUTPUT"

if [ "$VERBOSE" = true ]; then
  CMD="$CMD --verbose"
fi

if [ "$NO_VISUALIZATION" = true ]; then
  CMD="$CMD --no-visualization"
fi

# Run the command
if [ "$VERBOSE" = true ]; then
  echo "Running: $CMD"
fi

python3 $CMD

# Check if the command was successful
if [ $? -eq 0 ]; then
  if [ "$VERBOSE" = true ]; then
    echo "Test completed successfully"
  fi
  
  # If visualization was not skipped, display the output file
  if [ "$NO_VISUALIZATION" = false ]; then
    if [ "$(uname)" == "Darwin" ]; then
      # macOS
      open "$SCRIPT_DIR/$OUTPUT"
    elif [ "$(expr substr $(uname -s) 1 5)" == "Linux" ]; then
      # Linux
      if [ -n "$DISPLAY" ]; then
        if command -v xdg-open > /dev/null; then
          xdg-open "$SCRIPT_DIR/$OUTPUT"
        elif command -v display > /dev/null; then
          display "$SCRIPT_DIR/$OUTPUT"
        fi
      fi
    fi
  fi
else
  echo "Test failed"
  exit 1
fi
