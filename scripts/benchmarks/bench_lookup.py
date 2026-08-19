"""
Lookup Benchmark: point lookup by ID and filtered lookup (p50/p95) for all 5 platforms.

- Point lookup: fetch a single node by its indexed `id` property.
- Filtered lookup: find nodes whose `name` starts with a given prefix (LIMIT 10).
"""
import os
import sys
import json
import random
import logging

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.stats import calculate_stats
from utils.timer import Timer

logger = logging.getLogger(__name__)

ITERATIONS = 100
WARMUP = 10


# ---------------------------------------------------------------------------
# Point lookup
# ---------------------------------------------------------------------------

def _cypher_point_lookup(driver, start_nodes):
    query = "MATCH (n:User {id: $id}) RETURN n.id, n.name"
    latencies = []
    with driver.session() as session:
        for i in range(WARMUP + ITERATIONS):
            node_id = int(random.choice(start_nodes))
            with Timer() as t:
                result = session.run(query, id=node_id)
                result.consume()
            if i >= WARMUP:
                latencies.append(t.interval * 1000)
    return latencies


def _falkordb_point_lookup(graph, start_nodes):
    query = "MATCH (n:User {id: $id}) RETURN n.id, n.name"
    latencies = []
    for i in range(WARMUP + ITERATIONS):
        node_id = int(random.choice(start_nodes))
        with Timer() as t:
            graph.query(query, {"id": node_id})
        if i >= WARMUP:
            latencies.append(t.interval * 1000)
    return latencies


def _arangodb_point_lookup(db, start_nodes):
    query = "FOR doc IN Users FILTER doc.id == @id RETURN {id: doc.id, name: doc.name}"
    latencies = []
    for i in range(WARMUP + ITERATIONS):
        node_id = int(random.choice(start_nodes))
        with Timer() as t:
            cursor = db.aql.execute(query, bind_vars={"id": node_id})
            list(cursor)
        if i >= WARMUP:
            latencies.append(t.interval * 1000)
    return latencies


# ---------------------------------------------------------------------------
# Filtered lookup (name prefix search)
# ---------------------------------------------------------------------------

def _cypher_filtered_lookup(driver, prefixes):
    query = "MATCH (n:User) WHERE n.name STARTS WITH $prefix RETURN n.id, n.name LIMIT 10"
    latencies = []
    with driver.session() as session:
        for i in range(WARMUP + ITERATIONS):
            prefix = random.choice(prefixes)
            with Timer() as t:
                result = session.run(query, prefix=prefix)
                result.consume()
            if i >= WARMUP:
                latencies.append(t.interval * 1000)
    return latencies


def _falkordb_filtered_lookup(graph, prefixes):
    query = "MATCH (n:User) WHERE n.name STARTS WITH $prefix RETURN n.id, n.name LIMIT 10"
    latencies = []
    for i in range(WARMUP + ITERATIONS):
        prefix = random.choice(prefixes)
        with Timer() as t:
            graph.query(query, {"prefix": prefix})
        if i >= WARMUP:
            latencies.append(t.interval * 1000)
    return latencies


def _arangodb_filtered_lookup(db, prefixes):
    query = """
    FOR doc IN Users
        FILTER STARTS_WITH(doc.name, @prefix)
        LIMIT 10
        RETURN {id: doc.id, name: doc.name}
    """
    latencies = []
    for i in range(WARMUP + ITERATIONS):
        prefix = random.choice(prefixes)
        with Timer() as t:
            cursor = db.aql.execute(query, bind_vars={"prefix": prefix})
            list(cursor)
        if i >= WARMUP:
            latencies.append(t.interval * 1000)
    return latencies


# ---------------------------------------------------------------------------
# Main benchmark entry point
# ---------------------------------------------------------------------------

def run_benchmark(platforms, start_nodes, results_dir):
    """
    Run lookup benchmarks (point + filtered) on all platforms.

    Indexed property: User.id (all platforms create an index on this).
    Filtered property: User.name (prefix search, not indexed — tests scan perf).
    """
    os.makedirs(results_dir, exist_ok=True)
    all_results = {}

    # Generate some name prefixes for filtered lookup
    prefixes = [f"User_{random.choice(start_nodes)}"[:8] for _ in range(50)]

    for bench_type, runner_cypher, runner_fdb, runner_arango, args_fn in [
        (
            "point_lookup",
            _cypher_point_lookup,
            _falkordb_point_lookup,
            _arangodb_point_lookup,
            lambda: (start_nodes,),
        ),
        (
            "filtered_lookup",
            _cypher_filtered_lookup,
            _falkordb_filtered_lookup,
            _arangodb_filtered_lookup,
            lambda: (prefixes,),
        ),
    ]:
        for name, platform in platforms.items():
            key = f"{name}_{bench_type}"
            print(f"  ⏱  {bench_type} on {name}...")
            try:
                args = args_fn()
                if platform["type"] == "bolt":
                    latencies = runner_cypher(platform["connection"], *args)
                elif platform["type"] == "falkordb":
                    latencies = runner_fdb(platform["connection"], *args)
                elif platform["type"] == "arango":
                    latencies = runner_arango(platform["connection"], *args)
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

    out_path = os.path.join(results_dir, "lookup_results.json")
    with open(out_path, "w") as f:
        json.dump(all_results, f, indent=2)
    print(f"  📄 Saved → {out_path}")

    return all_results
