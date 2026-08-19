import numpy as np

def calculate_stats(latencies):
    if not latencies:
        return {"p50": 0.0, "p95": 0.0, "mean": 0.0, "count": 0}
    return {
        "p50": np.percentile(latencies, 50),
        "p95": np.percentile(latencies, 95),
        "mean": np.mean(latencies),
        "count": len(latencies)
    }
