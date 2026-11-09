# shard_config.py

# Available database nodes
SHARD_NODES = [
    "shard1_db",
    "shard2_db",
    "shard3_db"
]

# Active sharding strategy
SHARDING_STRATEGY = "hash"

# Range-based sharding configuration
SHARD_RANGES = {
    "shard1_db": (1, 1000),
    "shard2_db": (1001, 2000),
    "shard3_db": (2001, 3000)
}