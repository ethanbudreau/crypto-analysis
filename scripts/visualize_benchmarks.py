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

    # Load AWS data - find most recent
    aws_files = sorted(glob.glob("results/aws_persistent_session/all_results_*.csv"), reverse=True)
    if aws_files:
        aws_file = aws_files[0]
        print(f"  AWS: {aws_file}")
        aws_df = pd.read_csv(aws_file)
        aws_df['platform'] = 'AWS'
        df = pd.concat([local_df, aws_df], ignore_index=True)
    else:
        print("  Warning: No AWS results found, using local only")
        df = local_df

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

    # Remove extra subplots (we have 4 queries, but 2x3=6 subplots)
    fig.delaxes(axes[4])
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

    # Remove extra subplots (we have 4 queries, but 2x3=6 subplots)
    fig.delaxes(axes[4])
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


def plot_gpu_vs_cpus(df):
    """
    Plot 4: GPU speedup vs CPU from the other platform.
    Left: Tesla T4 (AWS) speedup vs Local CPU
    Right: RTX 3050 (Local) speedup vs AWS CPU
    """
    print("\nGenerating Plot 4: GPU vs CPU Speedups...")

    # Filter to common dataset sizes
    common_sizes = ['100k', '1m', '5m', '20m']
    df_common = df[df['dataset_size'].isin(common_sizes)].copy()

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 7))

    # Get CPU times for both platforms
    local_cpu = df_common[(df_common['platform'] == 'Local') & (df_common['database'] == 'duckdb')]
    aws_cpu = df_common[(df_common['platform'] == 'AWS') & (df_common['database'] == 'duckdb')]

    # Get GPU times for both platforms
    local_gpu = df_common[(df_common['platform'] == 'Local') & (df_common['database'] == 'sirius')]
    aws_gpu = df_common[(df_common['platform'] == 'AWS') & (df_common['database'] == 'sirius')]

    # Calculate speedups for Tesla T4 vs Local CPU (cross-platform comparison)
    t4_speedups = []
    for size in common_sizes:
        for query in QUERY_TYPES:
            t4_time = aws_gpu[(aws_gpu['dataset_size'] == size) & (aws_gpu['query'] == query)]['avg_query_time'].values
            local_cpu_time = local_cpu[(local_cpu['dataset_size'] == size) & (local_cpu['query'] == query)]['avg_query_time'].values

            if len(t4_time) > 0 and len(local_cpu_time) > 0:
                t4_speedups.append({
                    'dataset_size': size,
                    'query': query,
                    'speedup': local_cpu_time[0] / t4_time[0]
                })

    # Calculate speedups for RTX 3050 vs AWS CPU (cross-platform comparison)
    rtx_speedups = []
    for size in common_sizes:
        for query in QUERY_TYPES:
            rtx_time = local_gpu[(local_gpu['dataset_size'] == size) & (local_gpu['query'] == query)]['avg_query_time'].values
            aws_cpu_time = aws_cpu[(aws_cpu['dataset_size'] == size) & (aws_cpu['query'] == query)]['avg_query_time'].values

            if len(rtx_time) > 0 and len(aws_cpu_time) > 0:
                rtx_speedups.append({
                    'dataset_size': size,
                    'query': query,
                    'speedup': aws_cpu_time[0] / rtx_time[0]
                })

    # Plot T4 vs Local CPU
    t4_df = pd.DataFrame(t4_speedups)
    if len(t4_df) > 0:
        x_labels = [f"{row['dataset_size']}\n{row['query']}" for _, row in t4_df.iterrows()]
        x = np.arange(len(x_labels))

        ax1.bar(x, t4_df['speedup'], width=0.7, color='#74c476')

        ax1.set_xlabel('Dataset Size / Query Type', fontsize=11)
        ax1.set_ylabel('Speedup Factor (×)', fontsize=11)
        ax1.set_title('Tesla T4 (AWS) vs Local CPU (Core Ultra 7)', fontsize=14, fontweight='bold')
        ax1.set_xticks(x)
        ax1.set_xticklabels(x_labels, rotation=45, ha='right', fontsize=8)
        ax1.axhline(y=1, color='red', linestyle='--', linewidth=1.5, alpha=0.7)
        ax1.grid(axis='y', alpha=0.3)

    # Plot RTX 3050 vs AWS CPU
    rtx_df = pd.DataFrame(rtx_speedups)
    if len(rtx_df) > 0:
        x_labels = [f"{row['dataset_size']}\n{row['query']}" for _, row in rtx_df.iterrows()]
        x = np.arange(len(x_labels))

        ax2.bar(x, rtx_df['speedup'], width=0.7, color='#238b45')

        ax2.set_xlabel('Dataset Size / Query Type', fontsize=11)
        ax2.set_ylabel('Speedup Factor (×)', fontsize=11)
        ax2.set_title('RTX 3050 (Local) vs AWS CPU (Xeon)', fontsize=14, fontweight='bold')
        ax2.set_xticks(x)
        ax2.set_xticklabels(x_labels, rotation=45, ha='right', fontsize=8)
        ax2.axhline(y=1, color='red', linestyle='--', linewidth=1.5, alpha=0.7)
        ax2.grid(axis='y', alpha=0.3)

    plt.suptitle('Cross-Platform GPU vs CPU Comparison (>1× = GPU faster)',
                 fontsize=14, fontweight='bold')
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / '04_gpu_vs_cpu_speedups.png', dpi=300, bbox_inches='tight')
    print(f"  Saved: {OUTPUT_DIR / '04_gpu_vs_cpu_speedups.png'}")
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
    plot_gpu_vs_cpus(df)
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
