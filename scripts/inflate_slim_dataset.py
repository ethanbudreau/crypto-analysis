#!/usr/bin/env python3
"""
Dataset Inflation Script for Slim Datasets

Inflate slim datasets (txId, class only) to larger scales for GPU benchmarking.
Much faster and more space-efficient than inflating full 168-column datasets.

Usage:
    python scripts/inflate_slim_dataset.py --target 20M --base full_slim
"""

import argparse
import pandas as pd
import numpy as np
from pathlib import Path


def load_base_data(base_suffix='full_slim'):
    """Load the base slim dataset."""
    print("Loading base slim dataset...")

    nodes = pd.read_csv(f'data/processed/nodes_{base_suffix}.csv')
    edges = pd.read_csv(f'data/processed/edges_{base_suffix}.csv')

    print(f"  Base nodes: {len(nodes):,}")
    print(f"  Base edges: {len(edges):,}")

    return nodes, edges


def inflate_slim_dataset(nodes, edges, target_edges):
    """
    Inflate slim dataset to target number of edges.

    Args:
        nodes: Original nodes DataFrame (txId, class)
        edges: Original edges DataFrame (txId1, txId2)
        target_edges: Target number of edges

    Returns:
        Inflated nodes and edges DataFrames
    """
    original_edge_count = len(edges)
    original_node_count = len(nodes)

    # Calculate replication factor
    replication_factor = int(np.ceil(target_edges / original_edge_count))

    print(f"\nInflating dataset:")
    print(f"  Target edges: {target_edges:,}")
    print(f"  Replication factor: {replication_factor}x")

    # Replicate the graph multiple times with offset IDs
    inflated_nodes_list = []
    inflated_edges_list = []

    for i in range(replication_factor):
        # Offset node IDs
        node_offset = i * original_node_count

        # Copy nodes with offset IDs
        nodes_copy = nodes.copy()
        nodes_copy['txId'] = nodes_copy['txId'] + node_offset
        inflated_nodes_list.append(nodes_copy)

        # Copy edges with offset IDs
        edges_copy = edges.copy()
        edges_copy['txId1'] = edges_copy['txId1'] + node_offset
        edges_copy['txId2'] = edges_copy['txId2'] + node_offset
        inflated_edges_list.append(edges_copy)

        if (i + 1) % 10 == 0 or i + 1 == replication_factor:
            print(f"  Created copy {i+1}/{replication_factor}")

    # Combine all copies
    print("  Concatenating copies...")
    inflated_nodes = pd.concat(inflated_nodes_list, ignore_index=True)
    inflated_edges = pd.concat(inflated_edges_list, ignore_index=True)

    # Add cross-replica edges (10% of target)
    print("  Adding cross-replica edges...")
    num_cross_edges = min(int(target_edges * 0.1), original_edge_count)
    cross_edges = []

    for _ in range(num_cross_edges):
        # Random edge between different replicas
        replica1 = np.random.randint(0, replication_factor)
        replica2 = np.random.randint(0, replication_factor)
        if replica1 != replica2:
            offset1 = replica1 * original_node_count
            offset2 = replica2 * original_node_count

            # Pick random nodes from each replica
            node1 = np.random.randint(0, original_node_count) + offset1
            node2 = np.random.randint(0, original_node_count) + offset2

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

    print(f"\nInflated dataset:")
    print(f"  Final nodes: {len(inflated_nodes):,}")
    print(f"  Final edges: {len(inflated_edges):,}")
    print(f"  Inflation ratio: {len(inflated_edges)/original_edge_count:.1f}x")

    return inflated_nodes, inflated_edges


def save_inflated_data(nodes, edges, suffix):
    """Save inflated slim dataset."""
    output_dir = Path('data/processed')
    output_dir.mkdir(exist_ok=True, parents=True)

    nodes_file = output_dir / f'nodes_{suffix}.csv'
    edges_file = output_dir / f'edges_{suffix}.csv'

    print(f"\nSaving inflated dataset...")
    nodes.to_csv(nodes_file, index=False)
    edges.to_csv(edges_file, index=False)

    # Show file sizes
    nodes_size_mb = nodes_file.stat().st_size / (1024 ** 2)
    edges_size_mb = edges_file.stat().st_size / (1024 ** 2)

    print(f"  Nodes: {nodes_file} ({nodes_size_mb:.1f} MB)")
    print(f"  Edges: {edges_file} ({edges_size_mb:.1f} MB)")
    print(f"  Total: {nodes_size_mb + edges_size_mb:.1f} MB")
    print(f"✓ Saved slim dataset as '{suffix}'")


def main():
    parser = argparse.ArgumentParser(description='Inflate slim dataset for GPU benchmarking')
    parser.add_argument('--target', required=True,
                        help='Target edge count (e.g., 10M, 20M, 50M)')
    parser.add_argument('--base', default='full_slim',
                        help='Base dataset suffix (default: full_slim)')
    parser.add_argument('--output-suffix',
                        help='Output file suffix (default: based on target)')

    args = parser.parse_args()

    # Parse target size
    target_str = args.target.upper()
    if target_str.endswith('M'):
        target_edges = int(float(target_str[:-1]) * 1_000_000)
    elif target_str.endswith('K'):
        target_edges = int(float(target_str[:-1]) * 1_000)
    else:
        target_edges = int(target_str)

    # Default suffix based on target
    if args.output_suffix:
        suffix = args.output_suffix
    else:
        if target_edges >= 1_000_000:
            suffix = f"{target_edges // 1_000_000}m"
        else:
            suffix = f"{target_edges // 1_000}k"

    print("=" * 60)
    print("SLIM DATASET INFLATION")
    print("=" * 60)
    print(f"Target: {target_edges:,} edges")
    print(f"Base: {args.base}")
    print(f"Output suffix: {suffix}")
    print("=" * 60)

    # Load base data
    nodes, edges = load_base_data(args.base)

    # Check if target is reasonable
    if target_edges < len(edges):
        print(f"\n⚠ Warning: Target ({target_edges:,}) is smaller than base ({len(edges):,})")
        print(f"Use --base full_slim or a smaller base dataset instead.")
        return

    # Inflate dataset
    inflated_nodes, inflated_edges = inflate_slim_dataset(
        nodes, edges, target_edges
    )

    # Save inflated data
    save_inflated_data(inflated_nodes, inflated_edges, suffix)

    print("\n" + "=" * 60)
    print("INFLATION COMPLETE")
    print("=" * 60)
    print("\nTo benchmark this dataset:")
    print(f"  python scripts/02_run_benchmarks.py --db both --sizes {suffix} --queries 1_hop")
    print("\nNote: This is a slim dataset (txId, class only) for efficient testing.")
    print("Results are computationally valid but use optimized storage.")


if __name__ == "__main__":
    main()
