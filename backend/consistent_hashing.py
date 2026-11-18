# Consistent hashing : It is a hashing technique that distributes keys and nodes
# around a circular hash space

import hashlib  #Provides cryptographic hash functions, including SHA-256
import bisect   #Provides binary-search functionality on sorted lists


class ConsistentHashRing:

    def __init__(self, nodes, virtual_nodes=100):

        self.virtual_nodes = virtual_nodes
        self.ring = {}
        self.sorted_keys = []

        # Add every physical node to the hash ring
        for node in nodes:
            self.add_node(node)

    # Generate a consistent hash value
    def hash_value(self, key):
        key = str(key).encode("utf-8")

        hash_result = hashlib.sha256(key).hexdigest()  # Calculate SHA-256 hash

        return int(hash_result, 16)

    # Add a physical node and its virtual nodes        
    def add_node(self, node):                 # Why virtual nodes? #They help distribute physical node's
        for i in range(self.virtual_nodes):   #ownership across the hash ring more evenly

            virtual_node = f"{node}:VN{i}"

            position = self.hash_value(virtual_node)

            self.ring[position] = node

            bisect.insort(self.sorted_keys, position)

    # Find the responsible physical node
    def get_node(self, key):

        if not self.sorted_keys:
            raise ValueError("Hash ring is empty")

        position = self.hash_value(key)

        index = bisect.bisect_left(
            self.sorted_keys,
            position
        )

        # Wrap around to the beginning of the ring
        if index == len(self.sorted_keys):
            index = 0

        ring_position = self.sorted_keys[index]

        return self.ring[ring_position]


# Compare data movement when a node is added
if __name__ == "__main__":

    original_nodes = [
        "shard1_db",
        "shard2_db",
        "shard3_db"
    ]

    updated_nodes = original_nodes + ["shard4_db"]

    # Create rings before and after adding a node
    old_ring = ConsistentHashRing(original_nodes)
    new_ring = ConsistentHashRing(updated_nodes)

    total_records = 10000

    moved_records = 0

    for student_id in range(1, total_records + 1):

        old_shard = old_ring.get_node(student_id)
        new_shard = new_ring.get_node(student_id)

        if old_shard != new_shard:
            moved_records += 1

    movement_percentage = (
        moved_records / total_records
    ) * 100

    print("\n===== CONSISTENT HASHING ANALYSIS =====")

    print("Original nodes:", original_nodes)
    print("Updated nodes:", updated_nodes)

    print("Total records:", total_records)
    print("Records reassigned:", moved_records)

    print(
        "Data movement percentage:",
        round(movement_percentage, 2),
        "%"
    )

    print(
        "Records retained:",
        total_records - moved_records
    )
