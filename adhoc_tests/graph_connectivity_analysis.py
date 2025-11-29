#!/usr/bin/env python3
"""
Graph Connectivity Analysis - BFS Exploration

Analyzes the Bitcoin transaction graph to determine:
- Maximum reachable distance from illicit nodes
- Coverage of fixed-depth queries (e.g., 5-hop shortest_path)
- Distribution of nodes by distance
- Percentage of disconnected components

This validates the design choices for shortest_path and k-hop queries.
"""

import duckdb
import sys

def analyze_graph_connectivity(dataset_size='100k', max_hops=100):
    """
    Perform BFS from illicit nodes to analyze graph connectivity.

    Args:
        dataset_size: Dataset to analyze (e.g., '100k', '1m', '5m', '20m')
        max_hops: Maximum distance to explore (stops early if no new nodes found)

    Returns:
        Dictionary with analysis results
    """
    conn = duckdb.connect(':memory:')

    # Load data
    print(f'Loading {dataset_size} dataset...')
    nodes_file = f'data/processed/nodes_{dataset_size}.csv'
    edges_file = f'data/processed/edges_{dataset_size}.csv'

    conn.execute(f"CREATE TABLE nodes AS SELECT * FROM read_csv_auto('{nodes_file}')")
    conn.execute(f"CREATE TABLE edges AS SELECT * FROM read_csv_auto('{edges_file}')")

    # Get total counts
    total_nodes = conn.execute('SELECT COUNT(*) FROM nodes').fetchone()[0]
    illicit_nodes = conn.execute("SELECT COUNT(*) FROM nodes WHERE class = '1'").fetchone()[0]

    print(f'Total nodes: {total_nodes:,}')
    print(f'Illicit nodes: {illicit_nodes:,}')
    print()

    # Create temp table to track visited nodes
    conn.execute('CREATE TEMP TABLE visited_nodes (node_id INTEGER PRIMARY KEY, distance INTEGER)')

    # Start with illicit nodes at distance 0
    conn.execute("""
        INSERT INTO visited_nodes (node_id, distance)
        SELECT txId, 0
        FROM nodes
        WHERE class = '1'
    """)

    print('Hop | New Nodes | Cumulative | % of Total')
    print('-' * 50)

    # Track previous cumulative to detect when we stop finding nodes
    prev_cumulative = illicit_nodes
    print(f'  0 | {illicit_nodes:>9,} | {illicit_nodes:>10,} | {(illicit_nodes/total_nodes)*100:>6.2f}%')

    # Iteratively expand to max_hops
    final_hop = 0
    for hop in range(1, max_hops + 1):
        # Find new nodes at this distance
        query = f"""
            INSERT OR IGNORE INTO visited_nodes (node_id, distance)
            SELECT DISTINCT e.txId2, {hop}
            FROM visited_nodes v
            JOIN edges e ON v.node_id = e.txId1
            WHERE v.distance = {hop - 1}
              AND e.txId2 NOT IN (SELECT node_id FROM visited_nodes)
        """

        conn.execute(query)

        # Count new nodes added
        cumulative = conn.execute('SELECT COUNT(*) FROM visited_nodes').fetchone()[0]
        new_nodes = cumulative - prev_cumulative

        print(f'{hop:>3} | {new_nodes:>9,} | {cumulative:>10,} | {(cumulative/total_nodes)*100:>6.2f}%')

        # Stop if no new nodes found
        if new_nodes == 0:
            print(f'\n✓ Reached maximum distance at hop {hop-1}')
            final_hop = hop - 1
            break

        prev_cumulative = cumulative
        final_hop = hop

    # Final summary
    final_count = conn.execute('SELECT COUNT(*) FROM visited_nodes').fetchone()[0]
    unreachable = total_nodes - final_count

    print(f'\n' + '=' * 50)
    print(f'Reachable nodes: {final_count:,} ({(final_count/total_nodes)*100:.1f}%)')
    print(f'Unreachable nodes: {unreachable:,} ({(unreachable/total_nodes)*100:.1f}%)')

    # Calculate coverage for common query depths
    coverage_5 = conn.execute('SELECT COUNT(*) FROM visited_nodes WHERE distance <= 5').fetchone()[0]
    coverage_10 = conn.execute('SELECT COUNT(*) FROM visited_nodes WHERE distance <= 10').fetchone()[0]

    print(f'\nQuery coverage analysis:')
    print(f'  5-hop query:  {coverage_5:>6,} nodes ({(coverage_5/final_count)*100:>5.1f}% of reachable)')
    print(f'  10-hop query: {coverage_10:>6,} nodes ({(coverage_10/final_count)*100:>5.1f}% of reachable)')

    # Show distance distribution summary
    print(f'\nDistance distribution summary:')
    print(f'  0-5:   {coverage_5:>6,} nodes')
    ranges = [(6, 10), (11, 20), (21, 50), (51, 100)]
    for start, end in ranges:
        count = conn.execute(
            f'SELECT COUNT(*) FROM visited_nodes WHERE distance BETWEEN {start} AND {end}'
        ).fetchone()[0]
        if count > 0:
            print(f'  {start}-{end}: {count:>6,} nodes')

    print(f'\nMaximum distance reached: {final_hop}')

    conn.close()

    return {
        'dataset_size': dataset_size,
        'total_nodes': total_nodes,
        'illicit_nodes': illicit_nodes,
        'reachable_nodes': final_count,
        'unreachable_nodes': unreachable,
        'max_distance': final_hop,
        'coverage_5hop': coverage_5,
        'coverage_10hop': coverage_10
    }


if __name__ == '__main__':
    # Parse command line arguments
    dataset = sys.argv[1] if len(sys.argv) > 1 else '100k'
    max_hops = int(sys.argv[2]) if len(sys.argv) > 2 else 100

    print('=' * 50)
    print('GRAPH CONNECTIVITY ANALYSIS')
    print('=' * 50)
    print()

    results = analyze_graph_connectivity(dataset, max_hops)

    print('\n' + '=' * 50)
    print('Analysis complete!')
    print('=' * 50)
