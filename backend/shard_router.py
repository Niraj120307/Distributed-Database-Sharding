
from shard_config import SHARDING_STRATEGY, SHARD_RANGES
from consistent_hashing import ConsistentHashRing
from metadata_manager import get_active_nodes


def hash_sharding(student_id, active_nodes):
    """Distribute records using modulo hashing."""

    shard_index = student_id % len(active_nodes)
    return active_nodes[shard_index]


def range_sharding(student_id, active_nodes):
    """Route records using configured ID ranges."""

    for shard, (start, end) in SHARD_RANGES.items():
        if start <= student_id <= end:
            if shard not in active_nodes:
                raise RuntimeError(
                    f"Shard {shard} is not currently active"
                )
            return shard

    raise ValueError("Student ID outside configured ranges")


def consistent_sharding(student_id, active_nodes):
    """Route records using consistent hashing."""

    ring = ConsistentHashRing(
        active_nodes,
        virtual_nodes=100
    )

    return ring.get_node(student_id)


def get_shard(student_id, strategy=None):
    """Select a shard using the chosen strategy."""

    if not isinstance(student_id, int) or isinstance(student_id, bool):
        raise ValueError("Student ID must be an integer")

    if student_id <= 0:
        raise ValueError("Student ID must be positive")

    if strategy is None:
        strategy = SHARDING_STRATEGY

    active_nodes = get_active_nodes()

    if strategy == "hash":
        return hash_sharding(student_id, active_nodes)

    elif strategy == "range":
        return range_sharding(student_id, active_nodes)

    elif strategy == "consistent":
        return consistent_sharding(student_id, active_nodes)

    else:
        raise ValueError("Unsupported sharding strategy")


if __name__ == "__main__":

    student_ids = [101, 102, 103, 104, 105, 106]
    strategies = ["hash", "range", "consistent"]

    print("ACTIVE SHARD NODES:")
    print(get_active_nodes())

    for strategy in strategies:
        print("\n", strategy.upper(), "SHARDING")

        for student_id in student_ids:
            try:
                shard = get_shard(student_id, strategy)
                print(student_id, "->", shard)

            except (ValueError, RuntimeError) as error:
                print(student_id, "->", error)
