import os
import sys
import time
import pandas as pd

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import db_connections

BATCH_SIZE = 1000

def load_data(graph, nodes_path: str, edges_path: str):
    print(f"Loading data into FalkorDB from {nodes_path} and {edges_path}")
    
    df_nodes = pd.read_csv(nodes_path)
    nodes = df_nodes.to_dict('records')
    
    start_time = time.time()
    
    # Clear graph
    graph.delete()
    
    node_query = """
    UNWIND $batch AS row
    CREATE (n:User {id: toInteger(row.id), name: row.name})
    """
    
    for i in range(0, len(nodes), BATCH_SIZE):
        batch = nodes[i:i+BATCH_SIZE]
        graph.query(node_query, {"batch": batch})
        
    try:
        graph.query("CREATE INDEX ON :User(id)")
    except Exception:
        pass

    df_edges = pd.read_csv(edges_path)
    edges = df_edges.to_dict('records')
    
    edge_query = """
    UNWIND $batch AS row
    MATCH (src:User {id: toInteger(row.source_id)})
    MATCH (dst:User {id: toInteger(row.target_id)})
    CREATE (src)-[:KNOWS]->(dst)
    """
    
    for i in range(0, len(edges), BATCH_SIZE):
        batch = edges[i:i+BATCH_SIZE]
        graph.query(edge_query, {"batch": batch})
            
    end_time = time.time()
    total_time = end_time - start_time
    
    nodes_sec = len(nodes) / total_time
    edges_sec = len(edges) / total_time
    
    print(f"FalkorDB Load complete in {total_time:.2f}s")
    print(f"Nodes/sec: {nodes_sec:.2f}, Relationships/sec: {edges_sec:.2f}")

if __name__ == "__main__":
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    nodes_csv = os.path.join(base_dir, "data", "processed", "nodes.csv")
    edges_csv = os.path.join(base_dir, "data", "processed", "edges.csv")
    
    graph = db_connections.get_falkordb_graph()
    if graph:
        load_data(graph, nodes_csv, edges_csv)
    else:
        print("FalkorDB driver not configured.")
