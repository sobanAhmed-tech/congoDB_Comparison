"""
Traversal Benchmark: 1-hop, 2-hop, 3-hop latency (p50/p95) for all 5 platforms.

Measures the time to traverse the graph from a random start node at depths 1, 2 and 3.
Uses WARMUP iterations (discarded) followed by ITERATIONS measured iterations.
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
# Per-platform traversal runners
# ---------------------------------------------------------------------------

def _run_cypher_traversal(driver, start_nodes, hop_depth):
    """Run traversal on Cypher-based DBs (CognoDB, Neo4j, Memgraph)."""
    query = f"MATCH (n:User {{id: $id}})-[:KNOWS*1..{hop_depth}]->(friend) RETURN count(friend) AS cnt"
    latencies = []
    with driver.session() as session:
        for i in range(WARMUP + ITERATIONS):
            node_id = int(random.choice(start_nodes))
            with Timer() as t:
                result = session.run(query, id=node_id)
                result.consume()
            if i >= WARMUP:
                latencies.append(t.interval * 1000)  # ms
    return latencies


def _run_falkordb_traversal(graph, start_nodes, hop_depth):
    """Run traversal on FalkorDB (openCypher via its own client)."""
    query = f"MATCH (n:User {{id: $id}})-[:KNOWS*1..{hop_depth}]->(friend) RETURN count(friend) AS cnt"
    latencies = []
    for i in range(WARMUP + ITERATIONS):
        node_id = int(random.choice(start_nodes))
        with Timer() as t:
            graph.query(query, {"id": node_id})
        if i >= WARMUP:
            latencies.append(t.interval * 1000)
    return latencies


def _run_arangodb_traversal(db, start_nodes, hop_depth):
    """Run traversal on ArangoDB using AQL graph traversal."""
    query = """
    FOR v IN 1..@depth OUTBOUND CONCAT('Users/', @id) Knows
        COLLECT WITH COUNT INTO cnt
        RETURN cnt
    """
    latencies = []
    for i in range(WARMUP + ITERATIONS):
        node_id = str(random.choice(start_nodes))
        with Timer() as t:
            cursor = db.aql.execute(query, bind_vars={"id": node_id, "depth": hop_depth})
            list(cursor)  # consume the cursor
        if i >= WARMUP:
            latencies.append(t.interval * 1000)
    return latencies


# ---------------------------------------------------------------------------
# Main benchmark entry point
# ---------------------------------------------------------------------------

def run_benchmark(platforms, start_nodes, results_dir):
    """
    Run traversal benchmark across all platforms and hop depths.

    Args:
        platforms: dict {name: {"type": "bolt"|"falkordb"|"arango", "connection": obj}}
        start_nodes: list of integer node IDs to sample from
        results_dir: directory to write raw JSON results

    Returns:
        dict keyed by "{platform}_{depth}hop" with stats
    """
    os.makedirs(results_dir, exist_ok=True)
    all_results = {}

    for hop_depth in [1, 2, 3]:
        for name, platform in platforms.items():
            key = f"{name}_{hop_depth}hop"
            print(f"  ⏱  {hop_depth}-hop traversal on {name}...")
            try:
                if platform["type"] == "bolt":
                    latencies = _run_cypher_traversal(
                        platform["connection"], start_nodes, hop_depth
                    )
                elif platform["type"] == "falkordb":
                    latencies = _run_falkordb_traversal(
                        platform["connection"], start_nodes, hop_depth
                    )
                elif platform["type"] == "arango":
                    latencies = _run_arangodb_traversal(
                        platform["connection"], start_nodes, hop_depth
                    )
                else:
                    logger.warning(f"Unknown platform type: {platform['type']}")
                    continue

                stats = calculate_stats(latencies)
                all_results[key] = {
                    "platform": name,
                    "hop_depth": hop_depth,
                    **stats,
                }
                print(f"       p50={stats['p50']:.2f}ms  p95={stats['p95']:.2f}ms")

            except Exception as e:
                logger.error(f"  {name} {hop_depth}-hop FAILED: {e}")
                all_results[key] = {
                    "platform": name,
                    "hop_depth": hop_depth,
                    "error": str(e),
                }
                print(f"       ❌ FAILED: {e}")

    # Persist raw results (without the large latency arrays)
    out_path = os.path.join(results_dir, "traversal_results.json")
    with open(out_path, "w") as f:
        json.dump(all_results, f, indent=2)
    print(f"  📄 Saved → {out_path}")

    return all_results
