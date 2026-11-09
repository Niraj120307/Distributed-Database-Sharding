
import mysql.connector
from dotenv import load_dotenv
import os

load_dotenv()

# Metadata database connection details
METADATA_CONFIG = {
    "host": "127.0.0.1",
    "port": 3310,
    "user": "root",
    "password": os.getenv("MYSQL_ROOT_PASSWORD"),
    "database": "cluster_metadata"
}


def connect_to_metadata():
    """Connect to the cluster metadata database."""
    return mysql.connector.connect(**METADATA_CONFIG)


def register_node(node_name, host, port, database_name, virtual_nodes=100):
    """Register a new shard node in the metadata database."""

    connection = connect_to_metadata()
    cursor = connection.cursor()

    query = """
        INSERT INTO shard_nodes
        (node_name, host, port, database_name, virtual_nodes)
        VALUES (%s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
        host = VALUES(host),
        port = VALUES(port),
        database_name = VALUES(database_name),
        virtual_nodes = VALUES(virtual_nodes)
    """

    values = (node_name, host, port, database_name, virtual_nodes)

    cursor.execute(query, values)
    connection.commit()

    print(f"Node '{node_name}' registered successfully!")

    cursor.close()
    connection.close()


def get_all_nodes():
    """Retrieve all registered shard nodes."""

    connection = connect_to_metadata()
    cursor = connection.cursor(dictionary=True)

    cursor.execute("SELECT * FROM shard_nodes ORDER BY node_id")
    nodes = cursor.fetchall()

    cursor.close()
    connection.close()

    return nodes


def get_active_nodes():
    """Return only currently active shard nodes."""

    nodes = get_all_nodes()

    active_nodes = [
        node["node_name"]
        for node in nodes
        if node["status"] == "ACTIVE"
    ]

    if not active_nodes:
        raise RuntimeError("No active shard nodes available")

    return active_nodes


def get_node_details(node_name):
    """Retrieve connection details for a specific active node."""

    connection = connect_to_metadata()
    cursor = connection.cursor(dictionary=True)

    query = """
        SELECT node_name, host, port, database_name, status
        FROM shard_nodes
        WHERE node_name = %s AND status = 'ACTIVE'
    """

    cursor.execute(query, (node_name,))
    node = cursor.fetchone()

    cursor.close()
    connection.close()

    if node is None:
        raise ValueError(
            f"Node '{node_name}' does not exist or is inactive"
        )

    return node


def update_node_status(node_name, status):
    """Change a node's status to ACTIVE or INACTIVE."""

    if status not in ("ACTIVE", "INACTIVE"):
        raise ValueError("Status must be ACTIVE or INACTIVE")

    connection = connect_to_metadata()
    cursor = connection.cursor()

    query = """
        UPDATE shard_nodes
        SET status = %s
        WHERE node_name = %s
    """

    cursor.execute(query, (status, node_name))
    connection.commit()

    updated = cursor.rowcount

    cursor.close()
    connection.close()

    if updated:
        print(f"{node_name} status updated to {status}")
    else:
        print(f"Node '{node_name}' not found")


def set_cluster_config(config_key, config_value):
    """Insert or update a cluster-wide configuration."""

    connection = connect_to_metadata()
    cursor = connection.cursor()

    query = """
        INSERT INTO cluster_config (config_key, config_value)
        VALUES (%s, %s)
        ON DUPLICATE KEY UPDATE config_value = VALUES(config_value)
    """

    cursor.execute(query, (config_key, str(config_value)))
    connection.commit()

    cursor.close()
    connection.close()

    print(f"Configuration '{config_key}' saved.")


def get_cluster_config():
    """Retrieve all cluster configuration values."""

    connection = connect_to_metadata()
    cursor = connection.cursor(dictionary=True)

    cursor.execute("SELECT config_key, config_value FROM cluster_config")
    configs = cursor.fetchall()

    cursor.close()
    connection.close()

    return configs


if __name__ == "__main__":

    print("\n===== TESTING NODE STATUS UPDATE =====")

    update_node_status("shard2_db", "INACTIVE")

    print("\n===== NODES AFTER STATUS UPDATE =====")

    for node in get_all_nodes():
        print(node["node_name"], "->", node["status"])

    # Restore original status
    update_node_status("shard2_db", "ACTIVE")

    print("\n===== REGISTERING SHARD NODES =====")

    register_node("shard1_db", "127.0.0.1", 3307, "shard_db")
    register_node("shard2_db", "127.0.0.1", 3308, "shard_db")
    register_node("shard3_db", "127.0.0.1", 3309, "shard_db")
    register_node("shard4_db", "127.0.0.1", 3311, "shard_db")
    print("\n===== REGISTERED NODES =====")

    for node in get_all_nodes():
        print(node)

    print("\n===== SAVING CLUSTER CONFIGURATION =====")

    set_cluster_config("sharding_strategy", "hash")
    set_cluster_config("replication_enabled", "false")

    print("\n===== CLUSTER CONFIGURATION =====")

    for config in get_cluster_config():
        print(config)
