# Water Edge Comparison

This document compares two different methods for generating water edges from water buffers:

1. **Original Water Edges**: Edges derived directly from the high-resolution water buffers (`water_buf`)
2. **Dissolved Water Edges**: Edges derived from the dissolved water buffers (`water_buf_dissolved`)

## Implementation

The implementation consists of:

1. SQL file: `planning/sql/06_create_water_edges_comparison.sql`
   - Creates `water_edges_original` table from `water_buf`
   - Creates `water_edges_dissolved` table from `water_buf_dissolved`
   - Both without additional simplification or segmentation

2. Visualization script: `planning/scripts/visualize_water_edges_comparison.py`
   - Creates a 2x2 grid visualization comparing:
     - Original water buffers (top-left)
     - Dissolved water buffers (top-right)
     - Original water edges (bottom-left)
     - Dissolved water edges (bottom-right)
   - Saves the visualization to `output/visualizations/water/` with a timestamp

3. Runner script: `planning/scripts/run_water_edges_comparison.py`
   - Runs the SQL file to create the water edges
   - Runs the visualization script to compare the results

## Results

### Edge Count and Length

| Source | Edge Count | Total Length (km) |
|--------|------------|------------------|
| Original Water Edges | 56 | 87.59 |
| Dissolved Water Edges | 50 | 71.10 |

The dissolved water edges method produces:
- 10.7% fewer edges (56 → 50)
- 18.8% less total edge length (87.59 km → 71.10 km)

### Visual Comparison

The visualization shows:
1. **Original Water Buffers**: High-resolution buffers with detailed boundaries
2. **Dissolved Water Buffers**: Simplified buffers where adjacent water features with the same crossability are merged
3. **Original Water Edges**: More edges with complex geometry following the detailed buffer boundaries
4. **Dissolved Water Edges**: Fewer edges with simpler geometry following the dissolved buffer boundaries

## Advantages and Disadvantages

### Original Water Edges

**Advantages:**
- Preserves the detailed geometry of water features
- More accurate representation of the original water features
- Better for detailed navigation around small water features

**Disadvantages:**
- More edges to process in routing algorithms
- More complex geometry may slow down routing
- May create unnecessary detail for high-level routing

### Dissolved Water Edges

**Advantages:**
- Fewer edges to process in routing algorithms
- Simpler geometry may speed up routing
- Better for high-level routing where detailed water feature boundaries are less important
- Reduces redundant edges between adjacent water features with the same crossability

**Disadvantages:**
- Less accurate representation of the original water features
- May oversimplify complex water networks
- Could potentially merge water features that should remain separate

## Recommendation

The choice between original and dissolved water edges depends on the specific use case:

- For high-performance routing where detailed water feature boundaries are less important, the **dissolved water edges** approach is recommended.
- For detailed navigation around water features where accuracy is critical, the **original water edges** approach is recommended.

A hybrid approach could also be considered, where dissolved edges are used for high-level routing and original edges are used for detailed navigation in specific areas.

## How to Run the Comparison

To run the water edge comparison:

```bash
python planning/scripts/run_water_edges_comparison.py
```

This will:
1. Run the SQL file to create both sets of water edges
2. Generate a visualization comparing the two approaches
3. Save the visualization to `output/visualizations/water/` with a timestamp

Additional options:
```bash
python planning/scripts/run_water_edges_comparison.py --help
```
