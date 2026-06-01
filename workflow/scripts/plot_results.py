#!/usr/bin/env python3
import re
from pathlib import Path
import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns


def parse_sample_model(path):
    stem = Path(path).stem
    match = re.match(r"(?P<sample>[^.]+)\.(?P<model>[^.]+)\.summary", stem)
    if match:
        return match.group("sample"), match.group("model")
    parts = stem.split(".")
    return parts[0], parts[1] if len(parts) > 1 else "unknown"


def select_summary(df):
    if "subset" in df.columns:
        lower = df["subset"].astype(str).str.lower()
        for tag in ["all", "overall"]:
            selected = df[lower == tag]
            if not selected.empty:
                return selected.iloc[0]
    return df.iloc[0]


def main():
    rows = []
    metrics = [str(metric) for metric in snakemake.params.metrics]
    for summary_path in snakemake.input.summary:
        df = pd.read_csv(str(summary_path))
        sample_id, model_name = parse_sample_model(summary_path)
        summary = select_summary(df)
        for metric in metrics:
            if metric in summary.index:
                rows.append({
                    "sample_id": sample_id,
                    "model": model_name,
                    "metric": metric,
                    "value": float(summary[metric]),
                })
    if not rows:
        raise SystemExit("No benchmark metrics found to plot")

    plot_df = pd.DataFrame(rows)
    out_dir = Path(snakemake.output[0]).parent
    out_dir.mkdir(parents=True, exist_ok=True)

    summary_path = out_dir / "benchmark_summary.csv"
    plot_df.to_csv(summary_path, index=False)

    sns.set(style="whitegrid")
    plt.figure(figsize=(10, 6))
    sns.barplot(data=plot_df, x="model", y="value", hue="metric")
    plt.title("Benchmark metrics by model")
    plt.ylabel("Metric value")
    plt.xlabel("Model")
    plt.xticks(rotation=30)
    plt.tight_layout()
    plt.savefig(str(snakemake.output[0]), dpi=200)
