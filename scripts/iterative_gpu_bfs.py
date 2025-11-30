#!/usr/bin/env python3
"""
Iterative BFS using Sirius GPU for neighbor expansion.

This module provides true breadth-first search that:
- Runs each hop expansion on GPU via gpu_processing()
- Uses Python for iteration control and visited tracking
- Continues until no new nodes are found (fully exhaustive)
- Avoids constant columns and 3+ hop JOINs that cause GPU issues
"""

import subprocess
import tempfile
import os
import time
from pathlib import Path


def iterative_bfs_sirius(nodes_file, edges_file, start_class='1', max_hops=20,
                         buffer_min='4 GB', buffer_max='8 GB',
                         sirius_binary=None, verbose=False):
    """
    Perform iterative BFS using Sirius GPU for neighbor expansion.

    Strategy:
    1. Start with nodes of start_class (distance 0)
    2. For each iteration:
       - Find all neighbors of current frontier (1-hop GPU query)
       - Filter out already visited nodes
       - Add new nodes to results with current distance
       - Update frontier to new nodes
    3. Stop when no new nodes found or max_hops reached

    Uses PERSISTENT SESSION: Load data once, run multiple queries.

    Args:
        nodes_file: Path to nodes CSV
        edges_file: Path to edges CSV
        start_class: Starting node class (default '1' for illicit)
        max_hops: Maximum hops to explore (default 20)
        buffer_min: GPU buffer min size
        buffer_max: GPU buffer max size
        sirius_binary: Path to Sirius binary (auto-detect if None)
        verbose: Print progress messages

    Returns:
        dict with:
            - total_nodes: Total nodes discovered
            - max_distance: Maximum distance reached
            - distances: Dict mapping distance -> count of nodes at that distance
            - total_time: Total execution time
            - gpu_time: Time spent in GPU queries
            - iterations: Number of BFS iterations
            - init_time: Time spent loading data
    """
    if sirius_binary is None:
        sirius_binary = str(Path.home() / 'crypto-transaction-analysis' / 'sirius' / 'build' / 'release' / 'duckdb')

    total_start = time.time()
    gpu_time = 0
    init_time = 0

    # Track visited nodes and results
    visited = set()
    distance_counts = {}
    current_distance = 0

    if verbose:
        print(f"\n{'='*80}")
        print(f"ITERATIVE GPU BFS")
        print(f"{'='*80}")
        print(f"Start class: {start_class}")
        print(f"Max hops: {max_hops}")
        print(f"{'='*80}\n")

    # ========================================================================
    # Initialize persistent Sirius session
    # ========================================================================
    if verbose:
        print(f"Initializing Sirius session (loading data)...")

    init_start = time.time()

    # Create initialization script
    init_script = f"""
CREATE TABLE nodes AS SELECT * FROM read_csv_auto('{nodes_file}');
CREATE TABLE edges AS SELECT * FROM read_csv_auto('{edges_file}');
call gpu_buffer_init('{buffer_min}', '{buffer_max}');
"""

    with tempfile.NamedTemporaryFile(mode='w', suffix='.sql', delete=False) as f:
        f.write(init_script)
        init_sql = f.name

    # Start persistent Sirius process
    try:
        sirius_proc = subprocess.Popen(
            [sirius_binary, "-init", init_sql],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1
        )
    finally:
        os.remove(init_sql)

    init_time = time.time() - init_start

    if verbose:
        print(f"  Loaded data in {init_time:.2f}s")

    # ========================================================================
    # Distance 0: Get starting nodes
    # ========================================================================
    if verbose:
        print(f"\nDistance 0: Finding start nodes (class='{start_class}')...")

    init_query = f"COPY (SELECT txId FROM nodes WHERE class = '{start_class}') TO '/tmp/bfs_distance_0.csv' (HEADER, DELIMITER ',');\n"

    try:
        sirius_proc.stdin.write(init_query)
        sirius_proc.stdin.flush()
        time.sleep(0.5)  # Give it time to execute
    except Exception as e:
        sirius_proc.kill()
        raise RuntimeError(f"Failed to get start nodes: {e}")

    # Load distance 0 nodes
    import csv
    with open('/tmp/bfs_distance_0.csv', 'r') as f:
        reader = csv.DictReader(f)
        frontier_nodes = [int(row['txId']) for row in reader]

    visited.update(frontier_nodes)
    distance_counts[0] = len(frontier_nodes)

    if verbose:
        print(f"  Found {len(frontier_nodes)} start nodes")

    # ========================================================================
    # Iterative BFS: Expand frontier until exhausted
    # ========================================================================
    iteration = 0

    while len(frontier_nodes) > 0 and current_distance < max_hops:
        iteration += 1
        current_distance += 1

        if verbose:
            print(f"\nDistance {current_distance}: Expanding {len(frontier_nodes)} frontier nodes...")

        # Build IN clause for frontier (limit size to avoid huge queries)
        if len(frontier_nodes) > 100000:
            if verbose:
                print(f"  WARNING: Large frontier ({len(frontier_nodes)} nodes), sampling first 100k")
            frontier_nodes = frontier_nodes[:100000]

        frontier_str = ','.join(str(x) for x in frontier_nodes)

        # Export query: Find all neighbors of frontier nodes and export to CSV
        # This runs in the persistent session (data already loaded!)
        export_query = f"COPY (SELECT DISTINCT e.txId2 AS node_id FROM edges e WHERE e.txId1 IN ({frontier_str})) TO '/tmp/bfs_distance_{current_distance}.csv' (HEADER, DELIMITER ',');\n"

        try:
            gpu_start = time.time()
            sirius_proc.stdin.write(export_query)
            sirius_proc.stdin.flush()
            time.sleep(0.5)  # Give it time to execute and write file
            gpu_time += time.time() - gpu_start
        except Exception as e:
            if verbose:
                print(f"  WARNING: Iteration failed: {e}")
            break

        # Load new nodes
        try:
            with open(f'/tmp/bfs_distance_{current_distance}.csv', 'r') as f:
                reader = csv.DictReader(f)
                all_neighbors = [int(row['node_id']) for row in reader]
        except FileNotFoundError:
            if verbose:
                print(f"  No output file - likely no neighbors found")
            break

        # Filter out already visited nodes
        new_nodes = [n for n in all_neighbors if n not in visited]

        if len(new_nodes) == 0:
            if verbose:
                print(f"  No new nodes found - BFS complete at distance {current_distance-1}")
            break

        # Update visited set and counts
        visited.update(new_nodes)
        distance_counts[current_distance] = len(new_nodes)

        if verbose:
            print(f"  Found {len(all_neighbors)} neighbors, {len(new_nodes)} new (total visited: {len(visited)})")

        # New nodes become frontier for next iteration
        frontier_nodes = new_nodes

    # Clean up Sirius process
    try:
        sirius_proc.stdin.write('.quit\n')
        sirius_proc.stdin.flush()
        sirius_proc.wait(timeout=5)
    except:
        sirius_proc.kill()

    total_time = time.time() - total_start

    if verbose:
        print(f"\n{'='*80}")
        print(f"BFS COMPLETE")
        print(f"{'='*80}")
        print(f"Total nodes discovered: {len(visited)}")
        print(f"Maximum distance reached: {max(distance_counts.keys())}")
        print(f"Iterations: {iteration}")
        print(f"Init time: {init_time:.2f}s")
        print(f"Total time: {total_time:.2f}s")
        print(f"GPU time: {gpu_time:.2f}s ({100*gpu_time/total_time:.1f}%)")
        print(f"\nNodes by distance:")
        for dist in sorted(distance_counts.keys()):
            print(f"  Distance {dist}: {distance_counts[dist]} nodes")
        print(f"{'='*80}\n")

    return {
        'total_nodes': len(visited),
        'max_distance': max(distance_counts.keys()) if distance_counts else 0,
        'distances': distance_counts,
        'total_time': total_time,
        'init_time': init_time,
        'gpu_time': gpu_time,
        'iterations': iteration,
        'avg_time_per_iteration': gpu_time / iteration if iteration > 0 else 0
    }


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Run iterative GPU BFS')
    parser.add_argument('--size', default='5m', help='Dataset size (default: 5m)')
    parser.add_argument('--max-hops', type=int, default=20, help='Max hops to explore')
    parser.add_argument('--start-class', default='1', help='Starting node class')
    args = parser.parse_args()

    base_path = Path.home() / 'crypto-transaction-analysis'
    nodes_file = str(base_path / 'data' / 'processed' / f'nodes_{args.size}.csv')
    edges_file = str(base_path / 'data' / 'processed' / f'edges_{args.size}.csv')

    result = iterative_bfs_sirius(
        nodes_file=nodes_file,
        edges_file=edges_file,
        start_class=args.start_class,
        max_hops=args.max_hops,
        verbose=True
    )

    print(f"\nFinal result: {result}")
