"""
Network Overhead Benchmark: measures pure round-trip latency to CognoDB Cloud.

Runs a trivial no-op query (RETURN 1) 50 times and reports average, p50 and p95
latency. This baseline is used to contextualise CognoDB Cloud results: since the
Docker-hosted databases run locally with near-zero network latency, any raw
comparison would unfairly penalise the managed cloud service.
"""
import os
import sys
import json
import logging

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.stats import calculate_stats
from utils.timer import Timer

logger = logging.getLogger(__name__)

ITERATIONS = 50
WARMUP = 5


def run_benchmark(cognodb_driver, results_dir):
    """
    Measure network round-trip to CognoDB Cloud with a trivial query.

    Args:
        cognodb_driver: neo4j.Driver connected to the CognoDB bolt+s:// URI
        results_dir: directory to save the JSON results

    Returns:
        dict with p50, p95, mean and count
    """
    os.makedirs(results_dir, exist_ok=True)

    if cognodb_driver is None:
        print("  ⚠️  CognoDB driver not configured — skipping network overhead test.")
        return {"error": "CognoDB driver not configured"}

    print("  ⏱  Measuring network round-trip to CognoDB (RETURN 1 × 50)...")
    latencies = []

    with cognodb_driver.session() as session:
        for i in range(WARMUP + ITERATIONS):
            with Timer() as t:
                result = session.run("RETURN 1")
                result.consume()
            if i >= WARMUP:
                latencies.append(t.interval * 1000)  # ms

    stats = calculate_stats(latencies)
    results = {
        "platform": "cognodb",
        "query": "RETURN 1",
        "iterations": ITERATIONS,
        "warmup": WARMUP,
        **stats,
    }

    print(f"       avg={stats['mean']:.2f}ms  p50={stats['p50']:.2f}ms  p95={stats['p95']:.2f}ms")

    out_path = os.path.join(results_dir, "network_overhead_results.json")
    with open(out_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"  📄 Saved → {out_path}")

    return results
