
from database import connect_to_shard
from metadata_manager import get_active_nodes
from shard_router import get_shard


def get_replica_shard(primary_shard):
    active_nodes = get_active_nodes()

    if len(active_nodes) < 2:
        raise RuntimeError(
            "At least two active shards are required for replication."
        )

    primary_index = active_nodes.index(primary_shard)
    replica_index = (primary_index + 1) % len(active_nodes)

    return active_nodes[replica_index]


def replicate_student(student_id):
    """Create or synchronize the replica of a primary student."""

    primary_shard = get_shard(student_id, strategy="hash")
    replica_shard = get_replica_shard(primary_shard)

    primary_conn = None
    replica_conn = None

    try:
        primary_conn = connect_to_shard(primary_shard)
        replica_conn = connect_to_shard(replica_shard)

        primary_cursor = primary_conn.cursor()
        replica_cursor = replica_conn.cursor()

        primary_cursor.execute(
            """
            SELECT student_id, name, email, department, created_at
            FROM students
            WHERE student_id = %s AND is_replica = FALSE
            """,
            (student_id,)
        )

        student = primary_cursor.fetchone()

        if student is None:
            raise ValueError(
                f"Primary student {student_id} not found."
            )

        replica_cursor.execute(
            """
            INSERT INTO students
            (student_id, name, email, department, created_at,
             is_replica, primary_shard)
            VALUES (%s, %s, %s, %s, %s, TRUE, %s)
            ON DUPLICATE KEY UPDATE
                name = VALUES(name),
                email = VALUES(email),
                department = VALUES(department),
                created_at = VALUES(created_at),
                is_replica = TRUE,
                primary_shard = VALUES(primary_shard)
            """,
            (
                student[0],
                student[1],
                student[2],
                student[3],
                student[4],
                primary_shard
            )
        )

        replica_conn.commit()

        print(
            f"Replica synchronized: "
            f"{primary_shard} -> {replica_shard}"
        )

    except Exception:
        if replica_conn is not None:
            replica_conn.rollback()
        raise

    finally:
        if primary_conn is not None:
            primary_conn.close()

        if replica_conn is not None:
            replica_conn.close()


def delete_student_replica(student_id):
    """Delete the replica associated with a primary student."""

    primary_shard = get_shard(student_id, strategy="hash")
    replica_shard = get_replica_shard(primary_shard)

    connection = None

    try:
        connection = connect_to_shard(replica_shard)
        cursor = connection.cursor()

        cursor.execute(
            """
            DELETE FROM students
            WHERE student_id = %s
              AND is_replica = TRUE
              AND primary_shard = %s
            """,
            (student_id, primary_shard)
        )

        connection.commit()

        if cursor.rowcount > 0:
            print("Replica deleted from:", replica_shard)
        else:
            print("No replica found to delete.")

    except Exception:
        if connection is not None:
            connection.rollback()
        raise

    finally:
        if connection is not None:
            connection.close()


if __name__ == "__main__":
    student_id = 101

    print("===== REPLICATION MANAGER TEST =====")

    replicate_student(student_id)
