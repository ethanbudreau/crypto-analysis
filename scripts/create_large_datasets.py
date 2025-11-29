#!/usr/bin/env python3
"""
Create Large Datasets (50M, 100M edges)
Inflates the existing 100k base dataset to create very large test datasets.

Usage:
    python scripts/create_large_datasets.py
"""

import pandas as pd
import numpy as np
from pathlib import Path


def inflate_dataset(nodes, edges, target_edges, suffix):
    """
    Inflate dataset to target number of edges.

    Args:
        nodes: Original nodes DataFrame (txId, class)
        edges: Original edges DataFrame (txId1, txId2)
        target_edges: Target number of edges
        suffix: Output file suffix
    """
    original_edge_count = len(edges)
    original_node_count = len(nodes)

    # Calculate replication factor
    replication_factor = int(np.ceil(target_edges / original_edge_count))

    print(f"\nInflating to {target_edges:,} edges ({suffix}):")
    print(f"  Replication factor: {replication_factor}x")

    # Replicate the graph multiple times with offset IDs
    inflated_nodes_list = []
    inflated_edges_list = []

    for i in range(replication_factor):
        # Offset node IDs
        node_offset = i * original_node_count * 10  # Large offset to avoid collisions

        # Copy nodes with offset IDs
        nodes_copy = nodes.copy()
        nodes_copy['txId'] = nodes_copy['txId'] + node_offset
        inflated_nodes_list.append(nodes_copy)

        # Copy edges with offset IDs
        edges_copy = edges.copy()
        edges_copy['txId1'] = edges_copy['txId1'] + node_offset
        edges_copy['txId2'] = edges_copy['txId2'] + node_offset
        inflated_edges_list.append(edges_copy)

        if (i + 1) % 50 == 0 or i + 1 == replication_factor:
            print(f"  Created copy {i+1}/{replication_factor}")

    # Combine all copies
    print("  Concatenating copies...")
    inflated_nodes = pd.concat(inflated_nodes_list, ignore_index=True)
    inflated_edges = pd.concat(inflated_edges_list, ignore_index=True)

    # Add cross-replica edges (10% of target)
    print("  Adding cross-replica edges...")
    num_cross_edges = min(int(target_edges * 0.1), original_edge_count)
    cross_edges = []

    np.random.seed(42)
    for _ in range(num_cross_edges):
        # Random edge between different replicas
        replica1 = np.random.randint(0, replication_factor)
        replica2 = np.random.randint(0, replication_factor)
        if replica1 != replica2:
            offset1 = replica1 * original_node_count * 10
            offset2 = replica2 * original_node_count * 10

            # Pick random nodes from each replica
            node1 = nodes['txId'].iloc[np.random.randint(0, original_node_count)] + offset1
            node2 = nodes['txId'].iloc[np.random.randint(0, original_node_count)] + offset2

            cross_edges.append({
                'txId1': node1,
                'txId2': node2
            })

    if cross_edges:
        cross_edges_df = pd.DataFrame(cross_edges)
        inflated_edges = pd.concat([inflated_edges, cross_edges_df], ignore_index=True)
        print(f"  Added {len(cross_edges):,} cross-replica edges")

    # Trim to exact target size
    if len(inflated_edges) > target_edges:
        print("  Trimming to target size...")
        inflated_edges = inflated_edges.sample(n=target_edges, random_state=42).reset_index(drop=True)

    print(f"  ✓ Final: {len(inflated_nodes):,} nodes, {len(inflated_edges):,} edges")

    return inflated_nodes, inflated_edges


def save_dataset(nodes, edges, suffix):
    """Save dataset to CSV files."""
    nodes_file = f"data/processed/nodes_{suffix}.csv"
    edges_file = f"data/processed/edges_{suffix}.csv"

    nodes.to_csv(nodes_file, index=False)
    edges.to_csv(edges_file, index=False)

    # Show file sizes
    nodes_size_mb = Path(nodes_file).stat().st_size / (1024 ** 2)
    edges_size_mb = Path(edges_file).stat().st_size / (1024 ** 2)

    print(f"  ✓ Saved: {suffix} ({nodes_size_mb + edges_size_mb:.1f} MB)")


def main():
    """Main execution function."""
    print("="*50)
    print("CREATE LARGE DATASETS (50M, 100M)")
    print("="*50)
    print("\nLoading base 100k dataset...")

    # Load existing 100k dataset
    base_nodes = pd.read_csv("data/processed/nodes_100k.csv")
    base_edges = pd.read_csv("data/processed/edges_100k.csv")

    print(f"✓ Loaded base dataset: {len(base_nodes):,} nodes, {len(base_edges):,} edges")

    # Create larger datasets
    for target_edges, suffix in [
        (50_000_000, "50m"),
        (100_000_000, "100m"),
    ]:
        inflated_nodes, inflated_edges = inflate_dataset(
            base_nodes, base_edges, target_edges, suffix
        )
        save_dataset(inflated_nodes, inflated_edges, suffix)

    print("\n" + "="*50)
    print("LARGE DATASETS CREATED")
    print("="*50)
    print("\nCreated datasets:")
    print("  - 50m:  50,000,000 edges")
    print("  - 100m: 100,000,000 edges")


if __name__ == "__main__":
    main()
