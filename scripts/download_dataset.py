#!/usr/bin/env python3
"""
download_dataset.py — Fetch and prepare the benchmark dataset.

Strategy:
  1. Try downloading the SNAP soc-Pokec relationships file.
  2. If the download fails or times out, generate a synthetic social-network
     graph with the same structure (power-law degree distribution).

Output:
  data/processed/nodes.csv  — columns: id, name
  data/processed/edges.csv  — columns: source_id, target_id, relationship_type
"""
import os
import sys
import random
import argparse
import requests
import gzip
import pandas as pd
from tqdm import tqdm

DATASET_URL = "https://snap.stanford.edu/data/email-Enron.txt.gz"
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW_DIR = os.path.join(BASE_DIR, "data", "raw")
PROCESSED_DIR = os.path.join(BASE_DIR, "data", "processed")

# Default edge limit (Enron has 183,831 edges)
DEFAULT_EDGE_LIMIT = 200_000


# -------------------------------------------------------------------
# Option A: Download from SNAP
# -------------------------------------------------------------------

def download_snap(edge_limit: int, timeout: int = 120) -> bool:
    """Try to download and parse the SNAP dataset.
    Returns True on success, False on failure/timeout.
    """
    os.makedirs(RAW_DIR, exist_ok=True)
    raw_gz = os.path.join(RAW_DIR, "dataset.txt.gz")

    if not os.path.exists(raw_gz):
        print(f"Downloading {DATASET_URL} ...")
        try:
            resp = requests.get(DATASET_URL, stream=True, timeout=timeout)
            resp.raise_for_status()
            total = int(resp.headers.get("content-length", 0))
            with open(raw_gz, "wb") as f, tqdm(
                total=total, unit="iB", unit_scale=True, desc="Download"
            ) as bar:
                for chunk in resp.iter_content(8192):
                    f.write(chunk)
                    bar.update(len(chunk))
        except Exception as e:
            print(f"⚠️  SNAP download failed: {e}")
            if os.path.exists(raw_gz):
                os.remove(raw_gz)
            return False

    # Parse the gzipped edge list
    print(f"Parsing (limit {edge_limit} edges) ...")
    edges, nodes = [], set()
    try:
        with gzip.open(raw_gz, "rt") as f:
            for line in f:
                if line.startswith("#"):
                    continue
                if len(edges) >= edge_limit:
                    break
                parts = line.strip().split("\t")
                if len(parts) >= 2:
                    src, dst = parts[0], parts[1]
                    edges.append((src, dst, "KNOWS"))
                    nodes.add(src)
                    nodes.add(dst)
    except Exception as e:
        print(f"⚠️  Parsing failed: {e}")
        return False

    _save(nodes, edges)
    return True


# -------------------------------------------------------------------
# Option B: Generate a synthetic social graph
# -------------------------------------------------------------------

def generate_synthetic(edge_limit: int):
    """Generate a synthetic social-network graph with a power-law-ish
    degree distribution, suitable for benchmarking.
    """
    print(f"Generating synthetic graph ({edge_limit} edges) ...")
    random.seed(42)

    # Determine node count (~1 node per 5 edges is realistic for social nets)
    num_nodes = max(edge_limit // 5, 1000)
    node_ids = list(range(1, num_nodes + 1))

    # Build edges with preferential attachment (power-law degree dist)
    edges = []
    degree = {nid: 1 for nid in node_ids}  # start with degree 1

    for _ in tqdm(range(edge_limit), desc="Edges"):
        # Weighted random source (prefer high-degree nodes)
        total_deg = sum(degree.values())
        src = random.choices(node_ids, weights=[degree[n] / total_deg for n in node_ids])[0]
        dst = random.choice(node_ids)
        while dst == src:
            dst = random.choice(node_ids)
        edges.append((str(src), str(dst), "KNOWS"))
        degree[src] = degree.get(src, 0) + 1
        degree[dst] = degree.get(dst, 0) + 1

    nodes = set(str(n) for n in node_ids)
    _save(nodes, edges)


# -------------------------------------------------------------------
# Helpers
# -------------------------------------------------------------------

def _save(nodes, edges):
    os.makedirs(PROCESSED_DIR, exist_ok=True)

    nodes_df = pd.DataFrame([{"id": n, "name": f"User_{n}"} for n in sorted(nodes, key=lambda x: int(x))])
    edges_df = pd.DataFrame(edges, columns=["source_id", "target_id", "relationship_type"])

    nodes_path = os.path.join(PROCESSED_DIR, "nodes.csv")
    edges_path = os.path.join(PROCESSED_DIR, "edges.csv")

    nodes_df.to_csv(nodes_path, index=False)
    edges_df.to_csv(edges_path, index=False)

    print(f"\nSaved {len(nodes_df):,} nodes -> {nodes_path}")
    print(f"Saved {len(edges_df):,} edges -> {edges_path}")


# -------------------------------------------------------------------
# Main
# -------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Prepare benchmark dataset")
    parser.add_argument(
        "--edges", type=int, default=DEFAULT_EDGE_LIMIT,
        help=f"Maximum number of edges (default {DEFAULT_EDGE_LIMIT})",
    )
    parser.add_argument(
        "--synthetic", action="store_true",
        help="Skip SNAP download and generate a synthetic graph directly",
    )
    args = parser.parse_args()

    # Check if dataset already exists
    nodes_path = os.path.join(PROCESSED_DIR, "nodes.csv")
    edges_path = os.path.join(PROCESSED_DIR, "edges.csv")
    if os.path.exists(nodes_path) and os.path.exists(edges_path):
        print(f"Dataset already exists at {PROCESSED_DIR}. Skipping download.")
        return

    if args.synthetic:
        generate_synthetic(args.edges)
    else:
        ok = download_snap(args.edges, timeout=60)
        if not ok:
            print("\n🔄 Falling back to synthetic graph generation ...")
            generate_synthetic(args.edges)


if __name__ == "__main__":
    main()
