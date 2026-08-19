import os
import sys
import time
import pandas as pd

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import db_connections

BATCH_SIZE = 1000

def load_data(db, nodes_path: str, edges_path: str):
    print(f"Loading data into ArangoDB from {nodes_path} and {edges_path}")
    
    df_nodes = pd.read_csv(nodes_path)
    nodes = df_nodes.to_dict('records')
    
    start_time = time.time()
    
    if db.has_collection('Users'):
        db.delete_collection('Users')
    users = db.create_collection('Users')
    
    if db.has_collection('Knows'):
        db.delete_collection('Knows')
    knows = db.create_collection('Knows', edge=True)
    
    arango_nodes = []
    for n in nodes:
        arango_nodes.append({
            "_key": str(n["id"]),
            "id": int(n["id"]),
            "name": n["name"]
        })
        
    for i in range(0, len(arango_nodes), BATCH_SIZE):
        batch = arango_nodes[i:i+BATCH_SIZE]
        users.insert_many(batch)
        
    df_edges = pd.read_csv(edges_path)
    edges = df_edges.to_dict('records')
    
    arango_edges = []
    for e in edges:
        arango_edges.append({
            "_from": f"Users/{e['source_id']}",
            "_to": f"Users/{e['target_id']}",
            "type": e["relationship_type"]
        })
        
    for i in range(0, len(arango_edges), BATCH_SIZE):
        batch = arango_edges[i:i+BATCH_SIZE]
        knows.insert_many(batch)

    end_time = time.time()
    total_time = end_time - start_time
    
    nodes_sec = len(nodes) / total_time
    edges_sec = len(edges) / total_time
    
    print(f"ArangoDB Load complete in {total_time:.2f}s")
    print(f"Nodes/sec: {nodes_sec:.2f}, Relationships/sec: {edges_sec:.2f}")

if __name__ == "__main__":
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    nodes_csv = os.path.join(base_dir, "data", "processed", "nodes.csv")
    edges_csv = os.path.join(base_dir, "data", "processed", "edges.csv")
    
    db = db_connections.get_arangodb_db()
    if db:
        load_data(db, nodes_csv, edges_csv)
    else:
        print("ArangoDB driver not configured.")
