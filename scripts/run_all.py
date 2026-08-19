#!/usr/bin/env python3
"""
run_all.py — Main orchestrator for the CognoDB Graph Benchmark suite.

Usage:
    python scripts/run_all.py               # full run: load + benchmark
    python scripts/run_all.py --skip-load   # skip data loading, run benchmarks only

Pipeline:
    1. Load the dataset into all 5 databases (unless --skip-load)
    2. Run traversal, lookup, aggregation, mixed and network-overhead benchmarks
    3. Aggregate raw results into a summary JSON
    4. Print a summary table
"""
import os
import sys
import json
import time
import argparse
import logging
import pandas as pd
import glob
import shutil

# ---------------------------------------------------------------------------
# Path setup — make all project modules importable
# ---------------------------------------------------------------------------
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(SCRIPT_DIR)
sys.path.insert(0, SCRIPT_DIR)

import db_connections
from loaders import load_cognodb, load_neo4j, load_memgraph, load_arangodb, load_falkordb
from benchmarks import (
    bench_traversal,
    bench_lookup,
    bench_aggregation,
    bench_mixed,
    bench_network_overhead,
)

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("run_all")

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
NODES_CSV = os.path.join(BASE_DIR, "data", "processed", "nodes.csv")
EDGES_CSV = os.path.join(BASE_DIR, "data", "processed", "edges.csv")
RAW_DIR = os.path.join(BASE_DIR, "results", "raw")
SUMMARY_DIR = os.path.join(BASE_DIR, "results", "summary")


def _get_start_nodes():
    """Read node IDs from the processed CSV for benchmark sampling."""
    df = pd.read_csv(NODES_CSV)
    return df["id"].tolist()

def clean_old_results():
    """Remove old benchmark results and charts to ensure a clean run."""
    print("🧹 Cleaning up old results and charts...")
    
    # Remove old raw and summary JSONs
    for path in [RAW_DIR, SUMMARY_DIR]:
        if os.path.exists(path):
            for f in glob.glob(os.path.join(path, "*.json")):
                try:
                    os.remove(f)
                except Exception as e:
                    logger.warning(f"Could not delete {f}: {e}")
                    
    # Remove old charts
    charts_dir = os.path.join(BASE_DIR, "charts")
    if os.path.exists(charts_dir):
        for f in glob.glob(os.path.join(charts_dir, "*.png")):
            try:
                os.remove(f)
            except Exception as e:
                logger.warning(f"Could not delete {f}: {e}")


# ===================================================================
# 1. DATA LOADING
# ===================================================================

def run_load_phase():
    """Load the dataset into every platform, collecting ingest metrics."""
    print("\n" + "=" * 60)
    print("  PHASE 1 — DATA LOADING")
    print("=" * 60)

    load_results = {}

    # --- CognoDB ---
    print("\n📦 Loading CognoDB...")
    driver = None
    try:
        driver = db_connections.get_cognodb_driver()
        if driver:
            load_cognodb.load_data(driver, NODES_CSV, EDGES_CSV)
            load_results["cognodb"] = {"status": "ok"}
        else:
            print("  ⚠️  CognoDB not configured — skipped")
            load_results["cognodb"] = {"status": "skipped"}
    except Exception as e:
        logger.error(f"CognoDB load failed: {e}")
        load_results["cognodb"] = {"status": "error", "error": str(e)}
    finally:
        if driver:
            driver.close()

    # --- Neo4j ---
    print("\n📦 Loading Neo4j...")
    driver = None
    try:
        driver = db_connections.get_neo4j_driver()
        load_neo4j.load_data(driver, NODES_CSV, EDGES_CSV)
        load_results["neo4j"] = {"status": "ok"}
    except Exception as e:
        logger.error(f"Neo4j load failed: {e}")
        load_results["neo4j"] = {"status": "error", "error": str(e)}
    finally:
        if driver:
            driver.close()

    # --- Memgraph ---
    print("\n📦 Loading Memgraph...")
    driver = None
    try:
        driver = db_connections.get_memgraph_driver()
        load_memgraph.load_data(driver, NODES_CSV, EDGES_CSV)
        load_results["memgraph"] = {"status": "ok"}
    except Exception as e:
        logger.error(f"Memgraph load failed: {e}")
        load_results["memgraph"] = {"status": "error", "error": str(e)}
    finally:
        if driver:
            driver.close()

    # --- ArangoDB ---
    print("\n📦 Loading ArangoDB...")
    try:
        adb = db_connections.get_arangodb_db()
        load_arangodb.load_data(adb, NODES_CSV, EDGES_CSV)
        load_results["arangodb"] = {"status": "ok"}
    except Exception as e:
        logger.error(f"ArangoDB load failed: {e}")
        load_results["arangodb"] = {"status": "error", "error": str(e)}

    # --- FalkorDB ---
    print("\n📦 Loading FalkorDB...")
    try:
        graph = db_connections.get_falkordb_graph()
        load_falkordb.load_data(graph, NODES_CSV, EDGES_CSV)
        load_results["falkordb"] = {"status": "ok"}
    except Exception as e:
        logger.error(f"FalkorDB load failed: {e}")
        load_results["falkordb"] = {"status": "error", "error": str(e)}

    return load_results


# ===================================================================
# 2. BENCHMARKS
# ===================================================================

def _build_platforms():
    """Create a dict of platform connections for the benchmark runners."""
    platforms = {}

    # Bolt-protocol databases
    for name, getter in [
        ("cognodb", db_connections.get_cognodb_driver),
        ("neo4j", db_connections.get_neo4j_driver),
        ("memgraph", db_connections.get_memgraph_driver),
    ]:
        try:
            drv = getter()
            if drv is not None:
                platforms[name] = {"type": "bolt", "connection": drv}
        except Exception as e:
            logger.warning(f"Could not connect to {name}: {e}")

    # ArangoDB
    try:
        adb = db_connections.get_arangodb_db()
        platforms["arangodb"] = {"type": "arango", "connection": adb}
    except Exception as e:
        logger.warning(f"Could not connect to ArangoDB: {e}")

    # FalkorDB
    try:
        graph = db_connections.get_falkordb_graph()
        platforms["falkordb"] = {"type": "falkordb", "connection": graph}
    except Exception as e:
        logger.warning(f"Could not connect to FalkorDB: {e}")

    return platforms


def run_benchmark_phase(start_nodes):
    """Run every benchmark category on every available platform."""
    print("\n" + "=" * 60)
    print("  PHASE 2 — BENCHMARKS")
    print("=" * 60)

    os.makedirs(RAW_DIR, exist_ok=True)

    platforms = _build_platforms()
    print(f"\n  Connected platforms: {list(platforms.keys())}\n")

    all_results = {}

    # --- Traversal ---
    print("\n🔗 Traversal Benchmark (1-hop / 2-hop / 3-hop)")
    print("-" * 50)
    all_results["traversal"] = bench_traversal.run_benchmark(platforms, start_nodes, RAW_DIR)

    # --- Lookup ---
    print("\n🔍 Lookup Benchmark (point / filtered)")
    print("-" * 50)
    all_results["lookup"] = bench_lookup.run_benchmark(platforms, start_nodes, RAW_DIR)

    # --- Aggregation ---
    print("\n📊 Aggregation Benchmark (count / group-by)")
    print("-" * 50)
    all_results["aggregation"] = bench_aggregation.run_benchmark(platforms, start_nodes, RAW_DIR)

    # --- Mixed Workload ---
    print("\n⚡ Mixed Workload Benchmark (concurrent read/write)")
    print("-" * 50)
    all_results["mixed"] = bench_mixed.run_benchmark(platforms, start_nodes, RAW_DIR)

    # --- Network Overhead (CognoDB only) ---
    print("\n🌐 Network Overhead Baseline (CognoDB)")
    print("-" * 50)
    cognodb_driver = platforms.get("cognodb", {}).get("connection")
    all_results["network_overhead"] = bench_network_overhead.run_benchmark(cognodb_driver, RAW_DIR)

    # Close bolt drivers
    for name, p in platforms.items():
        if p["type"] == "bolt":
            try:
                p["connection"].close()
            except Exception:
                pass

    return all_results


# ===================================================================
# 3. SUMMARY
# ===================================================================

def write_summary(all_results):
    """Aggregate raw results into a summary JSON in results/summary/."""
    os.makedirs(SUMMARY_DIR, exist_ok=True)
    summary_path = os.path.join(SUMMARY_DIR, "benchmark_summary.json")
    with open(summary_path, "w") as f:
        json.dump(all_results, f, indent=2)
    print(f"\n✅ Summary saved → {summary_path}")


# ===================================================================
# MAIN
# ===================================================================

class LoggerWriter:
    def __init__(self, filename):
        self.terminal = sys.stdout
        self.log = open(filename, "a", encoding="utf-8")
        
    def write(self, message):
        self.terminal.write(message)
        self.log.write(message)
        self.log.flush()
        
    def flush(self):
        self.terminal.flush()
        self.log.flush()

def main():
    parser = argparse.ArgumentParser(description="CognoDB Graph Benchmark Suite")
    parser.add_argument(
        "--skip-load",
        action="store_true",
        help="Skip the data-loading phase (data must already be loaded into all DBs)",
    )
    args = parser.parse_args()

    sys.stdout = LoggerWriter("logs.txt")
    sys.stderr = sys.stdout

    print("╔══════════════════════════════════════════════════════════╗")
    print("║       CognoDB Graph Database Benchmark Suite            ║")
    print("╚══════════════════════════════════════════════════════════╝")

    overall_start = time.time()
    
    # Clean up old results before starting
    clean_old_results()

    # Verify dataset exists
    if not os.path.exists(NODES_CSV) or not os.path.exists(EDGES_CSV):
        print(f"\n❌ Dataset not found at {NODES_CSV}")
        print("   Run 'python scripts/download_dataset.py' first.")
        sys.exit(1)

    start_nodes = _get_start_nodes()
    print(f"\n  Dataset: {len(start_nodes)} nodes loaded from CSV")

    # Phase 1: Load
    if args.skip_load:
        print("\n  ⏭  --skip-load: skipping data loading phase")
    else:
        run_load_phase()

    # Phase 2: Benchmark
    all_results = run_benchmark_phase(start_nodes)

    # Phase 3: Summary
    write_summary(all_results)

    elapsed = time.time() - overall_start
    print(f"\n🏁 All done in {elapsed:.1f}s")


if __name__ == "__main__":
    main()
