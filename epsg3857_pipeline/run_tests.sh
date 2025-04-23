#!/bin/bash
# Run all tests for the EPSG:3857 pipeline

# Set up environment
export PYTHONPATH=$PYTHONPATH:$(pwd)

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[0;33m'
NC='\033[0m' # No Color

# Parse command line arguments
RUN_STANDARD=true
RUN_DELAUNAY=true

while [[ $# -gt 0 ]]; do
  case $1 in
    --standard-only)
      RUN_STANDARD=true
      RUN_DELAUNAY=false
      shift
      ;;
    --delaunay-only)
      RUN_STANDARD=false
      RUN_DELAUNAY=true
      shift
      ;;
    --verbose)
      VERBOSE="--verbose"
      shift
      ;;
    *)
      echo "Unknown option: $1"
      exit 1
      ;;
  esac
done

# Initialize exit code
EXIT_CODE=0

# Run standard EPSG:3857 pipeline tests
if [ "$RUN_STANDARD" = true ]; then
    echo -e "${YELLOW}Running standard EPSG:3857 pipeline tests...${NC}"
    python epsg3857_pipeline/tests/test_epsg3857_pipeline.py $VERBOSE
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}Standard EPSG:3857 pipeline tests passed!${NC}"
    else
        echo -e "${RED}Standard EPSG:3857 pipeline tests failed!${NC}"
        EXIT_CODE=1
    fi
fi

# Run Delaunay triangulation tests
if [ "$RUN_DELAUNAY" = true ]; then
    echo -e "${YELLOW}Running Delaunay triangulation tests...${NC}"
    python epsg3857_pipeline/tests/test_delaunay_pipeline.py $VERBOSE
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}Delaunay triangulation tests passed!${NC}"
    else
        echo -e "${RED}Delaunay triangulation tests failed!${NC}"
        EXIT_CODE=1
    fi
fi

# Final result
if [ $EXIT_CODE -eq 0 ]; then
    echo -e "${GREEN}All tests passed!${NC}"
else
    echo -e "${RED}Some tests failed!${NC}"
fi

exit $EXIT_CODE
