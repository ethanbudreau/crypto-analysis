#!/usr/bin/env python3
"""
Visualization Script
Generates charts and figures from benchmark results.

Creates:
- Comparative bar charts (DuckDB vs Sirius execution time)
- Scalability curves (performance vs dataset size)
- CPU/GPU utilization plots
- Performance speedup analysis

Usage:
    python scripts/03_visualize.py
"""

import os
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path


def load_results(results_file='results/benchmarks.csv'):
    """
    Load benchmark results from CSV.

    Args:
        results_file: Path to benchmarks CSV file

    Returns:
        pandas DataFrame with results
    """
    if not os.path.exists(results_file):
        print(f"✗ Results file not found: {results_file}")
        print("  Run benchmarks first: python scripts/02_run_benchmarks.py")
        return None

    df = pd.read_csv(results_file)
    print(f"✓ Loaded {len(df)} benchmark results")
    return df


def plot_execution_time_comparison(df):
    """
    Create bar chart comparing execution times across databases.

    Args:
        df: Benchmark results DataFrame
    """
    print("\nGenerating execution time comparison chart...")

    # Set style
    sns.set_style("whitegrid")

    # Create figure
    fig, ax = plt.subplots(figsize=(12, 6))

    # Filter and prepare data
    plot_data = df[df['avg_execution_time'].notna()].copy()

    # Create grouped bar chart
    # TODO: Implement proper grouped bar chart
    # For now, simple placeholder
    for db in plot_data['database'].unique():
        db_data = plot_data[plot_data['database'] == db]
        ax.bar(
            range(len(db_data)),
            db_data['avg_execution_time'],
            label=db.upper(),
            alpha=0.8
        )

    ax.set_xlabel('Query', fontsize=12)
    ax.set_ylabel('Avg Execution Time (seconds)', fontsize=12)
    ax.set_title('Query Execution Time: DuckDB vs Sirius', fontsize=14, fontweight='bold')
    ax.legend()
    ax.grid(axis='y', alpha=0.3)

    # Save figure
    Path("results/figures").mkdir(parents=True, exist_ok=True)
    output_path = 'results/figures/execution_time_comparison.png'
    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    print(f"✓ Saved: {output_path}")
    plt.close()


def plot_scalability_curves(df):
    """
    Create line plots showing performance vs dataset size.

    Args:
        df: Benchmark results DataFrame
    """
    print("\nGenerating scalability curves...")

    # Set style
    sns.set_style("whitegrid")

    # Create figure with subplots for each query
    queries = df['query'].unique()
    n_queries = len(queries)

    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    axes = axes.flatten()

    # Dataset size ordering
    size_order = ['10k', '50k', '100k', 'full']

    for idx, query in enumerate(queries):
        if idx >= len(axes):
            break

        ax = axes[idx]
        query_data = df[df['query'] == query].copy()

        # Plot lines for each database
        for db in query_data['database'].unique():
            db_data = query_data[query_data['database'] == db]

            # Sort by dataset size
            db_data['size_order'] = pd.Categorical(
                db_data['dataset_size'],
                categories=size_order,
                ordered=True
            )
            db_data = db_data.sort_values('size_order')

            ax.plot(
                db_data['dataset_size'],
                db_data['avg_execution_time'],
                marker='o',
                label=db.upper(),
                linewidth=2,
                markersize=8
            )

        ax.set_xlabel('Dataset Size', fontsize=10)
        ax.set_ylabel('Execution Time (s)', fontsize=10)
        ax.set_title(f'{query.replace("_", "-").upper()} Query', fontsize=11, fontweight='bold')
        ax.legend()
        ax.grid(alpha=0.3)

    # Remove empty subplots
    for idx in range(len(queries), len(axes)):
        fig.delaxes(axes[idx])

    plt.suptitle('Scalability Analysis: Performance vs Dataset Size',
                 fontsize=14, fontweight='bold', y=1.00)
    plt.tight_layout()

    # Save figure
    output_path = 'results/figures/scalability_curves.png'
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    print(f"✓ Saved: {output_path}")
    plt.close()


def plot_speedup_analysis(df):
    """
    Calculate and visualize GPU speedup over CPU.

    Args:
        df: Benchmark results DataFrame
    """
    print("\nGenerating speedup analysis...")

    # Check if we have both DuckDB and Sirius results
    databases = df['database'].unique()
    if 'duckdb' not in databases or 'sirius' not in databases:
        print("  ⚠ Need both DuckDB and Sirius results for speedup analysis")
        return

    # TODO: Implement speedup calculation
    # Speedup = DuckDB_time / Sirius_time
    print("  TODO: Implement speedup calculation and visualization")


def generate_summary_table(df):
    """
    Create a summary table of all benchmark results.

    Args:
        df: Benchmark results DataFrame
    """
    print("\nGenerating summary table...")

    # Create pivot table
    summary = df.pivot_table(
        values='avg_execution_time',
        index=['query', 'dataset_size'],
        columns='database',
        aggfunc='mean'
    )

    # Save as CSV
    output_path = 'results/summary_table.csv'
    summary.to_csv(output_path)
    print(f"✓ Saved: {output_path}")

    # Print to console
    print("\n" + "="*60)
    print("SUMMARY TABLE")
    print("="*60)
    print(summary)


def main():
    """Main execution function."""
    print("="*60)
    print("VISUALIZATION GENERATION")
    print("="*60)

    # Load results
    df = load_results()
    if df is None:
        return

    print(f"\nDataset overview:")
    print(f"  - Databases: {df['database'].unique()}")
    print(f"  - Queries: {df['query'].unique()}")
    print(f"  - Dataset sizes: {df['dataset_size'].unique()}")
    print(f"  - Total benchmarks: {len(df)}")

    # Generate visualizations
    plot_execution_time_comparison(df)
    plot_scalability_curves(df)
    plot_speedup_analysis(df)
    generate_summary_table(df)

    print("\n" + "="*60)
    print("VISUALIZATION COMPLETE")
    print("="*60)
    print("\nGenerated files:")
    print("  - results/figures/execution_time_comparison.png")
    print("  - results/figures/scalability_curves.png")
    print("  - results/summary_table.csv")
    print("\nNext steps:")
    print("  - Review figures for report")
    print("  - Analyze performance trends")
    print("  - Draft findings and insights")


if __name__ == "__main__":
    main()
