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
RUN_WATER_BOUNDARY=true
RUN_OBSTACLE_BOUNDARY=true
RUN_BOUNDARY_HEXAGON=true
RUN_VORONOI=true

while [[ $# -gt 0 ]]; do
  case $1 in
    --standard-only)
      RUN_STANDARD=true
      RUN_DELAUNAY=false
      RUN_WATER_BOUNDARY=false
      RUN_OBSTACLE_BOUNDARY=false
      RUN_BOUNDARY_HEXAGON=false
      shift
      ;;
    --delaunay-only)
      RUN_STANDARD=false
      RUN_DELAUNAY=true
      RUN_WATER_BOUNDARY=false
      RUN_OBSTACLE_BOUNDARY=false
      RUN_BOUNDARY_HEXAGON=false
      shift
      ;;
    --water-boundary-only)
      RUN_STANDARD=false
      RUN_DELAUNAY=false
      RUN_WATER_BOUNDARY=true
      RUN_OBSTACLE_BOUNDARY=false
      RUN_BOUNDARY_HEXAGON=false
      shift
      ;;
    --obstacle-boundary-only)
      RUN_STANDARD=false
      RUN_DELAUNAY=false
      RUN_WATER_BOUNDARY=false
      RUN_OBSTACLE_BOUNDARY=true
      RUN_BOUNDARY_HEXAGON=false
      shift
      ;;
    --boundary-hexagon-only)
      RUN_STANDARD=false
      RUN_DELAUNAY=false
      RUN_WATER_BOUNDARY=false
      RUN_OBSTACLE_BOUNDARY=false
      RUN_BOUNDARY_HEXAGON=true
      RUN_VORONOI=false
      shift
      ;;
    --hexagon-obstacle-only)
      RUN_STANDARD=false
      RUN_DELAUNAY=false
      RUN_WATER_BOUNDARY=false
      RUN_OBSTACLE_BOUNDARY=false
      RUN_BOUNDARY_HEXAGON=false
      RUN_VORONOI=false
      # We'll run the hexagon obstacle test directly
      echo -e "${YELLOW}Running Hexagon Obstacle Boundary tests...${NC}"
      python core/tests/test_hexagon_obstacle_boundary.py $VERBOSE
      
      if [ $? -eq 0 ]; then
          echo -e "${GREEN}Hexagon Obstacle Boundary tests passed!${NC}"
          exit 0
      else
          echo -e "${RED}Hexagon Obstacle Boundary tests failed!${NC}"
          exit 1
      fi
      ;;
    --voronoi-obstacle-only)
      RUN_STANDARD=false
      RUN_DELAUNAY=false
      RUN_WATER_BOUNDARY=false
      RUN_OBSTACLE_BOUNDARY=false
      RUN_BOUNDARY_HEXAGON=false
      RUN_VORONOI=false
      # We'll run the voronoi obstacle test directly
      echo -e "${YELLOW}Running Voronoi Obstacle Boundary tests...${NC}"
      python core/tests/test_voronoi_obstacle_boundary.py $VERBOSE
      
      if [ $? -eq 0 ]; then
          echo -e "${GREEN}Voronoi Obstacle Boundary tests passed!${NC}"
          exit 0
      else
          echo -e "${RED}Voronoi Obstacle Boundary tests failed!${NC}"
          exit 1
      fi
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
    python core/tests/test_epsg3857_pipeline.py $VERBOSE
    
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
    python core/tests/test_delaunay_pipeline.py $VERBOSE
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}Delaunay triangulation tests passed!${NC}"
    else
        echo -e "${RED}Delaunay triangulation tests failed!${NC}"
        EXIT_CODE=1
    fi
fi

# Run Water Boundary Approach tests
if [ "$RUN_WATER_BOUNDARY" = true ]; then
    echo -e "${YELLOW}Running Water Boundary Approach tests...${NC}"
    python core/tests/test_water_boundary_approach.py $VERBOSE
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}Water Boundary Approach tests passed!${NC}"
    else
        echo -e "${RED}Water Boundary Approach tests failed!${NC}"
        EXIT_CODE=1
    fi
fi

# Run Direct Water Obstacle Boundary Conversion tests
if [ "$RUN_OBSTACLE_BOUNDARY" = true ]; then
    echo -e "${YELLOW}Running Direct Water Obstacle Boundary Conversion tests...${NC}"
    python core/tests/test_obstacle_boundary_graph.py $VERBOSE
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}Direct Water Obstacle Boundary Conversion tests passed!${NC}"
    else
        echo -e "${RED}Direct Water Obstacle Boundary Conversion tests failed!${NC}"
        EXIT_CODE=1
    fi
fi

# Run Boundary Hexagon Layer tests
if [ "$RUN_BOUNDARY_HEXAGON" = true ]; then
    echo -e "${YELLOW}Running Boundary Hexagon Layer tests...${NC}"
    python core/tests/test_boundary_hexagon_layer.py $VERBOSE
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}Boundary Hexagon Layer tests passed!${NC}"
    else
        echo -e "${RED}Boundary Hexagon Layer tests failed!${NC}"
        EXIT_CODE=1
    fi
    
    echo -e "${YELLOW}Running Hexagon Obstacle Boundary tests...${NC}"
    python core/tests/test_hexagon_obstacle_boundary.py $VERBOSE
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}Hexagon Obstacle Boundary tests passed!${NC}"
    else
        echo -e "${RED}Hexagon Obstacle Boundary tests failed!${NC}"
        EXIT_CODE=1
    fi
fi

# Run Voronoi Obstacle Boundary tests
if [ "$RUN_VORONOI" = true ]; then
    echo -e "${YELLOW}Running Voronoi Obstacle Boundary tests...${NC}"
    python core/tests/test_voronoi_obstacle_boundary.py $VERBOSE
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}Voronoi Obstacle Boundary tests passed!${NC}"
    else
        echo -e "${RED}Voronoi Obstacle Boundary tests failed!${NC}"
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
