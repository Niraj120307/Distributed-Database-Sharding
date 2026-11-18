"""MySQL connections for shard nodes and cluster metadata."""
import os               #used to access enviornmental variables
import mysql.connector
from dotenv import load_dotenv

load_dotenv()  #loads environment variables from a .env file
USER = os.getenv("MYSQL_USER", "root")   # it retrieves the value of MYSQL_USER from env
PASSWORD = os.getenv("MYSQL_ROOT_PASSWORD", "")


def connect_to_metadata():
    return mysql.connector.connect(
        host=os.getenv("METADATA_HOST", "127.0.0.1"),              #Address of MySQL server
        port=int(os.getenv("METADATA_PORT", "3310")), user=USER,   #Port on which MySQL is accessible
        password=PASSWORD, database=os.getenv("METADATA_DATABASE", "cluster_metadata"),
        connection_timeout=4,
    )


def connect_to_shard(shard_name):    #It accepts a shard name as an argument
    """Use registered node details, falling back to known local Compose ports."""
    try:
        connection = connect_to_metadata()   #Connect to metadata
        cursor = connection.cursor(dictionary=True)  # Create a dictionary cursor
        cursor.execute("SELECT host, port, database_name, status FROM shard_nodes WHERE node_name=%s", (shard_name,))  # %s placeholder is a parameterized query
        node = cursor.fetchone()
        cursor.close()
        connection.close()
    except mysql.connector.Error:
        node = None
    if node is not None and node["status"] != "ACTIVE":        #Chech whether node is active
        raise ValueError(f"Shard is inactive: {shard_name}")
    if node is None:   #If no metadata record is found => Fallback
        key = shard_name.upper().replace('-', '_')
        hosts = {"shard1_db": ("127.0.0.1", 3307), "shard2_db": ("127.0.0.1", 3308), "shard3_db": ("127.0.0.1", 3309), "shard4_db": ("127.0.0.1", 3311)}
        if shard_name not in hosts:
            raise ValueError(f"Unknown or inactive shard: {shard_name}")
        host, port = hosts[shard_name]
        host = os.getenv(f"DB_HOST_{key}", host)
        port = int(os.getenv(f"DB_PORT_{key}", str(port)))
        node = {"host": host, "port": port, "database_name": "shard_db"}
    return mysql.connector.connect(host=node["host"], port=int(node["port"]), user=USER, password=PASSWORD, database=node["database_name"], connection_timeout=3)
