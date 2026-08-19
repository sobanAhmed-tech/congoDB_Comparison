import os
from neo4j import GraphDatabase
from arango import ArangoClient
from falkordb import FalkorDB
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

def get_cognodb_driver():
    uri = os.environ.get("COGNODB_URI")
    user = os.environ.get("COGNODB_USER")
    password = os.environ.get("COGNODB_PASSWORD")
    if not uri:
        return None
    return GraphDatabase.driver(uri, auth=(user, password))

def get_neo4j_driver():
    uri = os.environ.get("NEO4J_URI")
    user = os.environ.get("NEO4J_USER")
    password = os.environ.get("NEO4J_PASSWORD")
    if not uri: return None
    return GraphDatabase.driver(uri, auth=(user, password))

def get_memgraph_driver():
    uri = os.environ.get("MEMGRAPH_URI")
    user = os.environ.get("MEMGRAPH_USER")
    password = os.environ.get("MEMGRAPH_PASSWORD")
    if not uri: return None
    return GraphDatabase.driver(uri, auth=(user, password))

def get_arangodb_db():
    uri = os.environ.get("ARANGO_URI")
    user = os.environ.get("ARANGO_USER")
    password = os.environ.get("ARANGO_PASSWORD")
    db_name = os.environ.get("ARANGO_DATABASE", "benchmark_db")
    
    if not uri: return None
    
    client = ArangoClient(hosts=uri)
    sys_db = client.db('_system', username=user, password=password)
    
    if not sys_db.has_database(db_name):
        sys_db.create_database(db_name)
        
    return client.db(db_name, username=user, password=password)

def get_falkordb_graph():
    host = os.environ.get("FALKORDB_HOST")
    port = int(os.environ.get("FALKORDB_PORT", 6379))
    password = os.environ.get("FALKORDB_PASSWORD")
    graph_name = os.environ.get("FALKORDB_GRAPH_NAME", "benchmark_graph")
    
    if not host: return None
    
    db = FalkorDB(host=host, port=port, password=password)
    return db.select_graph(graph_name)
