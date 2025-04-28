#!/bin/bash
# Voronoi Test Suite Runner
# This script runs all the test phases in sequence

# Set default values
DB_NAME="postgres"
DB_USER="postgres"
DB_HOST="localhost"
DB_PORT="5432"
CONTAINER_NAME="geo-graph-db-1"
VERBOSE=false
PHASE=""

# Parse command line arguments
while [[ $# -gt 0 ]]; do
  case $1 in
    --db-name)
      DB_NAME="$2"
      shift 2
      ;;
    --db-user)
      DB_USER="$2"
      shift 2
      ;;
    --db-host)
      DB_HOST="$2"
      shift 2
      ;;
    --db-port)
      DB_PORT="$2"
      shift 2
      ;;
    --container)
      CONTAINER_NAME="$2"
      shift 2
      ;;
    --phase)
      PHASE="$2"
      shift 2
      ;;
    --verbose)
      VERBOSE=true
      shift
      ;;
    --help)
      echo "Usage: $0 [options]"
      echo "Options:"
      echo "  --db-name NAME       Database name (default: postgres)"
      echo "  --db-user USER       Database user (default: postgres)"
      echo "  --db-host HOST       Database host (default: localhost)"
      echo "  --db-port PORT       Database port (default: 5432)"
      echo "  --container NAME     Docker container name (default: geo-graph-db-1)"
      echo "  --phase PHASE        Run only a specific phase (e.g., phase1, phase2, etc.)"
      echo "  --verbose            Enable verbose output"
      echo "  --help               Show this help message"
      exit 0
      ;;
    *)
      echo "Unknown option: $1"
      echo "Use --help for usage information"
      exit 1
      ;;
  esac
done

# Function to run SQL script
run_sql_script() {
  local script_path=$1
  local script_name=$(basename "$script_path")
  
  echo "Running $script_name..."
  
  if [ "$VERBOSE" = true ]; then
    echo "Executing: $script_path"
  fi
  
  # Run the SQL script using docker exec
  if [ "$VERBOSE" = true ]; then
    docker exec -i "$CONTAINER_NAME" psql -U "$DB_USER" -d "$DB_NAME" -f - < "$script_path"
  else
    docker exec -i "$CONTAINER_NAME" psql -U "$DB_USER" -d "$DB_NAME" -f - < "$script_path" > /dev/null 2>&1
  fi
  
  # Check if the script executed successfully
  if [ $? -eq 0 ]; then
    echo "✅ $script_name completed successfully"
  else
    echo "❌ $script_name failed"
    exit 1
  fi
}

# Function to run all scripts in a directory
run_scripts_in_directory() {
  local dir_path=$1
  local dir_name=$(basename "$dir_path")
  
  echo "===== Running $dir_name ====="
  
  # Get all SQL files in the directory
  local sql_files=($(find "$dir_path" -name "*.sql" | sort))
  
  # Run each SQL file
  for sql_file in "${sql_files[@]}"; do
    run_sql_script "$sql_file"
  done
  
  echo "===== $dir_name completed ====="
  echo ""
}

# Create the results directory if it doesn't exist
mkdir -p voronoi_test/results

# Print header
echo "========================================"
echo "Voronoi Test Suite Runner"
echo "========================================"
echo "Database: $DB_NAME"
echo "User: $DB_USER"
echo "Host: $DB_HOST"
echo "Port: $DB_PORT"
echo "Container: $CONTAINER_NAME"
echo "Verbose: $VERBOSE"
if [ -n "$PHASE" ]; then
  echo "Running only phase: $PHASE"
fi
echo "========================================"
echo ""

# Setup: Create test tables and cleanup any existing data
if [ -z "$PHASE" ] || [ "$PHASE" = "setup" ]; then
  run_scripts_in_directory "voronoi_test/sql/setup"
fi

# Phase 1: Basic Tests
if [ -z "$PHASE" ] || [ "$PHASE" = "phase1" ]; then
  run_scripts_in_directory "voronoi_test/sql/phase1_basic"
fi

# Phase 2: Edge Cases
if [ -z "$PHASE" ] || [ "$PHASE" = "phase2" ]; then
  run_scripts_in_directory "voronoi_test/sql/phase2_edge_cases"
fi

# Phase 3: Boundary Cases
if [ -z "$PHASE" ] || [ "$PHASE" = "phase3" ]; then
  run_scripts_in_directory "voronoi_test/sql/phase3_boundary_cases"
fi

# Phase 4: Performance Testing
if [ -z "$PHASE" ] || [ "$PHASE" = "phase4" ]; then
  run_scripts_in_directory "voronoi_test/sql/phase4_performance"
fi

# Phase 5: Solution Testing
if [ -z "$PHASE" ] || [ "$PHASE" = "phase5" ]; then
  run_scripts_in_directory "voronoi_test/sql/phase5_solutions"
fi

# Generate summary report
echo "========================================"
echo "Generating Test Summary Report"
echo "========================================"

# Run SQL to generate summary report
docker exec -i "$CONTAINER_NAME" psql -U "$DB_USER" -d "$DB_NAME" << EOF > voronoi_test/results/summary_report.txt
-- Overall test results
SELECT 
    'Overall Test Results' AS section,
    COUNT(*) AS total_tests,
    SUM(CASE WHEN success THEN 1 ELSE 0 END) AS successful_tests,
    SUM(CASE WHEN NOT success THEN 1 ELSE 0 END) AS failed_tests,
    ROUND(SUM(CASE WHEN success THEN 1 ELSE 0 END)::NUMERIC / COUNT(*) * 100, 2) AS success_rate
FROM 
    voronoi_test_results;

-- Results by test phase
SELECT 
    'Results by Test Phase' AS section,
    p.test_phase,
    COUNT(*) AS total_tests,
    SUM(CASE WHEN r.success THEN 1 ELSE 0 END) AS successful_tests,
    SUM(CASE WHEN NOT r.success THEN 1 ELSE 0 END) AS failed_tests,
    ROUND(SUM(CASE WHEN r.success THEN 1 ELSE 0 END)::NUMERIC / COUNT(*) * 100, 2) AS success_rate
FROM 
    voronoi_test_results r
JOIN 
    voronoi_test_points p ON r.test_id = p.test_id
GROUP BY 
    p.test_phase
ORDER BY 
    p.test_phase;

-- Results by test category
SELECT 
    'Results by Test Category' AS section,
    p.test_category,
    COUNT(*) AS total_tests,
    SUM(CASE WHEN r.success THEN 1 ELSE 0 END) AS successful_tests,
    SUM(CASE WHEN NOT r.success THEN 1 ELSE 0 END) AS failed_tests,
    ROUND(SUM(CASE WHEN r.success THEN 1 ELSE 0 END)::NUMERIC / COUNT(*) * 100, 2) AS success_rate
FROM 
    voronoi_test_results r
JOIN 
    voronoi_test_points p ON r.test_id = p.test_id
GROUP BY 
    p.test_category
ORDER BY 
    p.test_category;

-- Performance metrics
SELECT 
    'Performance Metrics' AS section,
    p.test_phase,
    p.test_category,
    AVG(r.execution_time) AS avg_execution_time_ms,
    MIN(r.execution_time) AS min_execution_time_ms,
    MAX(r.execution_time) AS max_execution_time_ms
FROM 
    voronoi_test_results r
JOIN 
    voronoi_test_points p ON r.test_id = p.test_id
WHERE 
    r.success
GROUP BY 
    p.test_phase, p.test_category
ORDER BY 
    p.test_phase, p.test_category;

-- Solution effectiveness (Phase 5)
SELECT 
    'Solution Effectiveness' AS section,
    p.test_name,
    r.success,
    r.execution_time,
    CASE 
        WHEN r.success THEN 'EFFECTIVE'
        ELSE 'INEFFECTIVE'
    END AS solution_effectiveness
FROM 
    voronoi_test_results r
JOIN 
    voronoi_test_points p ON r.test_id = p.test_id
WHERE 
    p.test_phase = 'phase5_solutions'
ORDER BY 
    r.success DESC, r.execution_time ASC;

-- Failed tests with error messages
SELECT 
    'Failed Tests' AS section,
    p.test_phase,
    p.test_category,
    p.test_name,
    r.error_message
FROM 
    voronoi_test_results r
JOIN 
    voronoi_test_points p ON r.test_id = p.test_id
WHERE 
    NOT r.success
ORDER BY 
    p.test_phase, p.test_category, p.test_name;
EOF

echo "Summary report generated: voronoi_test/results/summary_report.txt"

# Print completion message
echo "========================================"
echo "Voronoi Test Suite Completed"
echo "========================================"
