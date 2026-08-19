import os
import sys
import time
import pandas as pd

# Add the parent directory to the path so we can import db_connections
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import db_connections

BATCH_SIZE = 1000

def load_data(driver, nodes_path: str, edges_path: str):
    print(f"Loading data into CognoDB from {nodes_path} and {edges_path}")
    
    df_nodes = pd.read_csv(nodes_path)
    nodes = df_nodes.to_dict('records')
    
    start_time = time.time()
    
    with driver.session() as session:
        # Clear existing data
        session.run("MATCH (n) DETACH DELETE n")
        
        node_query = """
        UNWIND $batch AS row
        CREATE (n:User {id: toInteger(row.id), name: row.name})
        """
        
        for i in range(0, len(nodes), BATCH_SIZE):
            batch = nodes[i:i+BATCH_SIZE]
            session.run(node_query, batch=batch)
            
        # Try creating index
        try:
            session.run("CREATE INDEX user_id_index FOR (n:User) ON (n.id)")
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
            session.run(edge_query, batch=batch)
            
    end_time = time.time()
    total_time = end_time - start_time
    
    nodes_sec = len(nodes) / total_time
    edges_sec = len(edges) / total_time
    
    print(f"CognoDB Load complete in {total_time:.2f}s")
    print(f"Nodes/sec: {nodes_sec:.2f}, Relationships/sec: {edges_sec:.2f}")

if __name__ == "__main__":
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    nodes_csv = os.path.join(base_dir, "data", "processed", "nodes.csv")
    edges_csv = os.path.join(base_dir, "data", "processed", "edges.csv")
    
    driver = db_connections.get_cognodb_driver()
    if driver:
        try:
            load_data(driver, nodes_csv, edges_csv)
        finally:
            driver.close()
    else:
        print("CognoDB driver not configured.")
