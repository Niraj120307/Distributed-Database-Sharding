
import os
import sys

BACKEND_DIR = os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))
)
sys.path.insert(0, BACKEND_DIR)

from metadata_manager import connect_to_metadata


def create_migration_job(strategy, total_records):
    connection = connect_to_metadata()
    cursor = connection.cursor()

    try:
        cursor.execute(
            """
            INSERT INTO migration_jobs
            (strategy, total_records, records_to_move,
             records_migrated, status)
            VALUES (%s, %s, 0, 0, 'RUNNING')
            """,
            (strategy, total_records)
        )

        connection.commit()
        return cursor.lastrowid

    finally:
        cursor.close()
        connection.close()


def update_migration_job(job_id, records_to_move,
                         records_migrated, status):

    connection = connect_to_metadata()
    cursor = connection.cursor()

    try:
        cursor.execute(
            """
            UPDATE migration_jobs
            SET records_to_move = %s,
                records_migrated = %s,
                status = %s,
                completed_at = CURRENT_TIMESTAMP
            WHERE job_id = %s
            """,
            (records_to_move, records_migrated, status, job_id)
        )

        connection.commit()

    finally:
        cursor.close()
        connection.close()


def log_migration_record(job_id, student_id, source_shard,
                         destination_shard, status):

    connection = connect_to_metadata()
    cursor = connection.cursor()

    try:
        cursor.execute(
            """
            INSERT INTO migration_records
            (job_id, student_id, source_shard,
             destination_shard, status)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (
                job_id,
                student_id,
                source_shard,
                destination_shard,
                status
            )
        )

        connection.commit()

    finally:
        cursor.close()
        connection.close()


def get_migration_history():

    connection = connect_to_metadata()
    cursor = connection.cursor(dictionary=True)

    try:
        cursor.execute(
            """
            SELECT *
            FROM migration_jobs
            ORDER BY job_id DESC
            """
        )

        return cursor.fetchall()

    finally:
        cursor.close()
        connection.close()


if __name__ == "__main__":

    print("===== MIGRATION HISTORY =====")

    jobs = get_migration_history()

    if not jobs:
        print("No migration history found.")

    for job in jobs:
        print(job)

