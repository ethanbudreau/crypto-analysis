#!/usr/bin/env python3
"""
Benchmark Visualization Script
Generates comprehensive visualizations comparing DuckDB vs Sirius performance
across different hardware configurations (local and AWS).

Hardware configurations:
- Local DuckDB (i5 CPU)
- Local Sirius (RTX 3050 GPU)
- AWS DuckDB (g4dn.2xlarge CPU)
- AWS Sirius (Tesla T4 GPU)

Dataset sizes: 100k, 1M, 5M, 20M, 50M, 100M edges
"""

import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
from pathlib import Path
import glob

# Set style
sns.set_style("whitegrid")
plt.rcParams['figure.figsize'] = (14, 8)
plt.rcParams['font.size'] = 10

# Output directory
OUTPUT_DIR = Path("results/figures")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Dataset size mapping (for proper ordering and numeric conversion)
DATASET_SIZE_MAP = {
    '100k': 100_000,
    '1m': 1_000_000,
    '5m': 5_000_000,
    '20m': 20_000_000,
    '50m': 50_000_000,
    '100m': 100_000_000
}

# Query types in order
QUERY_TYPES = ['1_hop', '2_hop', 'k_hop', 'shortest_path']

# Color palette for 4 configurations
COLORS = {
    'Local DuckDB': '#08519c',       # Dark blue (faster CPU gets darker color)
    'Local Sirius': '#238b45',       # Dark green
    'AWS DuckDB': '#6baed6',         # Light blue
    'AWS Sirius': '#74c476'          # Light green
}

# Hardware labels for titles
HARDWARE_LABELS = {
    'Local DuckDB': 'Local DuckDB (Core Ultra 7 265k)',
    'Local Sirius': 'Local Sirius (RTX 3050)',
    'AWS DuckDB': 'AWS DuckDB (g4dn.2xlarge)',
    'AWS Sirius': 'AWS Sirius (Tesla T4)'
}


def load_data():
    """Load all benchmark data from local and AWS results."""
    print("Loading benchmark data...")

    # Find most recent local results
    local_files = sorted(glob.glob("results/persistent_session/all_results_*.csv"), reverse=True)
    if not local_files:
        raise FileNotFoundError("No local benchmark results found")
    local_file = local_files[0]
    print(f"  Local: {local_file}")

    # Load local data
    local_df = pd.read_csv(local_file)
    local_df['platform'] = 'Local'

    # Load AWS data (100k-20M)
    aws_file = "results/aws_testing/all_results_20251129_212145.csv"
    print(f"  AWS: {aws_file}")
    aws_df = pd.read_csv(aws_file)
    aws_df['platform'] = 'AWS'

    # Load AWS large datasets (50M, 100M)
    aws_large_file = "results/aws_large_datasets/all_results_20251129_214343.csv"
    print(f"  AWS Large: {aws_large_file}")
    aws_large_df = pd.read_csv(aws_large_file)
    aws_large_df['platform'] = 'AWS'

    # Combine all data
    df = pd.concat([local_df, aws_df, aws_large_df], ignore_index=True)

    # Create configuration label
    df['config'] = df.apply(
        lambda row: f"{'Local' if row['platform'] == 'Local' else 'AWS'} "
                   f"{'DuckDB' if row['database'] == 'duckdb' else 'Sirius'}",
        axis=1
    )

    # Add numeric dataset size for sorting/plotting
    df['dataset_size_num'] = df['dataset_size'].map(DATASET_SIZE_MAP)

    print(f"  Total records: {len(df)}")
    print(f"  Configurations: {df['config'].unique()}")
    print(f"  Dataset sizes: {sorted(df['dataset_size'].unique(), key=lambda x: DATASET_SIZE_MAP[x])}")

    return df


def plot_performance_comparison(df):
    """
    Plot 1: Performance comparison across all 4 configurations.
    Grouped bar chart with separate subplot for each query type.
    """
    print("\nGenerating Plot 1: Performance Comparison...")

    # Filter to common dataset sizes (100k-20M)
    common_sizes = ['100k', '1m', '5m', '20m']
    df_common = df[df['dataset_size'].isin(common_sizes)].copy()

    fig, axes = plt.subplots(2, 3, figsize=(18, 10))
    axes = axes.flatten()

    for idx, query in enumerate(QUERY_TYPES):
        ax = axes[idx]
        query_df = df_common[df_common['query'] == query]

        # Pivot for grouped bar chart
        pivot = query_df.pivot_table(
            index='dataset_size',
            columns='config',
            values='avg_query_time',
            aggfunc='mean'
        )

        # Reorder columns and index
        pivot = pivot.reindex(common_sizes)
        pivot = pivot[['Local DuckDB', 'Local Sirius', 'AWS DuckDB', 'AWS Sirius']]

        # Plot
        pivot.plot(kind='bar', ax=ax, color=[COLORS[c] for c in pivot.columns], width=0.8)
        ax.set_title(f'{query.replace("_", " ").title()} Query', fontsize=12, fontweight='bold')
        ax.set_xlabel('Dataset Size', fontsize=10)
        ax.set_ylabel('Avg Query Time (seconds)', fontsize=10)
        ax.set_xticklabels(ax.get_xticklabels(), rotation=45, ha='right')
        ax.legend(fontsize=8, loc='upper left')
        ax.grid(axis='y', alpha=0.3)

    # Remove extra subplot
    fig.delaxes(axes[5])

    plt.suptitle('Performance Comparison: DuckDB vs Sirius (Local & AWS)',
                 fontsize=16, fontweight='bold', y=0.995)
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / '01_performance_comparison.png', dpi=300, bbox_inches='tight')
    print(f"  Saved: {OUTPUT_DIR / '01_performance_comparison.png'}")
    plt.close()


def plot_scaling_analysis(df):
    """
    Plot 2: Scaling analysis with log-log scale.
    Shows how each configuration scales with dataset size (100k-100M).
    """
    print("\nGenerating Plot 2: Scaling Analysis...")

    fig, axes = plt.subplots(2, 3, figsize=(18, 10))
    axes = axes.flatten()

    for idx, query in enumerate(QUERY_TYPES):
        ax = axes[idx]
        query_df = df[df['query'] == query]

        for config in ['Local DuckDB', 'Local Sirius', 'AWS DuckDB', 'AWS Sirius']:
            config_df = query_df[query_df['config'] == config].copy()
            config_df = config_df.sort_values('dataset_size_num')

            if len(config_df) > 0:
                ax.plot(config_df['dataset_size_num'],
                       config_df['avg_query_time'],
                       marker='o',
                       label=config,
                       color=COLORS[config],
                       linewidth=2,
                       markersize=6)

        ax.set_xscale('log')
        ax.set_yscale('log')
        ax.set_title(f'{query.replace("_", " ").title()} Query', fontsize=12, fontweight='bold')
        ax.set_xlabel('Number of Edges (log scale)', fontsize=10)
        ax.set_ylabel('Avg Query Time (log scale)', fontsize=10)
        ax.legend(fontsize=8)
        ax.grid(True, which="both", ls="-", alpha=0.2)

        # Format x-axis labels
        ax.set_xticks([100_000, 1_000_000, 5_000_000, 20_000_000, 50_000_000, 100_000_000])
        ax.set_xticklabels(['100k', '1M', '5M', '20M', '50M', '100M'], rotation=45, ha='right')

    # Remove extra subplot
    fig.delaxes(axes[5])

    plt.suptitle('Scaling Analysis: Performance vs Dataset Size (Log-Log Scale)',
                 fontsize=16, fontweight='bold', y=0.995)
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / '02_scaling_analysis.png', dpi=300, bbox_inches='tight')
    print(f"  Saved: {OUTPUT_DIR / '02_scaling_analysis.png'}")
    plt.close()


def plot_speedup_factors(df):
    """
    Plot 3: GPU speedup factors.
    Two side-by-side charts: Local (3050 vs CPU) and AWS (T4 vs CPU).
    """
    print("\nGenerating Plot 3: GPU Speedup Factors...")

    # Filter to common dataset sizes
    common_sizes = ['100k', '1m', '5m', '20m']
    df_common = df[df['dataset_size'].isin(common_sizes)].copy()

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6))

    # Calculate speedups
    speedup_data = []

    for platform, ax, title in [('Local', ax1, 'Local: RTX 3050 vs CPU'),
                                  ('AWS', ax2, 'AWS: Tesla T4 vs CPU')]:
        platform_df = df_common[df_common['platform'] == platform]

        for size in common_sizes:
            for query in QUERY_TYPES:
                duckdb_time = platform_df[
                    (platform_df['database'] == 'duckdb') &
                    (platform_df['dataset_size'] == size) &
                    (platform_df['query'] == query)
                ]['avg_query_time'].values

                sirius_time = platform_df[
                    (platform_df['database'] == 'sirius') &
                    (platform_df['dataset_size'] == size) &
                    (platform_df['query'] == query)
                ]['avg_query_time'].values

                if len(duckdb_time) > 0 and len(sirius_time) > 0:
                    speedup = duckdb_time[0] / sirius_time[0]
                    speedup_data.append({
                        'platform': platform,
                        'dataset_size': size,
                        'query': query,
                        'speedup': speedup
                    })

        # Plot for this platform
        platform_speedup = pd.DataFrame([s for s in speedup_data if s['platform'] == platform])

        if len(platform_speedup) > 0:
            pivot = platform_speedup.pivot_table(
                index='dataset_size',
                columns='query',
                values='speedup'
            )
            pivot = pivot.reindex(common_sizes)
            pivot = pivot[QUERY_TYPES]

            pivot.plot(kind='bar', ax=ax, width=0.8)
            ax.set_title(title, fontsize=14, fontweight='bold')
            ax.set_xlabel('Dataset Size', fontsize=11)
            ax.set_ylabel('Speedup Factor (×)', fontsize=11)
            ax.set_xticklabels(ax.get_xticklabels(), rotation=45, ha='right')
            ax.legend(title='Query Type', fontsize=9)
            ax.axhline(y=1, color='red', linestyle='--', linewidth=1, alpha=0.5, label='No speedup')
            ax.grid(axis='y', alpha=0.3)

    plt.suptitle('GPU Speedup Factors: Sirius vs DuckDB',
                 fontsize=16, fontweight='bold')
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / '03_speedup_factors.png', dpi=300, bbox_inches='tight')
    print(f"  Saved: {OUTPUT_DIR / '03_speedup_factors.png'}")
    plt.close()


def plot_platform_comparison(df):
    """
    Plot 4: Platform comparison (Local vs AWS).
    Two charts: CPU comparison and GPU comparison.
    """
    print("\nGenerating Plot 4: Platform Comparison...")

    # Filter to common dataset sizes
    common_sizes = ['100k', '1m', '5m', '20m']
    df_common = df[df['dataset_size'].isin(common_sizes)].copy()

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6))

    # CPU Comparison (DuckDB)
    cpu_df = df_common[df_common['database'] == 'duckdb']
    cpu_pivot = cpu_df.pivot_table(
        index=['dataset_size', 'query'],
        columns='platform',
        values='avg_query_time'
    )
    cpu_pivot = cpu_pivot.reset_index()

    # Average across queries for simplicity
    cpu_avg = cpu_df.groupby(['dataset_size', 'platform'])['avg_query_time'].mean().unstack()
    cpu_avg = cpu_avg.reindex(common_sizes)
    # Reorder columns to ensure Local is first (faster CPU gets darker color)
    cpu_avg = cpu_avg[['Local', 'AWS']]

    cpu_avg.plot(kind='bar', ax=ax1, color=['#08519c', '#6baed6'], width=0.7)
    ax1.set_title('CPU Comparison: Local vs AWS DuckDB', fontsize=14, fontweight='bold')
    ax1.set_xlabel('Dataset Size', fontsize=11)
    ax1.set_ylabel('Avg Query Time (seconds)', fontsize=11)
    ax1.set_xticklabels(ax1.get_xticklabels(), rotation=45, ha='right')
    ax1.legend(['Local (Core Ultra 7 265k)', 'AWS (g4dn.2xlarge)'], fontsize=10)
    ax1.grid(axis='y', alpha=0.3)

    # GPU Comparison (Sirius)
    gpu_df = df_common[df_common['database'] == 'sirius']
    gpu_avg = gpu_df.groupby(['dataset_size', 'platform'])['avg_query_time'].mean().unstack()
    gpu_avg = gpu_avg.reindex(common_sizes)
    # Reorder columns to ensure Local is first (darker color for local GPU)
    gpu_avg = gpu_avg[['Local', 'AWS']]

    gpu_avg.plot(kind='bar', ax=ax2, color=['#238b45', '#74c476'], width=0.7)
    ax2.set_title('GPU Comparison: RTX 3050 vs Tesla T4', fontsize=14, fontweight='bold')
    ax2.set_xlabel('Dataset Size', fontsize=11)
    ax2.set_ylabel('Avg Query Time (seconds)', fontsize=11)
    ax2.set_xticklabels(ax2.get_xticklabels(), rotation=45, ha='right')
    ax2.legend(['Local (RTX 3050)', 'AWS (Tesla T4)'], fontsize=10)
    ax2.grid(axis='y', alpha=0.3)

    plt.suptitle('Platform Comparison: Local vs AWS Performance',
                 fontsize=16, fontweight='bold')
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / '04_platform_comparison.png', dpi=300, bbox_inches='tight')
    print(f"  Saved: {OUTPUT_DIR / '04_platform_comparison.png'}")
    plt.close()


def plot_summary_heatmaps(df):
    """
    Plot 5: Summary heatmaps for all 4 configurations.
    """
    print("\nGenerating Plot 5: Summary Heatmaps...")

    fig, axes = plt.subplots(2, 2, figsize=(16, 12))
    axes = axes.flatten()

    configs = ['Local DuckDB', 'Local Sirius', 'AWS DuckDB', 'AWS Sirius']

    for idx, config in enumerate(configs):
        ax = axes[idx]
        config_df = df[df['config'] == config]

        # Get dataset sizes available for this config
        available_sizes = sorted(config_df['dataset_size'].unique(),
                                key=lambda x: DATASET_SIZE_MAP[x])

        # Create pivot table
        pivot = config_df.pivot_table(
            index='dataset_size',
            columns='query',
            values='avg_query_time'
        )

        # Reorder
        pivot = pivot.reindex(available_sizes)
        pivot = pivot[[q for q in QUERY_TYPES if q in pivot.columns]]

        # Plot heatmap
        sns.heatmap(pivot, annot=True, fmt='.3f', cmap='YlOrRd', ax=ax,
                   cbar_kws={'label': 'Avg Query Time (s)'})
        ax.set_title(config, fontsize=13, fontweight='bold')
        ax.set_xlabel('Query Type', fontsize=10)
        ax.set_ylabel('Dataset Size', fontsize=10)
        ax.set_yticklabels(ax.get_yticklabels(), rotation=0)

    plt.suptitle('Performance Heatmaps: All Configurations',
                 fontsize=16, fontweight='bold', y=0.995)
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / '05_summary_heatmaps.png', dpi=300, bbox_inches='tight')
    print(f"  Saved: {OUTPUT_DIR / '05_summary_heatmaps.png'}")
    plt.close()


def generate_summary_report(df):
    """Generate text summary of key findings."""
    print("\nGenerating Summary Report...")

    report = []
    report.append("="*80)
    report.append("BENCHMARK SUMMARY REPORT")
    report.append("="*80)
    report.append("")

    # Overall stats
    report.append("Dataset Coverage:")
    for config in df['config'].unique():
        config_df = df[df['config'] == config]
        sizes = sorted(config_df['dataset_size'].unique(), key=lambda x: DATASET_SIZE_MAP[x])
        report.append(f"  {config}: {', '.join(sizes)}")
    report.append("")

    # Best performing configuration per dataset size
    report.append("Fastest Configuration by Dataset Size (averaged across queries):")
    common_sizes = ['100k', '1m', '5m', '20m']
    for size in common_sizes:
        size_df = df[df['dataset_size'] == size]
        avg_by_config = size_df.groupby('config')['avg_query_time'].mean()
        fastest = avg_by_config.idxmin()
        time = avg_by_config.min()
        report.append(f"  {size}: {fastest} ({time:.4f}s)")
    report.append("")

    # GPU speedup summary
    report.append("Average GPU Speedup Factors (Sirius vs DuckDB):")
    for platform in ['Local', 'AWS']:
        platform_df = df[(df['platform'] == platform) &
                        (df['dataset_size'].isin(common_sizes))]

        duckdb_avg = platform_df[platform_df['database'] == 'duckdb']['avg_query_time'].mean()
        sirius_avg = platform_df[platform_df['database'] == 'sirius']['avg_query_time'].mean()

        if not pd.isna(duckdb_avg) and not pd.isna(sirius_avg) and sirius_avg > 0:
            speedup = duckdb_avg / sirius_avg
            report.append(f"  {platform}: {speedup:.1f}×")
    report.append("")

    # Large dataset performance (AWS Sirius only)
    report.append("Large Dataset Performance (AWS Sirius T4):")
    for size in ['50m', '100m']:
        size_df = df[(df['config'] == 'AWS Sirius') & (df['dataset_size'] == size)]
        if len(size_df) > 0:
            avg_time = size_df['avg_query_time'].mean()
            report.append(f"  {size}: {avg_time:.4f}s average")
    report.append("")

    report.append("="*80)

    # Write to file
    report_file = OUTPUT_DIR / 'summary_report.txt'
    with open(report_file, 'w') as f:
        f.write('\n'.join(report))

    print(f"  Saved: {report_file}")

    # Also print to console
    print("\n" + '\n'.join(report))


def main():
    """Main execution."""
    print("="*80)
    print("BENCHMARK VISUALIZATION GENERATOR")
    print("="*80)

    # Load data
    df = load_data()

    # Generate all visualizations
    plot_performance_comparison(df)
    plot_scaling_analysis(df)
    plot_speedup_factors(df)
    plot_platform_comparison(df)
    plot_summary_heatmaps(df)

    # Generate summary report
    generate_summary_report(df)

    print("\n" + "="*80)
    print("VISUALIZATION COMPLETE")
    print("="*80)
    print(f"\nAll figures saved to: {OUTPUT_DIR}")
    print("\nGenerated files:")
    for f in sorted(OUTPUT_DIR.glob("*.png")):
        print(f"  - {f.name}")
    print(f"  - summary_report.txt")


if __name__ == "__main__":
    main()
