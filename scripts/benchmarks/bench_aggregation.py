"""
Aggregation Benchmark: count and group-by queries (p50/p95) for all 5 platforms.

- Count: total number of User nodes.
- Group-by: top-10 nodes by outgoing relationship count (degree).
"""
import os
import sys
import json
import logging

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.stats import calculate_stats
from utils.timer import Timer

logger = logging.getLogger(__name__)

ITERATIONS = 100
WARMUP = 10


# ---------------------------------------------------------------------------
# Count query
# ---------------------------------------------------------------------------

def _cypher_count(driver):
    query = "MATCH (n:User) RETURN count(n) AS cnt"
    latencies = []
    with driver.session() as session:
        for i in range(WARMUP + ITERATIONS):
            with Timer() as t:
                result = session.run(query)
                result.consume()
            if i >= WARMUP:
                latencies.append(t.interval * 1000)
    return latencies


def _falkordb_count(graph):
    query = "MATCH (n:User) RETURN count(n) AS cnt"
    latencies = []
    for i in range(WARMUP + ITERATIONS):
        with Timer() as t:
            graph.query(query)
        if i >= WARMUP:
            latencies.append(t.interval * 1000)
    return latencies


def _arangodb_count(db):
    query = "RETURN LENGTH(Users)"
    latencies = []
    for i in range(WARMUP + ITERATIONS):
        with Timer() as t:
            cursor = db.aql.execute(query)
            list(cursor)
        if i >= WARMUP:
            latencies.append(t.interval * 1000)
    return latencies


# ---------------------------------------------------------------------------
# Group-by (degree distribution — top 10 nodes by outgoing edge count)
# ---------------------------------------------------------------------------

def _cypher_groupby(driver):
    query = """
    MATCH (n:User)-[r:KNOWS]->()
    RETURN n.id AS node_id, count(r) AS degree
    ORDER BY degree DESC LIMIT 10
    """
    latencies = []
    with driver.session() as session:
        for i in range(WARMUP + ITERATIONS):
            with Timer() as t:
                result = session.run(query)
                result.consume()
            if i >= WARMUP:
                latencies.append(t.interval * 1000)
    return latencies


def _falkordb_groupby(graph):
    query = """
    MATCH (n:User)-[r:KNOWS]->()
    RETURN n.id AS node_id, count(r) AS degree
    ORDER BY degree DESC LIMIT 10
    """
    latencies = []
    for i in range(WARMUP + ITERATIONS):
        with Timer() as t:
            graph.query(query)
        if i >= WARMUP:
            latencies.append(t.interval * 1000)
    return latencies


def _arangodb_groupby(db):
    query = """
    FOR e IN Knows
        COLLECT fromNode = e._from WITH COUNT INTO cnt
        SORT cnt DESC
        LIMIT 10
        RETURN {node: fromNode, degree: cnt}
    """
    latencies = []
    for i in range(WARMUP + ITERATIONS):
        with Timer() as t:
            cursor = db.aql.execute(query)
            list(cursor)
        if i >= WARMUP:
            latencies.append(t.interval * 1000)
    return latencies


# ---------------------------------------------------------------------------
# Main benchmark entry point
# ---------------------------------------------------------------------------

def run_benchmark(platforms, start_nodes, results_dir):
    """Run count and group-by aggregation benchmarks on all platforms."""
    os.makedirs(results_dir, exist_ok=True)
    all_results = {}

    for bench_type, runner_cypher, runner_fdb, runner_arango in [
        ("count", _cypher_count, _falkordb_count, _arangodb_count),
        ("groupby", _cypher_groupby, _falkordb_groupby, _arangodb_groupby),
    ]:
        for name, platform in platforms.items():
            key = f"{name}_{bench_type}"
            print(f"  ⏱  {bench_type} aggregation on {name}...")
            try:
                conn = platform["connection"]
                if platform["type"] == "bolt":
                    latencies = runner_cypher(conn)
                elif platform["type"] == "falkordb":
                    latencies = runner_fdb(conn)
                elif platform["type"] == "arango":
                    latencies = runner_arango(conn)
                else:
                    continue

                stats = calculate_stats(latencies)
                all_results[key] = {"platform": name, "benchmark": bench_type, **stats}
                print(f"       p50={stats['p50']:.2f}ms  p95={stats['p95']:.2f}ms")

            except Exception as e:
                logger.error(f"  {name} {bench_type} FAILED: {e}")
                all_results[key] = {
                    "platform": name,
                    "benchmark": bench_type,
                    "error": str(e),
                }
                print(f"       ❌ FAILED: {e}")

    out_path = os.path.join(results_dir, "aggregation_results.json")
    with open(out_path, "w") as f:
        json.dump(all_results, f, indent=2)
    print(f"  📄 Saved → {out_path}")

    return all_results
