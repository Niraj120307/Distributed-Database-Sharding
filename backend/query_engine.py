# query_engine.py

from database import connect_to_shard


# List of all available shards
SHARDS = ["shard1_db", "shard2_db", "shard3_db"]


# Scatter-Gather Query
def search_by_department(department):

    all_students = []

    # SCATTER: Send query to every shard
    for shard in SHARDS:

        connection = connect_to_shard(shard)
        cursor = connection.cursor()

        query = """
            SELECT * FROM students
            WHERE department = %s
        """

        cursor.execute(query, (department,))

        records = cursor.fetchall()

        # GATHER: Collect results
        for student in records:
            all_students.append(student)

        cursor.close()
        connection.close()

    # Display combined results
    print("\n===== SCATTER-GATHER RESULTS =====")

    if all_students:

        for student in all_students:
            print(student)

        print("\nTotal students found:", len(all_students))

    else:
        print("No students found in this department.")


# Test the query engine
if __name__ == "__main__":

    department = input("Enter department to search: ")

    search_by_department(department)