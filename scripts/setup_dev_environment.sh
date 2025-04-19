#!/bin/bash
# Setup development environment with a subset of OSM data
# This script combines all the steps into a single command for convenience

set -e  # Exit on error

# Default values
INPUT_FILE="data/iowa-latest.osm.pbf"
BENCHMARK="ia-central"
RADIUS=10
PRESERVE_ATTRIBUTES=true
EXPORT_SLICE=true
LON=-93.63
LAT=41.99
EXPORT_RADIUS=5
OUTPUT_FILE="slice_with_attributes.graphml"
SHOW_EXAMPLES=false
ANALYSIS_DIR=""

# Parse command line arguments
while [[ $# -gt 0 ]]; do
  case $1 in
    --input)
      INPUT_FILE="$2"
      shift 2
      ;;
    --benchmark)
      BENCHMARK="$2"
      shift 2
      ;;
    --radius)
      RADIUS="$2"
      shift 2
      ;;
    --no-preserve-attributes)
      PRESERVE_ATTRIBUTES=false
      shift
      ;;
    --no-export)
      EXPORT_SLICE=false
      shift
      ;;
    --lon)
      LON="$2"
      shift 2
      ;;
    --lat)
      LAT="$2"
      shift 2
      ;;
    --export-radius)
      EXPORT_RADIUS="$2"
      shift 2
      ;;
    --output)
      OUTPUT_FILE="$2"
      shift 2
      ;;
    --show-examples)
      SHOW_EXAMPLES=true
      shift
      ;;
    --analysis-dir)
      ANALYSIS_DIR="$2"
      shift 2
      ;;
    --help)
      echo "Usage: $0 [options]"
      echo "Options:"
      echo "  --input FILE             Input OSM PBF file (default: $INPUT_FILE)"
      echo "  --benchmark BENCHMARK    Benchmark location (default: $BENCHMARK)"
      echo "  --radius RADIUS          Extraction radius in km (default: $RADIUS)"
      echo "  --no-preserve-attributes Don't preserve OSM attributes"
      echo "  --no-export              Don't export a slice"
      echo "  --lon LON                Longitude for export (default: $LON)"
      echo "  --lat LAT                Latitude for export (default: $LAT)"
      echo "  --export-radius RADIUS   Export radius in km (default: $EXPORT_RADIUS)"
      echo "  --output FILE            Output GraphML file (default: $OUTPUT_FILE)"
      echo "  --show-examples          Show examples of attribute values"
      echo "  --analysis-dir DIR       Directory to save analysis plots"
      echo "  --help                   Show this help message"
      exit 0
      ;;
    *)
      echo "Unknown option: $1"
      exit 1
      ;;
  esac
done

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
  echo "Error: Docker is not running. Please start Docker and try again."
  exit 1
fi

# Step 1: Start Docker containers
echo "=== Step 1: Starting Docker containers ==="
docker compose up -d

# Step 2: Extract a subset of OSM data
echo "=== Step 2: Extracting OSM subset ==="
SUBSET_FILE="data/subsets/${INPUT_FILE##*/}_${BENCHMARK}_r${RADIUS}km.osm.pbf"
python scripts/extract_osm_subset.py --input "$INPUT_FILE" --benchmark "$BENCHMARK" --radius "$RADIUS"

# Step 3: Reset the database and import the subset
echo "=== Step 3: Resetting database and importing OSM data ==="
python scripts/reset_database.py --reset-all --import "$SUBSET_FILE"

# Step 4: Analyze the OSM attributes
echo "=== Step 4: Analyzing OSM attributes ==="
ANALYZE_CMD="python scripts/analyze_osm_attributes.py"
if [ "$SHOW_EXAMPLES" = true ]; then
  ANALYZE_CMD="$ANALYZE_CMD --show-examples"
fi
if [ -n "$ANALYSIS_DIR" ]; then
  ANALYZE_CMD="$ANALYZE_CMD --output-dir $ANALYSIS_DIR"
fi
$ANALYZE_CMD

# Step 5: Run the pipeline
echo "=== Step 5: Running the pipeline ==="
PIPELINE_CMD="python scripts/run_pipeline.py"
if [ "$PRESERVE_ATTRIBUTES" = true ]; then
  PIPELINE_CMD="$PIPELINE_CMD --preserve-attributes"
fi
$PIPELINE_CMD

# Step 6: Export a slice for testing
if [ "$EXPORT_SLICE" = true ]; then
  echo "=== Step 6: Exporting graph slice ==="
  python scripts/export_slice_with_attributes.py --lon "$LON" --lat "$LAT" --radius "$EXPORT_RADIUS" --outfile "$OUTPUT_FILE"
fi

echo "=== Setup complete! ==="
echo "OSM subset: $SUBSET_FILE"
if [ "$EXPORT_SLICE" = true ]; then
  echo "Graph slice: $OUTPUT_FILE"
fi
echo "You can now connect to the database at localhost:5432 (user: gis, password: gis)"
echo "pgAdmin is available at http://localhost:5050 (user: admin@example.com, password: admin)"
