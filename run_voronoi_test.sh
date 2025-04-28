#!/bin/bash
# Run Voronoi Connection Strategies Test
# This script runs the SQL test script and visualizes the results

# Default values
CONTAINER="geo-graph-db-1"
SQL_FILE="voronoi_connection_test.sql"
OUTPUT_DIR="visualizations"
SHOW_CELLS=false
SKIP_SQL=false

# Parse command line arguments
while [[ $# -gt 0 ]]; do
  case $1 in
    --container)
      CONTAINER="$2"
      shift 2
      ;;
    --sql-file)
      SQL_FILE="$2"
      shift 2
      ;;
    --output-dir)
      OUTPUT_DIR="$2"
      shift 2
      ;;
    --show-cells)
      SHOW_CELLS=true
      shift
      ;;
    --skip-sql)
      SKIP_SQL=true
      shift
      ;;
    --help)
      echo "Usage: $0 [options]"
      echo "Options:"
      echo "  --container CONTAINER    Docker container name (default: geo-graph-db-1)"
      echo "  --sql-file FILE          SQL test file (default: voronoi_connection_test.sql)"
      echo "  --output-dir DIR         Output directory for visualizations (default: visualizations)"
      echo "  --show-cells             Show Voronoi cells in visualizations"
      echo "  --skip-sql               Skip running SQL script (use existing data)"
      echo "  --help                   Show this help message"
      exit 0
      ;;
    *)
      echo "Unknown option: $1"
      echo "Use --help for usage information"
      exit 1
      ;;
  esac
done

# Create output directory
mkdir -p "$OUTPUT_DIR"

# Check if Docker is running
if ! docker ps > /dev/null 2>&1; then
  echo "Error: Docker is not running"
  exit 1
fi

# Check if container is running
if ! docker ps --format '{{.Names}}' | grep -q "^$CONTAINER$"; then
  echo "Error: Container $CONTAINER is not running"
  exit 1
fi

# Check if SQL file exists
if [ ! -f "$SQL_FILE" ]; then
  echo "Error: SQL file $SQL_FILE does not exist"
  exit 1
fi

# Check if Python script exists
if [ ! -f "run_voronoi_connection_test.py" ]; then
  echo "Error: Python script run_voronoi_connection_test.py does not exist"
  exit 1
fi

# Check if required Python packages are installed
if ! python -c "import psycopg2, matplotlib, numpy" > /dev/null 2>&1; then
  echo "Installing required Python packages..."
  pip install psycopg2-binary matplotlib numpy
fi

# Run the test
echo "Running Voronoi Connection Strategies Test..."
echo "Container: $CONTAINER"
echo "SQL file: $SQL_FILE"
echo "Output directory: $OUTPUT_DIR"
echo "Show cells: $SHOW_CELLS"
echo "Skip SQL: $SKIP_SQL"

# Build command
CMD="python run_voronoi_connection_test.py --container $CONTAINER --sql-file $SQL_FILE --output-dir $OUTPUT_DIR"
if [ "$SHOW_CELLS" = true ]; then
  CMD="$CMD --show-cells"
fi
if [ "$SKIP_SQL" = true ]; then
  CMD="$CMD --skip-sql"
fi

# Run command
echo "Executing: $CMD"
eval "$CMD"

# Check if visualization was created
if [ -f "$OUTPUT_DIR/connection_strategies_comparison.png" ]; then
  echo "Visualization created successfully: $OUTPUT_DIR/connection_strategies_comparison.png"
  
  # Try to open the visualization
  if command -v open > /dev/null 2>&1; then
    open "$OUTPUT_DIR/connection_strategies_comparison.png"
  elif command -v xdg-open > /dev/null 2>&1; then
    xdg-open "$OUTPUT_DIR/connection_strategies_comparison.png"
  elif command -v start > /dev/null 2>&1; then
    start "$OUTPUT_DIR/connection_strategies_comparison.png"
  else
    echo "Visualization available at: $OUTPUT_DIR/connection_strategies_comparison.png"
  fi
else
  echo "Error: Visualization was not created"
  exit 1
fi

echo "Done!"
