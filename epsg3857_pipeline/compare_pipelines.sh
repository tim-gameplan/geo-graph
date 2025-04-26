#!/bin/bash
# Script to run both the standard and obstacle boundary pipelines for comparison

# Set up colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Parse command line arguments
VERBOSE=""
SKIP_RESET=false
EXPORT_SLICE=false
VISUALIZE=false
COORDINATES="-93.63 41.99"
TRAVEL_TIME=60

while [[ $# -gt 0 ]]; do
  case $1 in
    --verbose)
      VERBOSE="--verbose"
      shift
      ;;
    --skip-reset)
      SKIP_RESET=true
      shift
      ;;
    --export-slice)
      EXPORT_SLICE=true
      shift
      ;;
    --visualize)
      VISUALIZE=true
      shift
      ;;
    --coordinates)
      COORDINATES="$2"
      shift
      shift
      ;;
    --travel-time)
      TRAVEL_TIME="$2"
      shift
      shift
      ;;
    *)
      echo "Unknown option: $1"
      echo "Usage: $0 [--verbose] [--skip-reset] [--export-slice] [--visualize] [--coordinates \"lon lat\"] [--travel-time minutes]"
      exit 1
      ;;
  esac
done

# Extract longitude and latitude from coordinates
LON=$(echo $COORDINATES | cut -d' ' -f1)
LAT=$(echo $COORDINATES | cut -d' ' -f2)

# Function to display section header
section() {
  echo -e "\n${BLUE}=== $1 ===${NC}\n"
}

# Reset the database if not skipped
if [ "$SKIP_RESET" = false ]; then
  section "Resetting Database"
  python epsg3857_pipeline/tools/database/reset_non_osm_tables.py
  if [ $? -ne 0 ]; then
    echo -e "${RED}Failed to reset database${NC}"
    exit 1
  fi
fi

# Run the standard pipeline
section "Running Standard EPSG:3857 Pipeline"
STANDARD_CMD="python epsg3857_pipeline/run_epsg3857_pipeline.py --mode standard"
if [ "$SKIP_RESET" = true ]; then
  STANDARD_CMD="$STANDARD_CMD --skip-reset"
fi
if [ ! -z "$VERBOSE" ]; then
  STANDARD_CMD="$STANDARD_CMD $VERBOSE"
fi
echo -e "${YELLOW}Executing: $STANDARD_CMD${NC}"
eval $STANDARD_CMD
if [ $? -ne 0 ]; then
  echo -e "${RED}Standard pipeline failed${NC}"
  exit 1
fi
echo -e "${GREEN}Standard pipeline completed successfully${NC}"

# Export standard graph slice if requested
if [ "$EXPORT_SLICE" = true ]; then
  section "Exporting Standard Graph Slice"
  EXPORT_CMD="python epsg3857_pipeline/core/scripts/export_slice.py --lon $LON --lat $LAT --minutes $TRAVEL_TIME --outfile standard_graph_slice.graphml"
  echo -e "${YELLOW}Executing: $EXPORT_CMD${NC}"
  eval $EXPORT_CMD
  if [ $? -ne 0 ]; then
    echo -e "${RED}Failed to export standard graph slice${NC}"
  else
    echo -e "${GREEN}Standard graph slice exported successfully${NC}"
  fi
fi

# Visualize standard graph if requested
if [ "$VISUALIZE" = true ]; then
  section "Visualizing Standard Graph"
  VIZ_CMD="python epsg3857_pipeline/core/scripts/visualize.py --mode water --output standard_water_obstacles.png"
  echo -e "${YELLOW}Executing: $VIZ_CMD${NC}"
  eval $VIZ_CMD
  if [ $? -ne 0 ]; then
    echo -e "${RED}Failed to visualize standard graph${NC}"
  else
    echo -e "${GREEN}Standard graph visualization created successfully${NC}"
  fi
fi

# Run the obstacle boundary pipeline
section "Running Obstacle Boundary Pipeline"
OBSTACLE_CMD="python epsg3857_pipeline/run_obstacle_boundary_pipeline.py"
if [ ! -z "$VERBOSE" ]; then
  OBSTACLE_CMD="$OBSTACLE_CMD $VERBOSE"
fi
echo -e "${YELLOW}Executing: $OBSTACLE_CMD${NC}"
eval $OBSTACLE_CMD
if [ $? -ne 0 ]; then
  echo -e "${RED}Obstacle boundary pipeline failed${NC}"
  exit 1
fi
echo -e "${GREEN}Obstacle boundary pipeline completed successfully${NC}"

# Visualize obstacle boundary graph
if [ "$VISUALIZE" = true ]; then
  section "Visualizing Obstacle Boundary Graph"
  VIZ_CMD="python epsg3857_pipeline/core/obstacle_boundary/visualize.py --output obstacle_boundary_graph.png"
  echo -e "${YELLOW}Executing: $VIZ_CMD${NC}"
  eval $VIZ_CMD
  if [ $? -ne 0 ]; then
    echo -e "${RED}Failed to visualize obstacle boundary graph${NC}"
  else
    echo -e "${GREEN}Obstacle boundary graph visualization created successfully${NC}"
  fi
fi

# Export obstacle boundary graph slice if requested
if [ "$EXPORT_SLICE" = true ]; then
  section "Exporting Obstacle Boundary Graph Slice"
  EXPORT_CMD="python epsg3857_pipeline/core/scripts/export_slice.py --lon $LON --lat $LAT --minutes $TRAVEL_TIME --outfile obstacle_boundary_graph_slice.graphml"
  echo -e "${YELLOW}Executing: $EXPORT_CMD${NC}"
  eval $EXPORT_CMD
  if [ $? -ne 0 ]; then
    echo -e "${RED}Failed to export obstacle boundary graph slice${NC}"
  else
    echo -e "${GREEN}Obstacle boundary graph slice exported successfully${NC}"
  fi
fi

section "Pipeline Comparison Complete"
echo -e "Standard pipeline results:"
echo -e "  - Graph slice: standard_graph_slice.graphml (if exported)"
echo -e "  - Visualization: standard_water_obstacles.png (if visualized)"
echo -e ""
echo -e "Obstacle boundary pipeline results:"
echo -e "  - Graph slice: obstacle_boundary_graph_slice.graphml (if exported)"
echo -e "  - Visualization: obstacle_boundary_graph.png (if visualized)"
echo -e ""
echo -e "${GREEN}Both pipelines completed successfully. You can now compare the results.${NC}"
