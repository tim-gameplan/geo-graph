# Voronoi Diagram Test Suite

This test suite is designed to systematically test PostGIS's `ST_VoronoiPolygons` function, identify common issues, and develop robust solutions for handling edge cases. The suite focuses particularly on addressing the "Invalid number of points in LinearRing found 2 - must be 0 or >= 4" error that can occur with certain input geometries.

## Test Suite Structure

The test suite is organized into multiple phases, each focusing on different aspects of Voronoi diagram generation:

### Phase 1: Basic Tests
- Tests with simple, well-behaved point sets
- Verifies basic functionality of `ST_VoronoiPolygons`
- Establishes baseline performance metrics

### Phase 2: Edge Cases
- Tests with problematic point configurations:
  - Collinear points
  - Coincident points
  - Nearly coincident points
  - Single points

### Phase 3: Boundary Cases
- Tests with points on or near the envelope boundary
- Tests with different envelope configurations
- Tests with points outside the envelope

### Phase 4: Performance Testing
- Tests with varying numbers of points to measure scaling behavior
- Tests with different spatial distributions
- Identifies performance bottlenecks

### Phase 5: Solution Testing
- Tests various preprocessing techniques to solve common issues:
  - Deduplication of coincident points
  - Adding small random offsets to break collinearity
  - Using non-zero tolerance values
  - Expanding the envelope
  - Combined approaches

## Directory Structure

```
voronoi_test/
├── README.md                 # This documentation file
├── run_tests.sh              # Main test runner script
├── results/                  # Directory for test results and reports
├── connection_strategies/    # Tests for different connection strategies
│   ├── README.md                   # Documentation for connection strategies
│   ├── run_voronoi_test.sh         # Script to run connection strategy tests
│   ├── voronoi_connection_test.sql # SQL tests for connection strategies
│   └── run_voronoi_connection_test.py # Python script to visualize results
└── sql/
    ├── setup/                # Setup scripts
    │   ├── create_test_tables.sql  # Creates test tables
    │   └── cleanup.sql             # Cleans up test data
    ├── phase1_basic/         # Basic test scripts
    │   └── test_simple_points.sql  # Tests with simple point sets
    ├── phase2_edge_cases/    # Edge case test scripts
    │   ├── test_collinear.sql      # Tests with collinear points
    │   └── test_coincident.sql     # Tests with coincident points
    ├── phase3_boundary_cases/ # Boundary case test scripts
    │   └── test_envelope.sql       # Tests with different envelopes
    ├── phase4_performance/   # Performance test scripts
    │   └── test_scaling.sql        # Tests with varying point counts
    └── phase5_solutions/     # Solution test scripts
        └── test_preprocessing.sql  # Tests preprocessing techniques
```

## Database Schema

The test suite uses the following tables:

### `voronoi_test_points`
Stores test point sets and metadata:
- `test_id`: Unique identifier for the test
- `test_name`: Name of the test
- `test_description`: Description of the test
- `test_phase`: Test phase (e.g., 'phase1_basic')
- `test_category`: Test category (e.g., 'collinear')
- `point_count`: Number of points in the test
- `points`: Geometry collection of points

### `voronoi_test_results`
Stores test results:
- `result_id`: Unique identifier for the result
- `test_id`: Reference to the test
- `test_type`: Type of test (e.g., 'baseline', 'preprocessing')
- `success`: Whether the test succeeded
- `error_message`: Error message if the test failed
- `execution_time`: Execution time in milliseconds
- `voronoi_diagram`: Resulting Voronoi diagram geometry

### `voronoi_test_preprocessing`
Stores preprocessing information:
- `preprocessing_id`: Unique identifier
- `result_id`: Reference to the test result
- `preprocessing_type`: Type of preprocessing (e.g., 'deduplication')
- `description`: Description of the preprocessing technique

### `voronoi_test_parameters`
Stores test parameters:
- `param_id`: Unique identifier
- `result_id`: Reference to the test result
- `param_name`: Parameter name (e.g., 'tolerance')
- `param_value`: Parameter value

## Running the Tests

The test suite can be run using the `run_tests.sh` script:

```bash
# Run all tests
./run_tests.sh

# Run with verbose output
./run_tests.sh --verbose

# Run only a specific phase
./run_tests.sh --phase phase1

# Run with a specific database
./run_tests.sh --db-name mydb --db-user myuser

# Show help
./run_tests.sh --help
```

## Test Results

After running the tests, a summary report is generated in the `results/` directory. The report includes:

- Overall test results
- Results by test phase
- Results by test category
- Performance metrics
- Solution effectiveness
- Failed tests with error messages

## Common Issues and Solutions

### 1. Coincident Points

**Issue**: `ST_VoronoiPolygons` can fail when input contains duplicate points.

**Solution**: Use `ST_UnaryUnion` to remove duplicate points:
```sql
preprocessed_points := ST_UnaryUnion(problematic_points);
```

### 2. Collinear Points

**Issue**: Collinear points can cause the "Invalid number of points in LinearRing" error.

**Solution**: Add small random offsets to break collinearity:
```sql
WITH points_array AS (
    SELECT (ST_Dump(problematic_points)).geom AS geom
),
jittered_points AS (
    SELECT ST_Translate(
        geom,
        (random() - 0.5) * 0.01,
        (random() - 0.5) * 0.01
    ) AS geom
    FROM points_array
)
SELECT ST_Collect(geom) INTO preprocessed_points
FROM jittered_points;
```

### 3. Points on Envelope Boundary

**Issue**: Points on the envelope boundary can cause issues.

**Solution**: Expand the envelope:
```sql
envelope := ST_Expand(envelope, 100);
```

### 4. Combined Approach

For maximum robustness, combine multiple techniques:
```sql
-- 1. Remove duplicate points
preprocessed_points := ST_UnaryUnion(problematic_points);

-- 2. Use a non-zero tolerance
tolerance := 0.1;

-- 3. Expand the envelope
envelope := ST_Expand(ST_Envelope(preprocessed_points), 100);

-- 4. Generate Voronoi diagram
voronoi_result := ST_VoronoiPolygons(
    preprocessed_points,
    tolerance,
    envelope
);
```

## Best Practices

1. **Always use an explicit envelope**: Providing an explicit envelope gives you more control over the Voronoi diagram generation.

2. **Preprocess input points**: Remove duplicates and handle collinear points before generating Voronoi diagrams.

3. **Use a small non-zero tolerance**: A small tolerance value (e.g., 0.1) can help avoid numerical precision issues.

4. **Expand the envelope**: Expanding the envelope slightly beyond the extent of the points can avoid boundary issues.

5. **Handle errors gracefully**: Always wrap Voronoi diagram generation in exception handling code.

## Contributing

To add new tests to the suite:

1. Create a new SQL file in the appropriate phase directory
2. Follow the existing test pattern
3. Update this README if necessary

## License

This test suite is released under the same license as the main project.
