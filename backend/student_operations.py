
from database import connect_to_shard
from shard_router import get_shard
from metadata_manager import get_active_nodes
from replication_manager import (
    replicate_student,
    delete_student_replica
)


# 1. INSERT STUDENT
def add_student(student_id, name, email, department):

    shard = get_shard(student_id)
    connection = None

    try:
        connection = connect_to_shard(shard)
        cursor = connection.cursor()

        query = """
            INSERT INTO students
            (student_id, name, email, department)
            VALUES (%s, %s, %s, %s)
        """

        cursor.execute(
            query,
            (student_id, name, email, department)
        )

        connection.commit()

        print("Student added successfully!")
        print("Primary stored in:", shard)

    finally:
        if connection is not None:
            connection.close()

    # Replicate after primary insertion
    try:
        replicate_student(student_id)
    except Exception as error:
        print("WARNING: Primary inserted, but replication failed:", error)


# 2. VIEW ALL PRIMARY STUDENTS
def view_students():

    shards = get_active_nodes()
    found = False

    for shard in shards:

        connection = connect_to_shard(shard)
        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT student_id, name, email, department, created_at
            FROM students
            WHERE is_replica = FALSE
            ORDER BY student_id
            """
        )

        records = cursor.fetchall()

        print("\n---", shard, "---")

        for student in records:
            found = True
            print(student)

        cursor.close()
        connection.close()

    if not found:
        print("No students found.")


# 3. SEARCH STUDENT
def search_student(student_id):

    shard = get_shard(student_id)
    connection = connect_to_shard(shard)
    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT student_id, name, email, department, created_at
        FROM students
        WHERE student_id = %s AND is_replica = FALSE
        """,
        (student_id,)
    )

    student = cursor.fetchone()

    if student:
        print("Student found:", student)
        print("Primary located in:", shard)
    else:
        print("Student not found!")

    cursor.close()
    connection.close()


# 4. UPDATE STUDENT
def update_student(student_id, name, email, department):

    shard = get_shard(student_id)
    connection = connect_to_shard(shard)

    try:
        cursor = connection.cursor()

        cursor.execute(
            """
            UPDATE students
            SET name = %s, email = %s, department = %s
            WHERE student_id = %s AND is_replica = FALSE
            """,
            (name, email, department, student_id)
        )

        updated = cursor.rowcount > 0
        connection.commit()

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()

    if updated:
        print("Primary student updated successfully!")

        try:
            replicate_student(student_id)
        except Exception as error:
            print("WARNING: Primary updated, but replica synchronization failed:", error)
    else:
        print("Student not found!")


# 5. DELETE STUDENT
def delete_student(student_id):

    shard = get_shard(student_id)
    connection = connect_to_shard(shard)

    try:
        cursor = connection.cursor()

        cursor.execute(
            """
            DELETE FROM students
            WHERE student_id = %s AND is_replica = FALSE
            """,
            (student_id,)
        )

        deleted = cursor.rowcount > 0
        connection.commit()

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()

    if deleted:
        print("Primary student deleted successfully!")

        try:
            delete_student_replica(student_id)
        except Exception as error:
            print("WARNING: Primary deleted, but replica deletion failed:", error)
    else:
        print("Student not found!")


# MAIN MENU
if __name__ == "__main__":

    while True:

        print("\n===== DISTRIBUTED DATABASE SYSTEM =====")
        print("1. Add Student")
        print("2. View All Students")
        print("3. Search Student")
        print("4. Update Student")
        print("5. Delete Student")
        print("6. Exit")

        choice = input("Enter your choice: ")

        try:

            if choice == "1":
                sid = int(input("Student ID: "))
                name = input("Name: ")
                email = input("Email: ")
                department = input("Department: ")

                add_student(sid, name, email, department)

            elif choice == "2":
                view_students()

            elif choice == "3":
                sid = int(input("Enter Student ID: "))
                search_student(sid)

            elif choice == "4":
                sid = int(input("Enter Student ID: "))
                name = input("New Name: ")
                email = input("New Email: ")
                department = input("New Department: ")

                update_student(sid, name, email, department)

            elif choice == "5":
                sid = int(input("Enter Student ID: "))
                delete_student(sid)

            elif choice == "6":
                print("Exiting application...")
                break

            else:
                print("Invalid choice!")

        except ValueError as error:
            print("Invalid input or operation:", error)

        except Exception as error:
            print("Operation failed:", error)
