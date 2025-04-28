"""
Voronoi Diagram Utilities

This module provides utility functions for generating robust Voronoi diagrams,
particularly addressing common issues with the ST_VoronoiPolygons function.
"""

import logging
import psycopg2
from psycopg2 import sql

# Set up logging
logger = logging.getLogger(__name__)

def preprocess_voronoi_points(conn, points_geom, tolerance=0.1, envelope_expansion=100, 
                             add_jitter=False, jitter_amount=0.01):
    """
    Preprocess points for Voronoi diagram generation to avoid common errors.
    
    This function applies a combined approach to preprocess points before
    generating Voronoi diagrams, addressing issues like coincident points,
    collinear points, and points on envelope boundaries.
    
    Args:
        conn: Database connection object
        points_geom: WKT or geometry object representing the input points
        tolerance: Tolerance value for ST_VoronoiPolygons (default: 0.1)
        envelope_expansion: Amount to expand the envelope by (default: 100)
        add_jitter: Whether to add small random offsets to points (default: False)
        jitter_amount: Maximum amount of jitter to add (default: 0.01)
        
    Returns:
        tuple: (preprocessed_points, envelope, tolerance)
    """
    cursor = conn.cursor()
    
    try:
        # Step 1: Convert input to geometry if it's WKT
        if isinstance(points_geom, str):
            cursor.execute(
                "SELECT ST_GeomFromText(%s)",
                (points_geom,)
            )
            points_geom = cursor.fetchone()[0]
        
        # Step 2: Remove duplicate points using ST_UnaryUnion
        logger.info("Removing duplicate points with ST_UnaryUnion")
        cursor.execute(
            "SELECT ST_UnaryUnion(%s)",
            (points_geom,)
        )
        deduped_points = cursor.fetchone()[0]
        
        # Step 3: Add jitter if requested (helps with collinear points)
        if add_jitter:
            logger.info(f"Adding random jitter (amount: {jitter_amount})")
            cursor.execute(
                sql.SQL("""
                WITH points_array AS (
                    SELECT (ST_Dump(%s)).geom AS geom
                ),
                jittered_points AS (
                    SELECT ST_Translate(
                        geom,
                        (random() - 0.5) * %s,
                        (random() - 0.5) * %s
                    ) AS geom
                    FROM points_array
                )
                SELECT ST_Collect(geom)
                FROM jittered_points
                """),
                (deduped_points, jitter_amount, jitter_amount)
            )
            preprocessed_points = cursor.fetchone()[0]
        else:
            preprocessed_points = deduped_points
        
        # Step 4: Create expanded envelope
        logger.info(f"Creating expanded envelope (expansion: {envelope_expansion})")
        cursor.execute(
            "SELECT ST_Expand(ST_Envelope(%s), %s)",
            (preprocessed_points, envelope_expansion)
        )
        envelope = cursor.fetchone()[0]
        
        # Step 5: Log preprocessing results
        cursor.execute("SELECT ST_NumGeometries(%s), ST_NumGeometries(%s)",
                      (points_geom, preprocessed_points))
        original_count, processed_count = cursor.fetchone()
        logger.info(f"Preprocessing complete: {original_count} original points -> {processed_count} preprocessed points")
        
        return preprocessed_points, envelope, tolerance
        
    except Exception as e:
        logger.error(f"Error preprocessing points for Voronoi diagram: {str(e)}")
        raise
    finally:
        cursor.close()

def generate_robust_voronoi(conn, points_geom, tolerance=0.1, envelope_expansion=100, 
                           add_jitter=False, jitter_amount=0.01):
    """
    Generate a robust Voronoi diagram that handles common edge cases.
    
    This function applies preprocessing techniques and generates a Voronoi diagram
    using ST_VoronoiPolygons, with error handling and fallback strategies.
    
    Args:
        conn: Database connection object
        points_geom: WKT or geometry object representing the input points
        tolerance: Tolerance value for ST_VoronoiPolygons (default: 0.1)
        envelope_expansion: Amount to expand the envelope by (default: 100)
        add_jitter: Whether to add small random offsets to points (default: False)
        jitter_amount: Maximum amount of jitter to add (default: 0.01)
        
    Returns:
        geometry: Voronoi diagram as a geometry object
    """
    cursor = conn.cursor()
    
    try:
        # Preprocess points
        preprocessed_points, envelope, tolerance = preprocess_voronoi_points(
            conn, points_geom, tolerance, envelope_expansion, add_jitter, jitter_amount
        )
        
        # Generate Voronoi diagram
        logger.info(f"Generating Voronoi diagram with tolerance: {tolerance}")
        cursor.execute(
            "SELECT ST_VoronoiPolygons(%s, %s, %s)",
            (preprocessed_points, tolerance, envelope)
        )
        voronoi_result = cursor.fetchone()[0]
        
        logger.info("Voronoi diagram generated successfully")
        return voronoi_result
        
    except Exception as e:
        logger.error(f"Error generating Voronoi diagram: {str(e)}")
        
        # Fallback strategy: try with increased jitter if not already using it
        if not add_jitter:
            logger.info("Attempting fallback with jitter")
            try:
                return generate_robust_voronoi(
                    conn, points_geom, tolerance, envelope_expansion, 
                    add_jitter=True, jitter_amount=jitter_amount
                )
            except Exception as e2:
                logger.error(f"Fallback with jitter failed: {str(e2)}")
        
        # Fallback strategy: try with increased tolerance
        if tolerance < 1.0:
            new_tolerance = tolerance * 10
            logger.info(f"Attempting fallback with increased tolerance: {new_tolerance}")
            try:
                return generate_robust_voronoi(
                    conn, points_geom, new_tolerance, envelope_expansion, 
                    add_jitter, jitter_amount
                )
            except Exception as e3:
                logger.error(f"Fallback with increased tolerance failed: {str(e3)}")
        
        # If all fallbacks fail, re-raise the original exception
        raise
    finally:
        cursor.close()

def create_voronoi_preprocessing_function(conn):
    """
    Create a SQL function for preprocessing points for Voronoi diagram generation.
    
    This function creates a PostgreSQL function that implements the combined
    preprocessing approach directly in the database.
    
    Args:
        conn: Database connection object
        
    Returns:
        None
    """
    cursor = conn.cursor()
    
    try:
        # Create the function
        cursor.execute("""
        CREATE OR REPLACE FUNCTION preprocess_voronoi_points(
            points geometry,
            tolerance float DEFAULT 0.1,
            envelope_expansion float DEFAULT 100,
            add_jitter boolean DEFAULT false,
            jitter_amount float DEFAULT 0.01
        )
        RETURNS TABLE(
            preprocessed_points geometry,
            envelope geometry,
            tolerance_value float
        )
        AS $$
        DECLARE
            deduped_points geometry;
            result_points geometry;
            result_envelope geometry;
        BEGIN
            -- Step 1: Remove duplicate points using ST_UnaryUnion
            deduped_points := ST_UnaryUnion(points);
            
            -- Step 2: Add jitter if requested (helps with collinear points)
            IF add_jitter THEN
                WITH points_array AS (
                    SELECT (ST_Dump(deduped_points)).geom AS geom
                ),
                jittered_points AS (
                    SELECT ST_Translate(
                        geom,
                        (random() - 0.5) * jitter_amount,
                        (random() - 0.5) * jitter_amount
                    ) AS geom
                    FROM points_array
                )
                SELECT ST_Collect(geom) INTO result_points
                FROM jittered_points;
            ELSE
                result_points := deduped_points;
            END IF;
            
            -- Step 3: Create expanded envelope
            result_envelope := ST_Expand(ST_Envelope(result_points), envelope_expansion);
            
            -- Return the results
            RETURN QUERY SELECT result_points, result_envelope, tolerance;
        END;
        $$ LANGUAGE plpgsql;
        """)
        
        # Create a wrapper function that uses the preprocessing function
        cursor.execute("""
        CREATE OR REPLACE FUNCTION generate_robust_voronoi(
            points geometry,
            tolerance float DEFAULT 0.1,
            envelope_expansion float DEFAULT 100,
            add_jitter boolean DEFAULT false,
            jitter_amount float DEFAULT 0.01
        )
        RETURNS geometry
        AS $$
        DECLARE
            prep_result record;
            voronoi_result geometry;
        BEGIN
            -- Preprocess the points
            SELECT * INTO prep_result 
            FROM preprocess_voronoi_points(
                points, tolerance, envelope_expansion, add_jitter, jitter_amount
            );
            
            -- Generate the Voronoi diagram
            voronoi_result := ST_VoronoiPolygons(
                prep_result.preprocessed_points,
                prep_result.tolerance_value,
                prep_result.envelope
            );
            
            RETURN voronoi_result;
        EXCEPTION WHEN OTHERS THEN
            -- Fallback: try with jitter if not already using it
            IF NOT add_jitter THEN
                RETURN generate_robust_voronoi(
                    points, tolerance, envelope_expansion, true, jitter_amount
                );
            -- Fallback: try with increased tolerance
            ELSIF tolerance < 1.0 THEN
                RETURN generate_robust_voronoi(
                    points, tolerance * 10, envelope_expansion, add_jitter, jitter_amount
                );
            ELSE
                -- If all fallbacks fail, re-raise the exception
                RAISE;
            END IF;
        END;
        $$ LANGUAGE plpgsql;
        """)
        
        conn.commit()
        logger.info("Created Voronoi preprocessing functions in the database")
        
    except Exception as e:
        conn.rollback()
        logger.error(f"Error creating Voronoi preprocessing functions: {str(e)}")
        raise
    finally:
        cursor.close()

def apply_voronoi_preprocessing_to_pipeline(conn, config):
    """
    Apply Voronoi preprocessing to the obstacle boundary pipeline.
    
    This function modifies the Voronoi obstacle boundary pipeline to use
    the robust Voronoi generation approach.
    
    Args:
        conn: Database connection object
        config: Pipeline configuration object
        
    Returns:
        dict: Dictionary of preprocessing parameters
    """
    # Create the preprocessing functions in the database
    create_voronoi_preprocessing_function(conn)
    
    # Extract configuration parameters from voronoi_preprocessing section
    voronoi_preprocessing = config.get('voronoi_preprocessing', {})
    tolerance = voronoi_preprocessing.get('tolerance', 0.1)
    envelope_expansion = voronoi_preprocessing.get('envelope_expansion', 100)
    add_jitter = voronoi_preprocessing.get('add_jitter', False)
    jitter_amount = voronoi_preprocessing.get('jitter_amount', 0.01)
    enable_fallback = voronoi_preprocessing.get('enable_fallback', True)
    use_combined_approach = voronoi_preprocessing.get('use_combined_approach', True)
    use_robust_voronoi = voronoi_preprocessing.get('use_robust_voronoi', True)
    max_points_per_chunk = voronoi_preprocessing.get('max_points_per_chunk', 5000)
    chunk_overlap = voronoi_preprocessing.get('chunk_overlap', 50)
    
    logger.info(f"Applying Voronoi preprocessing to pipeline with parameters:")
    logger.info(f"  tolerance: {tolerance}")
    logger.info(f"  envelope_expansion: {envelope_expansion}")
    logger.info(f"  add_jitter: {add_jitter}")
    logger.info(f"  jitter_amount: {jitter_amount}")
    logger.info(f"  enable_fallback: {enable_fallback}")
    logger.info(f"  use_combined_approach: {use_combined_approach}")
    logger.info(f"  use_robust_voronoi: {use_robust_voronoi}")
    logger.info(f"  max_points_per_chunk: {max_points_per_chunk}")
    logger.info(f"  chunk_overlap: {chunk_overlap}")
    
    # Create a function to handle chunking for large point sets
    if use_robust_voronoi:
        cursor = conn.cursor()
        try:
            cursor.execute("""
            CREATE OR REPLACE FUNCTION generate_chunked_voronoi(
                points geometry,
                max_points_per_chunk integer DEFAULT 5000,
                chunk_overlap float DEFAULT 50,
                tolerance float DEFAULT 0.1,
                envelope_expansion float DEFAULT 100,
                add_jitter boolean DEFAULT false,
                jitter_amount float DEFAULT 0.01
            )
            RETURNS geometry
            AS $$
            DECLARE
                total_points integer;
                num_chunks integer;
                chunk_size integer;
                result_voronoi geometry;
                chunk_points geometry;
                chunk_envelope geometry;
                chunk_voronoi geometry;
                i integer;
                j integer;
                point_geom geometry;
            BEGIN
                -- Get total number of points
                SELECT ST_NumGeometries(points) INTO total_points;
                
                -- If fewer points than max_points_per_chunk, just use generate_robust_voronoi
                IF total_points <= max_points_per_chunk THEN
                    RETURN generate_robust_voronoi(
                        points, tolerance, envelope_expansion, add_jitter, jitter_amount
                    );
                END IF;
                
                -- Calculate number of chunks and chunk size
                num_chunks := CEIL(total_points::float / max_points_per_chunk::float);
                chunk_size := CEIL(total_points::float / num_chunks::float);
                
                -- Initialize result
                result_voronoi := NULL;
                
                -- Process each chunk
                FOR i IN 0..(num_chunks-1) LOOP
                    -- Create a chunk of points
                    chunk_points := NULL;
                    
                    -- Add points to chunk
                    FOR j IN (i * chunk_size - chunk_overlap)..((i+1) * chunk_size + chunk_overlap) LOOP
                        IF j >= 0 AND j < total_points THEN
                            SELECT (ST_Dump(points)).geom INTO point_geom LIMIT 1 OFFSET j;
                            IF chunk_points IS NULL THEN
                                chunk_points := point_geom;
                            ELSE
                                chunk_points := ST_Union(chunk_points, point_geom);
                            END IF;
                        END IF;
                    END LOOP;
                    
                    -- Generate Voronoi for this chunk
                    chunk_voronoi := generate_robust_voronoi(
                        chunk_points, tolerance, envelope_expansion, add_jitter, jitter_amount
                    );
                    
                    -- Union with result
                    IF result_voronoi IS NULL THEN
                        result_voronoi := chunk_voronoi;
                    ELSE
                        result_voronoi := ST_Union(result_voronoi, chunk_voronoi);
                    END IF;
                END LOOP;
                
                RETURN result_voronoi;
            END;
            $$ LANGUAGE plpgsql;
            """)
            conn.commit()
            logger.info("Created chunked Voronoi generation function in the database")
        except Exception as e:
            conn.rollback()
            logger.error(f"Error creating chunked Voronoi generation function: {str(e)}")
            raise
        finally:
            cursor.close()
    
    return {
        'tolerance': tolerance,
        'envelope_expansion': envelope_expansion,
        'add_jitter': add_jitter,
        'jitter_amount': jitter_amount,
        'enable_fallback': enable_fallback,
        'use_combined_approach': use_combined_approach,
        'use_robust_voronoi': use_robust_voronoi,
        'max_points_per_chunk': max_points_per_chunk,
        'chunk_overlap': chunk_overlap
    }
