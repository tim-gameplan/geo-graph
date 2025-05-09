# Table Naming Code Reference Updates

This document outlines the approach for updating code references to use the new table names after implementing the Pipeline Stage Prefixing naming convention.

## Overview

After implementing the Pipeline Stage Prefixing naming convention, all code that references the old table names will need to be updated to use the new table names. This includes:

1. Python scripts
2. SQL scripts
3. Visualization code
4. Documentation
5. Tests

While the backward compatibility views will allow existing code to continue working with the old table names, it's best practice to update all code references to use the new table names directly. This will improve code clarity and maintainability, and reduce the dependency on the backward compatibility views.

## Identification of Code References

The first step is to identify all code that references the old table names. This can be done using the following approaches:

### 1. Grep for Table Names

Use `grep` or similar tools to search for references to the old table names in all code files:

```bash
grep -r "water_features_polygon" --include="*.py" --include="*.sql" .
grep -r "water_buffers" --include="*.py" --include="*.sql" .
grep -r "dissolved_water_buffers" --include="*.py" --include="*.sql" .
# ... and so on for all old table names
```

### 2. Database Query Analysis

Analyze database queries in the code to identify references to the old table names:

```python
# Example of a database query using the old table name
cursor.execute("SELECT * FROM water_features_polygon WHERE id = %s", (id,))
```

### 3. Code Review

Perform a manual code review to identify references to the old table names that might be missed by automated tools, such as:

- Dynamic SQL generation
- String concatenation
- Variable names that reference table names

## Update Approach

Once all code references have been identified, they can be updated using the following approach:

### 1. Create a Mapping File

Create a mapping file that maps old table names to new table names:

```python
TABLE_NAME_MAPPING = {
    "water_features_polygon": "s01_water_features_polygon",
    "water_features_line": "s01_water_features_line",
    "water_features": "s01_water_features_view",
    "water_buffers": "s02_water_buffers",
    "dissolved_water_buffers": "s03_water_buffers_dissolved",
    "water_obstacles": "s03_water_obstacles",
    # ... and so on for all table names
}
```

### 2. Update Python Code

Update Python code to use the new table names:

```python
# Old code
cursor.execute("SELECT * FROM water_features_polygon WHERE id = %s", (id,))

# New code
cursor.execute("SELECT * FROM s01_water_features_polygon WHERE id = %s", (id,))
```

For dynamic SQL generation, use the mapping file:

```python
# Old code
table_name = "water_features_polygon"
cursor.execute(f"SELECT * FROM {table_name} WHERE id = %s", (id,))

# New code
table_name = "water_features_polygon"
new_table_name = TABLE_NAME_MAPPING.get(table_name, table_name)
cursor.execute(f"SELECT * FROM {new_table_name} WHERE id = %s", (id,))
```

### 3. Update SQL Scripts

Update SQL scripts to use the new table names:

```sql
-- Old code
SELECT * FROM water_features_polygon WHERE id = 1;

-- New code
SELECT * FROM s01_water_features_polygon WHERE id = 1;
```

### 4. Update Visualization Code

Update visualization code to use the new table names:

```python
# Old code
def visualize_water_features():
    cursor.execute("SELECT geom FROM water_features_polygon")
    # ... visualization code

# New code
def visualize_water_features():
    cursor.execute("SELECT geom FROM s01_water_features_polygon")
    # ... visualization code
```

### 5. Update Documentation

Update documentation to use the new table names:

```markdown
<!-- Old documentation -->
The `water_features_polygon` table contains water feature polygons extracted from OSM data.

<!-- New documentation -->
The `s01_water_features_polygon` table contains water feature polygons extracted from OSM data.
```

### 6. Update Tests

Update tests to use the new table names:

```python
# Old code
def test_water_features():
    cursor.execute("SELECT COUNT(*) FROM water_features_polygon")
    # ... test code

# New code
def test_water_features():
    cursor.execute("SELECT COUNT(*) FROM s01_water_features_polygon")
    # ... test code
```

## Testing

After updating code references, thorough testing is required to ensure that the updated code works correctly:

1. Run unit tests to verify that individual components work correctly
2. Run integration tests to verify that the entire system works correctly
3. Run end-to-end tests to verify that the system works correctly from a user's perspective
4. Manually test key functionality to verify that it works as expected

## Phased Approach

Given the scope of the changes, a phased approach is recommended:

### Phase 1: Core Pipeline Code

Update the core pipeline code to use the new table names:

1. Pipeline runner scripts
2. SQL scripts
3. Core utility functions

### Phase 2: Visualization and Analysis Code

Update visualization and analysis code to use the new table names:

1. Visualization scripts
2. Analysis scripts
3. Reporting scripts

### Phase 3: Tests and Documentation

Update tests and documentation to use the new table names:

1. Unit tests
2. Integration tests
3. Documentation
4. Examples

### Phase 4: Auxiliary Code

Update auxiliary code to use the new table names:

1. Helper scripts
2. Debugging tools
3. Monitoring scripts

## Backward Compatibility Considerations

While updating code references, it's important to maintain backward compatibility:

1. Keep the backward compatibility views in place until all code has been updated
2. Test both the old and new code to ensure that they work correctly
3. Consider using feature flags to switch between the old and new table names

## Conclusion

Updating code references to use the new table names is an important step in implementing the Pipeline Stage Prefixing naming convention. By following a systematic approach, all code references can be updated correctly and efficiently, while maintaining backward compatibility.