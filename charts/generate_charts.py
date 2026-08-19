#!/usr/bin/env python3
"""
generate_charts.py — Create bar charts comparing all 5 platforms.

Reads results/summary/benchmark_summary.json and produces PNG charts in charts/.
"""
import os
import sys
import json
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use("Agg")  # non-interactive backend

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SUMMARY_PATH = os.path.join(BASE_DIR, "results", "summary", "benchmark_summary.json")
CHARTS_DIR = os.path.dirname(os.path.abspath(__file__))

# Colour palette — one colour per platform
COLORS = {
    "cognodb": "#4A90D9",
    "neo4j": "#008CC1",
    "memgraph": "#FF6B35",
    "arangodb": "#6DB33F",
    "falkordb": "#E63946",
}


def _bar_chart(title, labels, p50_vals, p95_vals, ylabel, filename):
    """Draw a grouped bar chart with p50 and p95 bars."""
    x = range(len(labels))
    width = 0.35

    fig, ax = plt.subplots(figsize=(10, 6))
    bars1 = ax.bar([i - width / 2 for i in x], p50_vals, width, label="p50", color="#4A90D9")
    bars2 = ax.bar([i + width / 2 for i in x], p95_vals, width, label="p95", color="#E63946")

    ax.set_ylabel(ylabel)
    ax.set_title(title)
    ax.set_xticks(list(x))
    ax.set_xticklabels(labels, rotation=30, ha="right")
    ax.legend()
    ax.grid(axis="y", alpha=0.3)

    # Value labels on bars
    for bar in bars1 + bars2:
        height = bar.get_height()
        if height > 0:
            ax.annotate(
                f"{height:.1f}",
                xy=(bar.get_x() + bar.get_width() / 2, height),
                xytext=(0, 3),
                textcoords="offset points",
                ha="center",
                va="bottom",
                fontsize=7,
            )

    fig.tight_layout()
    path = os.path.join(CHARTS_DIR, filename)
    fig.savefig(path, dpi=150)
    plt.close(fig)
    print(f"  📈 Saved → {path}")


def _qps_chart(title, labels, qps_vals, filename):
    """Draw a simple bar chart for QPS values."""
    fig, ax = plt.subplots(figsize=(10, 6))
    colors = [COLORS.get(l.split("_")[0], "#888888") for l in labels]
    bars = ax.bar(range(len(labels)), qps_vals, color=colors)

    ax.set_ylabel("Queries per Second (QPS)")
    ax.set_title(title)
    ax.set_xticks(range(len(labels)))
    ax.set_xticklabels(labels, rotation=30, ha="right")
    ax.grid(axis="y", alpha=0.3)

    for bar in bars:
        height = bar.get_height()
        if height > 0:
            ax.annotate(
                f"{height:.0f}",
                xy=(bar.get_x() + bar.get_width() / 2, height),
                xytext=(0, 3),
                textcoords="offset points",
                ha="center",
                va="bottom",
                fontsize=8,
            )

    fig.tight_layout()
    path = os.path.join(CHARTS_DIR, filename)
    fig.savefig(path, dpi=150)
    plt.close(fig)
    print(f"  📈 Saved → {path}")


def generate():
    if not os.path.exists(SUMMARY_PATH):
        print(f"❌ Summary file not found: {SUMMARY_PATH}")
        print("   Run 'python scripts/run_all.py' first.")
        return

    with open(SUMMARY_PATH) as f:
        data = json.load(f)

    # ----- Traversal charts (one per hop depth) -----
    traversal = data.get("traversal", {})
    for hop in [1, 2, 3]:
        labels, p50s, p95s = [], [], []
        for key, val in traversal.items():
            if val.get("hop_depth") == hop and "error" not in val:
                labels.append(val["platform"])
                p50s.append(val["p50"])
                p95s.append(val["p95"])
        if labels:
            _bar_chart(
                f"{hop}-Hop Traversal Latency",
                labels, p50s, p95s,
                "Latency (ms)",
                f"traversal_{hop}hop.png",
            )

    # ----- Lookup charts -----
    lookup = data.get("lookup", {})
    for bench in ["point_lookup", "filtered_lookup"]:
        labels, p50s, p95s = [], [], []
        for key, val in lookup.items():
            if val.get("benchmark") == bench and "error" not in val:
                labels.append(val["platform"])
                p50s.append(val["p50"])
                p95s.append(val["p95"])
        if labels:
            _bar_chart(
                f"{bench.replace('_', ' ').title()} Latency",
                labels, p50s, p95s,
                "Latency (ms)",
                f"{bench}.png",
            )

    # ----- Aggregation charts -----
    aggregation = data.get("aggregation", {})
    for bench in ["count", "groupby"]:
        labels, p50s, p95s = [], [], []
        for key, val in aggregation.items():
            if val.get("benchmark") == bench and "error" not in val:
                labels.append(val["platform"])
                p50s.append(val["p50"])
                p95s.append(val["p95"])
        if labels:
            _bar_chart(
                f"{bench.title()} Aggregation Latency",
                labels, p50s, p95s,
                "Latency (ms)",
                f"aggregation_{bench}.png",
            )

    # ----- Mixed workload QPS chart -----
    mixed = data.get("mixed", {})
    for clients in [10, 20, 40]:
        labels, qps_vals = [], []
        for key, val in mixed.items():
            if val.get("clients") == clients and "error" not in val:
                labels.append(val["platform"])
                qps_vals.append(val["qps"])
        if labels:
            _qps_chart(
                f"Mixed Workload QPS @ {clients} Clients",
                labels, qps_vals,
                f"mixed_qps_{clients}clients.png",
            )

    print("\n✅ All charts generated.")


if __name__ == "__main__":
    generate()
