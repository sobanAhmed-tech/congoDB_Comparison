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
    uri = os.environ.get("NEO4J_URI", "bolt://localhost:7687")
    user = os.environ.get("NEO4J_USER", "neo4j")
    password = os.environ.get("NEO4J_PASSWORD", "password")
    return GraphDatabase.driver(uri, auth=(user, password))

def get_memgraph_driver():
    uri = os.environ.get("MEMGRAPH_URI", "bolt://localhost:7688")
    user = os.environ.get("MEMGRAPH_USER", "")
    password = os.environ.get("MEMGRAPH_PASSWORD", "")
    return GraphDatabase.driver(uri, auth=(user, password))

def get_arangodb_db():
    uri = os.environ.get("ARANGO_URI", "http://localhost:8529")
    user = os.environ.get("ARANGO_USER", "root")
    password = os.environ.get("ARANGO_PASSWORD", "password")
    db_name = os.environ.get("ARANGO_DATABASE", "benchmark_db")
    
    client = ArangoClient(hosts=uri)
    sys_db = client.db('_system', username=user, password=password)
    
    if not sys_db.has_database(db_name):
        sys_db.create_database(db_name)
        
    return client.db(db_name, username=user, password=password)

def get_falkordb_graph():
    host = os.environ.get("FALKORDB_HOST", "localhost")
    port = int(os.environ.get("FALKORDB_PORT", 6379))
    graph_name = os.environ.get("FALKORDB_GRAPH_NAME", "benchmark_graph")
    
    db = FalkorDB(host=host, port=port)
    return db.select_graph(graph_name)
