
import mysql.connector
from dotenv import load_dotenv
import os

from metadata_manager import get_node_details
from metadata_manager import get_active_nodes

load_dotenv()

USER = "root"
PASSWORD = os.getenv("MYSQL_ROOT_PASSWORD")


def connect_to_shard(shard_name):
    """
    Connect to a shard using connection details
    retrieved from the metadata database.
    """

    node = get_node_details(shard_name)

    connection = mysql.connector.connect(
        host=node["host"],
        port=node["port"],
        user=USER,
        password=PASSWORD,
        database=node["database_name"]
    )

    return connection


if __name__ == "__main__":

    print("===== TESTING DYNAMIC SHARD CONNECTIONS =====")

    shards = get_active_nodes()

    for shard in shards:
        try:
            connection = connect_to_shard(shard)
            print(shard, "connected successfully!")
            connection.close()

        except Exception as error:
            print(shard, "connection failed:", error)
