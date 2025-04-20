#!/usr/bin/env python3
"""
Visualize the isochrone graph.
"""

import networkx as nx
import matplotlib.pyplot as plt
import sys

def main():
    if len(sys.argv) < 2:
        print("Usage: python visualize_graph.py <graphml_file>")
        sys.exit(1)
    
    graphml_file = sys.argv[1]
    print(f"Loading graph from {graphml_file}...")
    
    # Load the graph
    G = nx.read_graphml(graphml_file)
    
    print(f"Graph loaded with {len(G.nodes)} nodes and {len(G.edges)} edges")
    
    # Extract node positions
    pos = {node: (float(G.nodes[node]['x']), float(G.nodes[node]['y'])) for node in G.nodes()}
    
    # Create a figure
    plt.figure(figsize=(12, 10))
    
    # Draw the graph
    nx.draw(G, pos, 
            node_size=100, 
            node_color='blue', 
            edge_color='gray', 
            width=1.0, 
            with_labels=False,
            arrows=True)
    
    # Add node labels
    nx.draw_networkx_labels(G, pos, font_size=8, font_color='red')
    
    # Save the figure
    output_file = graphml_file.replace('.graphml', '_visualization.png')
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"Visualization saved to {output_file}")

if __name__ == "__main__":
    main()
