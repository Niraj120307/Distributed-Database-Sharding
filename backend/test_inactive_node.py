from database import connect_to_shard

try:
    connection = connect_to_shard("shard2_db")
    print("Connection successful!")
    connection.close()

except Exception as error:
    print("Connection rejected:", error)