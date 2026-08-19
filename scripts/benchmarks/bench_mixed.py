"""
Mixed Workload Benchmark: concurrent read/write throughput (QPS) for all 5 platforms.

Simulates a realistic workload with configurable concurrency (10/20/40 clients)
and a 70 % read / 30 % write mix sustained over a fixed duration (30 s default).

Reads  = random point lookup by id
Writes = update a random node's name property
"""
import os
import sys
import json
import time
import random
import logging
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import db_connections

logger = logging.getLogger(__name__)

DURATION_SECONDS = 30
CLIENT_COUNTS = [10, 20, 40]
READ_RATIO = 0.70  # 70 % reads, 30 % writes


# ---------------------------------------------------------------------------
# Worker functions (one per platform type)
# ---------------------------------------------------------------------------

def _bolt_worker(driver, start_nodes, stop_event, counters, lock):
    """Worker thread for Cypher-based platforms (CognoDB, Neo4j, Memgraph)."""
    read_q = "MATCH (n:User {id: $id}) RETURN n.id, n.name"
    write_q = "MATCH (n:User {id: $id}) SET n.name = $new_name"
    local_ops = 0
    while not stop_event.is_set():
        node_id = int(random.choice(start_nodes))
        try:
            with driver.session() as session:
                if random.random() < READ_RATIO:
                    session.run(read_q, id=node_id).consume()
                else:
                    new_name = f"User_{node_id}_upd"
                    session.run(write_q, id=node_id, new_name=new_name).consume()
            local_ops += 1
        except Exception:
            pass  # count only successful ops
    with lock:
        counters["ops"] += local_ops


def _falkordb_worker(graph_fn, start_nodes, stop_event, counters, lock):
    """Worker for FalkorDB. graph_fn creates a fresh graph handle per thread."""
    read_q = "MATCH (n:User {id: $id}) RETURN n.id, n.name"
    write_q = "MATCH (n:User {id: $id}) SET n.name = $new_name"
    local_ops = 0
    graph = graph_fn()  # each thread gets its own connection
    while not stop_event.is_set():
        node_id = int(random.choice(start_nodes))
        try:
            if random.random() < READ_RATIO:
                graph.query(read_q, {"id": node_id})
            else:
                graph.query(write_q, {"id": node_id, "new_name": f"User_{node_id}_upd"})
            local_ops += 1
        except Exception:
            pass
    with lock:
        counters["ops"] += local_ops


def _arango_worker(db_fn, start_nodes, stop_event, counters, lock):
    """Worker for ArangoDB. db_fn creates a fresh DB handle per thread."""
    read_q = "FOR doc IN Users FILTER doc.id == @id RETURN doc"
    write_q = """
    FOR doc IN Users FILTER doc.id == @id
        UPDATE doc WITH {name: @new_name} IN Users
    """
    local_ops = 0
    db = db_fn()
    while not stop_event.is_set():
        node_id = int(random.choice(start_nodes))
        try:
            if random.random() < READ_RATIO:
                list(db.aql.execute(read_q, bind_vars={"id": node_id}))
            else:
                list(db.aql.execute(
                    write_q,
                    bind_vars={"id": node_id, "new_name": f"User_{node_id}_upd"},
                ))
            local_ops += 1
        except Exception:
            pass
    with lock:
        counters["ops"] += local_ops


# ---------------------------------------------------------------------------
# Connection factory helpers (so each thread can get its own connection)
# ---------------------------------------------------------------------------

def _make_falkordb_factory():
    def factory():
        return db_connections.get_falkordb_graph()
    return factory


def _make_arango_factory():
    def factory():
        return db_connections.get_arangodb_db()
    return factory


# ---------------------------------------------------------------------------
# Main benchmark entry point
# ---------------------------------------------------------------------------

def run_benchmark(platforms, start_nodes, results_dir):
    """
    Run mixed-workload QPS benchmark at multiple concurrency levels.

    Returns dict keyed by "{platform}_{clients}clients" with QPS values.
    """
    os.makedirs(results_dir, exist_ok=True)
    all_results = {}

    for num_clients in CLIENT_COUNTS:
        for name, platform in platforms.items():
            key = f"{name}_{num_clients}clients"
            print(f"  ⏱  Mixed workload: {name} @ {num_clients} clients for {DURATION_SECONDS}s...")

            counters = {"ops": 0}
            lock = threading.Lock()
            stop_event = threading.Event()

            try:
                threads = []
                for _ in range(num_clients):
                    if platform["type"] == "bolt":
                        t = threading.Thread(
                            target=_bolt_worker,
                            args=(platform["connection"], start_nodes, stop_event, counters, lock),
                        )
                    elif platform["type"] == "falkordb":
                        t = threading.Thread(
                            target=_falkordb_worker,
                            args=(_make_falkordb_factory(), start_nodes, stop_event, counters, lock),
                        )
                    elif platform["type"] == "arango":
                        t = threading.Thread(
                            target=_arango_worker,
                            args=(_make_arango_factory(), start_nodes, stop_event, counters, lock),
                        )
                    else:
                        continue
                    t.daemon = True
                    threads.append(t)

                # Start all workers
                wall_start = time.perf_counter()
                for t in threads:
                    t.start()

                # Let them run for DURATION_SECONDS
                time.sleep(DURATION_SECONDS)
                stop_event.set()

                # Wait for threads to finish
                for t in threads:
                    t.join(timeout=5)

                wall_elapsed = time.perf_counter() - wall_start
                qps = counters["ops"] / wall_elapsed

                all_results[key] = {
                    "platform": name,
                    "clients": num_clients,
                    "duration_s": round(wall_elapsed, 2),
                    "total_ops": counters["ops"],
                    "qps": round(qps, 2),
                    "read_ratio": READ_RATIO,
                }
                print(f"       {counters['ops']} ops in {wall_elapsed:.1f}s → {qps:.1f} QPS")

            except Exception as e:
                logger.error(f"  {name} mixed FAILED: {e}")
                all_results[key] = {
                    "platform": name,
                    "clients": num_clients,
                    "error": str(e),
                }
                print(f"       ❌ FAILED: {e}")

    out_path = os.path.join(results_dir, "mixed_results.json")
    with open(out_path, "w") as f:
        json.dump(all_results, f, indent=2)
    print(f"  📄 Saved → {out_path}")

    return all_results
