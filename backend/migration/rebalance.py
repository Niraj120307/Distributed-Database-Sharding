
import os
import sys

BACKEND_DIR = os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))
)
sys.path.insert(0, BACKEND_DIR)

from database import connect_to_shard
from metadata_manager import get_active_nodes
from shard_router import get_shard

from migration.migration_logger import (
    create_migration_job,
    update_migration_job,
    log_migration_record
)


def migrate_record(source_shard, destination_shard, student):

    student_id, name, email, department, created_at = student

    source_conn = None
    destination_conn = None

    try:
        source_conn = connect_to_shard(source_shard)
        destination_conn = connect_to_shard(destination_shard)

        source_cursor = source_conn.cursor()
        destination_cursor = destination_conn.cursor()

        expected = (
            student_id, name, email, department, created_at
        )

        destination_cursor.execute(
            """
            SELECT student_id, name, email, department, created_at
            FROM students
            WHERE student_id = %s
            """,
            (student_id,)
        )

        existing = destination_cursor.fetchone()

        if existing is not None:

            if existing != expected:
                raise RuntimeError(
                    f"Conflicting record {student_id} at destination."
                )

        else:

            destination_cursor.execute(
                """
                INSERT INTO students
                (student_id, name, email, department, created_at)
                VALUES (%s, %s, %s, %s, %s)
                """,
                expected
            )

            destination_conn.commit()

            destination_cursor.execute(
                """
                SELECT student_id, name, email, department, created_at
                FROM students
                WHERE student_id = %s
                """,
                (student_id,)
            )

            inserted = destination_cursor.fetchone()

            if inserted != expected:
                raise RuntimeError(
                    f"Verification failed for student {student_id}."
                )

        # Delete source only after destination verification.
        source_cursor.execute(
            "DELETE FROM students WHERE student_id = %s",
            (student_id,)
        )

        if source_cursor.rowcount != 1:
            source_conn.rollback()
            raise RuntimeError(
                f"Source deletion failed for student {student_id}."
            )

        source_conn.commit()

        print(f"Student {student_id} migrated successfully.")

    except Exception:
        if source_conn is not None:
            source_conn.rollback()

        if destination_conn is not None:
            destination_conn.rollback()

        raise

    finally:
        if source_conn is not None:
            source_conn.close()

        if destination_conn is not None:
            destination_conn.close()


def rebalance(execute=False):

    active_nodes = get_active_nodes()

    print("\n===== DATA REBALANCING =====")
    print("Active nodes:", active_nodes)

    # First collect a snapshot of all records.
    records_to_check = []

    for source_shard in active_nodes:

        connection = connect_to_shard(source_shard)
        cursor = connection.cursor()

        try:
            cursor.execute(
                """
                SELECT student_id, name, email,
                       department, created_at
                FROM students
                ORDER BY student_id
                """
            )

            records = cursor.fetchall()

            for student in records:
                records_to_check.append(
                    (source_shard, student)
                )

        finally:
            cursor.close()
            connection.close()

    total_records = len(records_to_check)

    # Calculate migration destinations.
    migration_plan = []

    for source_shard, student in records_to_check:

        student_id = student[0]

        destination_shard = get_shard(
            student_id,
            strategy="hash"
        )

        if source_shard != destination_shard:
            migration_plan.append(
                (source_shard, destination_shard, student)
            )

    records_to_move = len(migration_plan)

    print("Total records:", total_records)
    print("Records requiring migration:", records_to_move)

    if not execute:
        for source, destination, student in migration_plan:
            print(
                f"Student {student[0]}: "
                f"{source} -> {destination}"
            )

        print("\nDry run only. No records were changed.")
        return

    if records_to_move == 0:
        print("\nCluster is already balanced.")
        return

    # Create a persistent migration job.
    job_id = create_migration_job(
        strategy="hash",
        total_records=total_records
    )

    print("\nMigration Job ID:", job_id)

    migrated = 0
    failed = 0

    for source, destination, student in migration_plan:

        student_id = student[0]

        print(
            f"\nMigrating {student_id}: "
            f"{source} -> {destination}"
        )

        try:
            migrate_record(source, destination, student)

            log_migration_record(
                job_id,
                student_id,
                source,
                destination,
                "SUCCESS"
            )

            migrated += 1

        except Exception as error:

            print("Migration failed:", error)

            failed += 1

            log_migration_record(
                job_id,
                student_id,
                source,
                destination,
                "FAILED"
            )

    final_status = "FAILED" if failed else "COMPLETED"

    update_migration_job(
        job_id,
        records_to_move,
        migrated,
        final_status
    )

    print("\n===== REBALANCING SUMMARY =====")
    print("Migration Job ID:", job_id)
    print("Total records:", total_records)
    print("Records requiring migration:", records_to_move)
    print("Successfully migrated:", migrated)
    print("Failed migrations:", failed)
    print("Final status:", final_status)


if __name__ == "__main__":

    execute = "--execute" in sys.argv
    rebalance(execute)
