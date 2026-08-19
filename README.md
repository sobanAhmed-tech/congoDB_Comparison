# CognoDB Cloud — Graph Database Benchmark

> **A reproducible, automated benchmark comparing [CognoDB Cloud](https://cognodb.com) against four self-hosted graph databases on the same dataset, same queries, and same resource limits.**

---

## Table of Contents

1. [Overview](#overview)
2. [Databases Under Test](#databases-under-test)
3. [Methodology](#methodology)
4. [Setup & Reproduction](#setup--reproduction)
5. [Dataset](#dataset)
6. [Results](#results)
   - [Data Loading](#data-loading)
   - [Traversals (1 / 2 / 3-hop)](#traversals)
   - [Lookups (Point / Filtered)](#lookups)
   - [Aggregations (Count / Group-By)](#aggregations)
   - [Mixed Workload (QPS)](#mixed-workload)
   - [Network Overhead Baseline](#network-overhead-baseline)
   - [Resource Footprint](#resource-footprint)
7. [Charts](#charts)
8. [Analysis](#analysis)
9. [Caveats](#caveats)

---

## Overview

This repository contains a fully scripted benchmark suite that loads a public social-network graph into five graph databases and measures:

| Category | Metric |
|---|---|
| **Data loading** | Nodes/s, Relationships/s, wall-clock time |
| **Traversals** | 1-hop, 2-hop, 3-hop latency (p50 / p95) |
| **Lookups** | Point lookup and filtered/prefix lookup (p50 / p95) |
| **Aggregations** | Node count and top-10 degree group-by (p50 / p95) |
| **Mixed workload** | Sustained QPS at 10 / 20 / 40 concurrent clients (70 % read / 30 % write) |
| **Network overhead** | CognoDB round-trip baseline (RETURN 1 × 50) |

Every benchmark is run ≥ 100 iterations (after warm-up), with latency percentiles computed from the raw data.

---

## Databases Under Test

| # | Database | Deployment | Protocol | Recommended Free Tier Limits |
|---|---|---|---|---|
| 1 | **CognoDB Cloud** (c0 free tier) | Managed cloud | Bolt (`bolt+s://`) | 0.5 vCPU, 256 MB RAM, 1 GB disk |
| 2 | **Neo4j Aura** | Managed cloud | Bolt (`neo4j+s://`) | Similar to Aura Free |
| 3 | **Memgraph Cloud** | Managed cloud | Bolt (`bolt+s://`) | Sandbox/Trial specs |
| 4 | **ArangoDB Cloud** | Managed cloud | HTTP + AQL | Oasis free tier |
| 5 | **FalkorDB Cloud** | Managed cloud | Redis protocol + Cypher | Free tier specs |

*Note: All databases should ideally be provisioned on their respective free cloud tiers to ensure a fair resource-constrained comparison.*

---

## Methodology

### Fairness

* **Fairness via Cloud Free Tiers.** All databases are tested using their managed cloud free tiers (where available) to compare out-of-the-box cloud performance.
* **Same dataset, same logical queries.** The exact same `nodes.csv` / `edges.csv` are loaded into every platform. Cypher and AQL queries are logically equivalent.
* **Same client machine.** All benchmarks are driven from the same host.

### Warm-up & Measurement

* Each benchmark performs a warm-up pass (10 iterations) whose results are discarded.
* The subsequent 100 measured iterations are used to compute p50 and p95 latency.

### Concurrency

* The mixed workload benchmark uses Python `threading` with 10, 20, and 40 concurrent worker threads performing a 70 % read / 30 % write mix for 30 seconds each.

---

## Setup & Reproduction

### Prerequisites

* **Python 3.10+**
* Cloud database credentials for all platforms

### Steps

```bash
# 1. Clone the repository
git clone https://github.com/<your-username>/cognodb-graph-benchmark.git
cd cognodb-graph-benchmark

# 2. Create a Python virtual environment and install dependencies
python -m venv venv
source venv/bin/activate        # Linux/macOS
# .\venv\Scripts\Activate.ps1   # Windows PowerShell
pip install -r requirements.txt

# 3. Configure credentials
cp .env.example .env
# Edit .env and fill in your connection URIs, usernames, and passwords for ALL cloud platforms.

# 4. Download and prepare the dataset
python scripts/download_dataset.py

# 5. Run the full benchmark suite
python scripts/run_all.py

# 6. Generate charts
python charts/generate_charts.py
```

Use `--skip-load` to skip the data loading phase if data is already loaded:

```bash
python scripts/run_all.py --skip-load
```

---

## Dataset

| Property | Value |
|---|---|
| **Source** | [SNAP soc-Pokec](https://snap.stanford.edu/data/soc-Pokec.html) |
| **Description** | Anonymised social network from a Slovak social network |
| **Nodes** | _TBD after run_ |
| **Relationships** | _TBD after run_ (target: 100 k–500 k) |
| **Node label** | `User` (properties: `id`, `name`) |
| **Relationship type** | `KNOWS` (directed) |

The raw dataset is downloaded and processed into `data/processed/nodes.csv` and `data/processed/edges.csv`.

---

## Results

> **Note:** The tables below will be populated after running the benchmark suite. Run `python scripts/run_all.py` and fill in the numbers.

### Data Loading

| Platform | Nodes/s | Rels/s | Wall-clock (s) |
|---|---|---|---|
| CognoDB | _TBD_ | _TBD_ | _TBD_ |
| Neo4j | _TBD_ | _TBD_ | _TBD_ |
| Memgraph | _TBD_ | _TBD_ | _TBD_ |
| ArangoDB | _TBD_ | _TBD_ | _TBD_ |
| FalkorDB | _TBD_ | _TBD_ | _TBD_ |

### Traversals

| Platform | 1-hop p50 (ms) | 1-hop p95 (ms) | 2-hop p50 | 2-hop p95 | 3-hop p50 | 3-hop p95 |
|---|---|---|---|---|---|---|
| CognoDB | _TBD_ | _TBD_ | _TBD_ | _TBD_ | _TBD_ | _TBD_ |
| Neo4j | _TBD_ | _TBD_ | _TBD_ | _TBD_ | _TBD_ | _TBD_ |
| Memgraph | _TBD_ | _TBD_ | _TBD_ | _TBD_ | _TBD_ | _TBD_ |
| ArangoDB | _TBD_ | _TBD_ | _TBD_ | _TBD_ | _TBD_ | _TBD_ |
| FalkorDB | _TBD_ | _TBD_ | _TBD_ | _TBD_ | _TBD_ | _TBD_ |

### Lookups

| Platform | Point p50 (ms) | Point p95 (ms) | Filtered p50 | Filtered p95 |
|---|---|---|---|---|
| CognoDB | _TBD_ | _TBD_ | _TBD_ | _TBD_ |
| Neo4j | _TBD_ | _TBD_ | _TBD_ | _TBD_ |
| Memgraph | _TBD_ | _TBD_ | _TBD_ | _TBD_ |
| ArangoDB | _TBD_ | _TBD_ | _TBD_ | _TBD_ |
| FalkorDB | _TBD_ | _TBD_ | _TBD_ | _TBD_ |

**Indexed properties:** `User.id` is indexed on all platforms. `User.name` is not indexed (used for filtered scan benchmark).

### Aggregations

| Platform | Count p50 (ms) | Count p95 (ms) | Group-by p50 | Group-by p95 |
|---|---|---|---|---|
| CognoDB | _TBD_ | _TBD_ | _TBD_ | _TBD_ |
| Neo4j | _TBD_ | _TBD_ | _TBD_ | _TBD_ |
| Memgraph | _TBD_ | _TBD_ | _TBD_ | _TBD_ |
| ArangoDB | _TBD_ | _TBD_ | _TBD_ | _TBD_ |
| FalkorDB | _TBD_ | _TBD_ | _TBD_ | _TBD_ |

### Mixed Workload

| Platform | 10 clients (QPS) | 20 clients (QPS) | 40 clients (QPS) |
|---|---|---|---|
| CognoDB | _TBD_ | _TBD_ | _TBD_ |
| Neo4j | _TBD_ | _TBD_ | _TBD_ |
| Memgraph | _TBD_ | _TBD_ | _TBD_ |
| ArangoDB | _TBD_ | _TBD_ | _TBD_ |
| FalkorDB | _TBD_ | _TBD_ | _TBD_ |

Mix: 70 % reads (point lookup) / 30 % writes (property update). Duration: 30 seconds per concurrency level.

### Network Overhead Baseline

| Metric | Value |
|---|---|
| Query | `RETURN 1` |
| Iterations | 50 (after 5 warm-up) |
| Average RTT | _TBD_ ms |
| p50 | _TBD_ ms |
| p95 | _TBD_ ms |

This measures the pure network round-trip from the benchmark host to the CognoDB Cloud endpoint. Note that since all databases are now tested in the cloud, network latency applies fairly to all of them.

### Resource Footprint

| Platform | Instance Specs | Observed Memory | Stored Data Size |
|---|---|---|---|
| CognoDB | 0.5 vCPU, 256 MB, 1 GB disk | Managed | _TBD_ |
| Neo4j | Cloud Free Tier | Managed | _TBD_ |
| Memgraph | Cloud Free Tier | Managed | _TBD_ |
| ArangoDB | Cloud Free Tier | Managed | _TBD_ |
| FalkorDB | Cloud Free Tier | Managed | _TBD_ |

---

## Charts

After running `python charts/generate_charts.py`, PNG charts are saved in `charts/`:

- `traversal_1hop.png` / `traversal_2hop.png` / `traversal_3hop.png`
- `point_lookup.png` / `filtered_lookup.png`
- `aggregation_count.png` / `aggregation_groupby.png`
- `mixed_qps_10clients.png` / `mixed_qps_20clients.png` / `mixed_qps_40clients.png`

---

## Analysis

_To be written after results are collected._

Key areas to address:
- Which platforms excel at traversal vs. point lookup vs. aggregation?
- How does concurrency scaling compare?
- How much of CognoDB's latency is attributable to network overhead vs. query processing?
- Where do the free-tier resource constraints become the bottleneck?

---

## Caveats

1. **Network latency.** All databases are tested as managed cloud services. Network latency heavily depends on the geographic region of the provisioned cluster relative to the machine running the benchmark.
2. **Free-tier throttling.** Managed platforms may apply rate limits or burstable CPU throttling on free tiers that are not visible to the benchmark client.
3. **Query language differences.** Neo4j, Memgraph, CognoDB and FalkorDB use Cypher; ArangoDB uses AQL. Queries are logically equivalent but syntactically different, which may affect query planning.
4. **Single client machine.** All benchmarks are driven from a single host. Network conditions, CPU contention and OS scheduling can introduce variance between runs.

6. **Python GIL.** The mixed-workload benchmark uses `threading`, which is subject to the Python Global Interpreter Lock. True parallelism requires multiprocessing or async I/O; threading is used here because the workload is I/O-bound (network calls).

---

## License

MIT
