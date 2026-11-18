"""HTTP API used by the existing ShardX browser interface."""
import os
import re
import csv
import io
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Query, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import mysql.connector

from database import connect_to_metadata, connect_to_shard
from metadata_manager import get_all_nodes, register_node, update_node_status, set_cluster_config, get_cluster_config
from shard_router import get_shard

NODES = [
    ("shard1_db", "shard1", 3306, "127.0.0.1", 3307),
    ("shard2_db", "shard2", 3306, "127.0.0.1", 3308),
    ("shard3_db", "shard3", 3306, "127.0.0.1", 3309),
    ("shard4_db", "shard4", 3306, "127.0.0.1", 3311),
]


def initialize_cluster():
    last_error = None
    for attempt in range(30):
        try:
            for name, compose_host, compose_port, local_host, local_port in NODES:
                host = os.getenv(f"DB_HOST_{name.upper()}", compose_host if os.getenv("METADATA_HOST") else local_host)
                port = int(os.getenv(f"DB_PORT_{name.upper()}", str(compose_port if os.getenv("METADATA_HOST") else local_port)))
                register_node(name, host, port, "shard_db")
                # An unavailable shard must not prevent API startup; schema errors on
                # reachable shards still fail initialization and remain visible.
                try:
                    conn = mysql.connector.connect(host=host, port=port, user=os.getenv("MYSQL_USER", "root"), password=os.getenv("MYSQL_ROOT_PASSWORD", ""), database="shard_db", connection_timeout=3)
                except (mysql.connector.InterfaceError, mysql.connector.OperationalError):
                    continue
                try:
                    cur = conn.cursor()
                    cur.execute("CREATE TABLE IF NOT EXISTS students (student_id INT PRIMARY KEY, name VARCHAR(100) NOT NULL, email VARCHAR(100) NOT NULL, department VARCHAR(50) NOT NULL, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, is_replica BOOLEAN NOT NULL DEFAULT FALSE, primary_shard VARCHAR(100) NULL)")
                    if not column_exists(cur, "is_replica"):
                        cur.execute("ALTER TABLE students ADD COLUMN is_replica BOOLEAN NOT NULL DEFAULT FALSE")
                    if not column_exists(cur, "primary_shard"):
                        cur.execute("ALTER TABLE students ADD COLUMN primary_shard VARCHAR(100) NULL")
                    if not index_exists(cur, "idx_student_email"): cur.execute("CREATE INDEX idx_student_email ON students(email)")
                    if not index_exists(cur, "idx_student_department"): cur.execute("CREATE INDEX idx_student_department ON students(department)")
                    if not index_exists(cur, "idx_student_primary_replica"): cur.execute("CREATE INDEX idx_student_primary_replica ON students(is_replica, student_id)")
                    conn.commit(); cur.close()
                finally:
                    conn.close()
            meta = connect_to_metadata(); cursor = meta.cursor()
            cursor.execute("CREATE TABLE IF NOT EXISTS migration_jobs (job_id INT AUTO_INCREMENT PRIMARY KEY, strategy VARCHAR(32) NOT NULL, total_records INT NOT NULL DEFAULT 0, records_to_move INT NOT NULL DEFAULT 0, records_migrated INT NOT NULL DEFAULT 0, status ENUM('RUNNING','COMPLETED','FAILED') NOT NULL DEFAULT 'RUNNING', created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, completed_at TIMESTAMP NULL)")
            cursor.execute("CREATE TABLE IF NOT EXISTS migration_records (record_id BIGINT AUTO_INCREMENT PRIMARY KEY, job_id INT NOT NULL, student_id INT NOT NULL, source_shard VARCHAR(100) NOT NULL, destination_shard VARCHAR(100) NOT NULL, status ENUM('SUCCESS','FAILED') NOT NULL, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, INDEX idx_migration_job(job_id), CONSTRAINT fk_migration_records_job FOREIGN KEY (job_id) REFERENCES migration_jobs(job_id))")
            cursor.execute("CREATE TABLE IF NOT EXISTS operation_events (operation_id BIGINT AUTO_INCREMENT PRIMARY KEY, operation VARCHAR(64) NOT NULL, target VARCHAR(128) NOT NULL, status ENUM('SUCCESS','FAILED') NOT NULL DEFAULT 'SUCCESS', occurred_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, INDEX idx_operation_time(occurred_at))")
            meta.commit(); cursor.close(); meta.close()
            set_cluster_config("sharding_strategy", "hash")
            set_cluster_config("replication_enabled", "false")
            return
        except Exception as exc:
            last_error = exc
            import time
            time.sleep(2)
    raise RuntimeError(f"Could not initialize MySQL cluster: {last_error}")


def index_exists(cursor, index_name):
    cursor.execute("SELECT COUNT(*) FROM information_schema.statistics WHERE table_schema=DATABASE() AND table_name='students' AND index_name=%s", (index_name,))
    return cursor.fetchone()[0] > 0


def column_exists(cursor, column_name):
    cursor.execute("SELECT COUNT(*) FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='students' AND column_name=%s", (column_name,))
    return cursor.fetchone()[0] > 0


@asynccontextmanager
async def lifespan(_app):
    initialize_cluster()
    yield


app = FastAPI(title="ShardX API", version="1.0.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


class Student(BaseModel):
    student_id: int = Field(gt=0)
    name: str = Field(min_length=1, max_length=100)
    email: str = Field(min_length=3, max_length=100)
    department: str = Field(min_length=1, max_length=50)


MAX_CSV_SIZE = 10 * 1024 * 1024  # 10 MB

REQUIRED_CSV_COLUMNS = {
    "student_id",
    "name",
    "email",
    "department"
}



def parse_students_csv(file_content: bytes):
    """
    Read and validate CSV records.
    Does not insert anything into MySQL.
    """

    try:
        text = file_content.decode("utf-8-sig")

        # Remove blank lines and whitespace before the header
        text = text.lstrip("\ufeff\r\n\t ")

        reader = csv.DictReader(io.StringIO(text))

        if not reader.fieldnames:
            raise HTTPException(400, "CSV file is empty.")

        # Remove accidental spaces around column names
        reader.fieldnames = [
            name.strip() if name else name
            for name in reader.fieldnames
        ]

        columns = set(reader.fieldnames)

        missing = REQUIRED_CSV_COLUMNS - columns

        if missing:
            raise HTTPException(
                400,
                f"Missing CSV columns: {', '.join(sorted(missing))}"
            )

        valid_records = []
        errors = []
        seen_ids = set()

        for row_number, row in enumerate(reader, start=2):
            try:
                student = Student(
                    student_id=int(row["student_id"]),
                    name=(row["name"] or "").strip(),
                    email=(row["email"] or "").strip(),
                    department=(row["department"] or "").strip()
                )

                if student.student_id in seen_ids:
                    raise ValueError(
                        f"Duplicate student ID {student.student_id} in CSV"
                    )

                seen_ids.add(student.student_id)
                valid_records.append(student)

            except Exception as exc:
                errors.append({
                    "row": row_number,
                    "error": str(exc)
                })

        return valid_records, errors

    except UnicodeDecodeError:
        raise HTTPException(
            400,
            "Please upload a UTF-8 encoded CSV file."
        )

@app.post("/api/students/bulk-preview")
async def bulk_preview(file: UploadFile = File(...)):

    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(400, "Please upload a CSV file.")

    content = await file.read()

    # DEBUG: Check what the API receives
    print("========== CSV PREVIEW DEBUG ==========", flush=True)
    print("Filename:", file.filename, flush=True)
    print("Received file size:", len(content), flush=True)
    print("Received content:", repr(content[:200]), flush=True)

    if len(content) > MAX_CSV_SIZE:
        raise HTTPException(413, "CSV file must be 10 MB or smaller.")

    records, errors = parse_students_csv(content)

    distribution = {}

    for student in records:
        shard = get_shard(student.student_id)
        distribution[shard] = distribution.get(shard, 0) + 1

    return {
        "total_valid": len(records),
        "total_invalid": len(errors),
        "preview": [
            student.model_dump()
            for student in records[:10]
        ],
        "errors": errors[:50],
        "shard_distribution": distribution
    }



@app.post("/api/students/bulk-import")
async def bulk_import(file: UploadFile = File(...)):

    # Check file extension
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(400, "Please upload a CSV file.")

    # Read CSV file

    content = await file.read()

    if len(content) > MAX_CSV_SIZE:
        raise HTTPException(413, "CSV file must be 10 MB or smaller.")


    # Validate CSV records
    records, errors = parse_students_csv(content)

    if not records:
        raise HTTPException(
            400,
            detail={
                "message": "No valid student records found.",
                "errors": errors[:50]
            }
        )

    # Distribute records according to shard
    shard_records = {}

    for student in records:
        shard = get_shard(student.student_id)
        shard_records.setdefault(shard, []).append(student)

    inserted = 0
    skipped = 0
    shard_results = {}

    # Insert records shard by shard
    for shard, students in shard_records.items():

        connection = None
        cursor = None

        try:
            connection = connect_to_shard(shard)
            cursor = connection.cursor()

            shard_inserted = 0
            shard_skipped = 0
            batch_size = 500

            # Process records in batches
            for start in range(0, len(students), batch_size):

                batch = students[start:start + batch_size]

                student_ids = [s.student_id for s in batch]
                placeholders = ",".join(["%s"] * len(student_ids))

                # Check which student IDs already exist
                cursor.execute(
                    f"""
                    SELECT student_id
                    FROM students
                    WHERE student_id IN ({placeholders})
                    """,
                    tuple(student_ids)
                )

                existing_ids = {
                    row[0] for row in cursor.fetchall()
                }

                new_students = [
                    s for s in batch
                    if s.student_id not in existing_ids
                ]

                shard_skipped += len(existing_ids)

                # Insert only new students
                if new_students:
                    values = [
                        (
                            s.student_id,
                            s.name,
                            s.email,
                            s.department
                        )
                        for s in new_students
                    ]

                    cursor.executemany(
                        """
                        INSERT INTO students
                        (student_id, name, email, department)
                        VALUES (%s, %s, %s, %s)
                        """,
                        values
                    )

                    shard_inserted += len(new_students)

            # Commit this shard's records
            connection.commit()

            inserted += shard_inserted
            skipped += shard_skipped

            shard_results[shard] = {
                "inserted": shard_inserted,
                "skipped": shard_skipped,
                "status": "SUCCESS"
            }

        except Exception as exc:

            if connection:
                connection.rollback()

            shard_results[shard] = {
                "inserted": 0,
                "skipped": 0,
                "status": "FAILED",
                "error": str(exc)
            }

        finally:
            if cursor:
                cursor.close()

            if connection:
                connection.close()

    # Identify failed shards
    failed_shards = [
        name
        for name, result in shard_results.items()
        if result["status"] == "FAILED"
    ]

    # Record bulk import operation in metadata database
    record_operation(
        "BULK_IMPORT",
        (
            f"Inserted: {inserted}, "
            f"Skipped: {skipped}, "
            f"Invalid: {len(errors)}"
        ),
        "FAILED" if failed_shards else "SUCCESS"
    )

    # Return import summary
    return {
        "message": "Bulk import completed.",
        "total_valid": len(records),
        "inserted": inserted,
        "skipped": skipped,
        "invalid": len(errors),
        "failed_shards": failed_shards,
        "shard_results": shard_results,
        "errors": errors[:50]
    }

def db_error(exc):
    if isinstance(exc, mysql.connector.Error):
        raise HTTPException(status_code=503, detail=f"Database unavailable: {exc.msg}")
    if isinstance(exc, RuntimeError):
        raise HTTPException(status_code=503, detail=str(exc))
    raise exc


def record_operation(operation, target, status="SUCCESS"):
    try:
        connection = connect_to_metadata()
    except Exception:
        return
    try:
        cursor = connection.cursor()
        cursor.execute("INSERT INTO operation_events(operation,target,status) VALUES(%s,%s,%s)", (operation, str(target), status))
        connection.commit()
        cursor.close()
    finally:
        connection.close()


def rows_on_shard(name, query, params=()):
    connection = connect_to_shard(name)
    try:
        cursor = connection.cursor(dictionary=True)
        cursor.execute(query, params)
        return cursor.fetchall()
    finally:
        connection.close()


def all_primary_students():
    results = []
    for node in get_all_nodes():
        try:
            records = rows_on_shard(node["node_name"], "SELECT student_id,name,email,department,created_at FROM students WHERE is_replica=FALSE")
            results.extend({**r, "shard": node["node_name"]} for r in records)
        except Exception:
            continue
    return results


@app.get("/")
def root():
    return {"service": "ShardX API", "docs": "/docs"}


@app.get("/health")
def health():
    try:
        nodes = get_all_nodes()
        reachable = 0
        for node in nodes:
            try:
                conn = connect_to_shard(node["node_name"])
                conn.close()
                reachable += 1
            except Exception:
                if node["status"] == "ACTIVE":
                    update_node_status(node["node_name"], "INACTIVE")
        return {"status": "ok" if reachable else "degraded", "database": reachable > 0, "nodes_reachable": reachable}
    except Exception as exc:
        return {"status": "unavailable", "database": False, "detail": str(exc)}


@app.get("/api/dashboard")
def dashboard():
    nodes = get_all_nodes()
    shard_stats = []
    live_nodes = []
    total = 0
    for node in nodes:
        try:
            conn = connect_to_shard(node["node_name"])
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM students WHERE is_replica=FALSE")
            count = cur.fetchone()[0]
            cur.close(); conn.close()
            total += count
            status = "ACTIVE"
        except Exception:
            count = 0
            status = "INACTIVE"
        live_nodes.append({"node_id": node["node_name"], "host": f"{node['host']}:{node['port']}", "status": status, "assigned_shards": 1 if status == "ACTIVE" else 0})
        shard_stats.append({"shard_id": node["node_name"], "node": node["node_name"], "records": count, "status": status})
    conn = connect_to_metadata()
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT occurred_at,operation,status FROM operation_events ORDER BY operation_id DESC LIMIT 10")
        operations = cur.fetchall()
    finally:
        conn.close()
    return {"total_shards": len(nodes), "active_nodes": sum(n["status"] == "ACTIVE" for n in live_nodes), "total_records": total, "database_connected": any(n["status"] == "ACTIVE" for n in live_nodes), "nodes": live_nodes, "shards": shard_stats, "recent_operations": operations}


@app.get("/api/nodes")
def nodes():
    output = []
    for node in get_all_nodes():
        status = node["status"]
        try:
            conn = connect_to_shard(node["node_name"]); conn.close()
            status = "ACTIVE"
        except Exception:
            status = "INACTIVE"
        output.append({"node_id": node["node_name"], "node_name": node["node_name"], "host": node["host"], "port": node["port"], "status": status, "assigned_shards": 1 if status == "ACTIVE" else 0})
    return output


@app.patch("/api/nodes/{node_name}/status")
def node_status(node_name: str, body: dict):
    status = body.get("status")
    if status not in ("ACTIVE", "INACTIVE"):
        raise HTTPException(400, "Status must be ACTIVE or INACTIVE")
    try:
        update_node_status(node_name, status)
        record_operation("NODE_STATUS", f"{node_name}: {status}")
    except Exception as exc: db_error(exc)
    return {"node_name": node_name, "status": status}


@app.get("/api/shards")
def shards():
    return dashboard()["shards"]


@app.get("/api/students")
def list_students(search: str = "", department: str = "", limit: int = Query(100, ge=1, le=500), offset: int = Query(0, ge=0)):
    results = all_primary_students()
    if search:
        q = search.casefold(); results = [r for r in results if q in str(r["student_id"]).casefold() or q in r["name"].casefold() or q in r["email"].casefold()]
    if department: results = [r for r in results if r["department"].casefold() == department.casefold()]
    results.sort(key=lambda r: r["student_id"])
    return {"items": results[offset:offset + limit], "total": len(results)}


@app.post("/api/students", status_code=201)
def create_student(student: Student):
    try:
        shard = get_shard(student.student_id)
        connection = connect_to_shard(shard)
        try:
            cursor = connection.cursor()
            cursor.execute("INSERT INTO students(student_id,name,email,department) VALUES(%s,%s,%s,%s)", (student.student_id, student.name, student.email, student.department))
            connection.commit(); cursor.close()
        finally: connection.close()
        record_operation("CREATE_STUDENT", f"{student.student_id} on {shard}")
        return {"student_id": student.student_id, "shard": shard, "status": "created"}
    except mysql.connector.IntegrityError: raise HTTPException(409, "Student ID already exists")
    except Exception as exc: db_error(exc)


@app.get("/api/students/{student_id}")
def get_student(student_id: int):
    try:
        shard = get_shard(student_id)
        result = rows_on_shard(shard, "SELECT student_id,name,email,department,created_at FROM students WHERE student_id=%s AND is_replica=FALSE", (student_id,))
        if not result: raise HTTPException(404, "Student not found")
        return {**result[0], "shard": shard}
    except HTTPException: raise
    except Exception as exc: db_error(exc)


@app.put("/api/students/{student_id}")
def update_student(student_id: int, student: Student):
    if student_id != student.student_id: raise HTTPException(400, "Path and body student IDs must match")
    try:
        shard = get_shard(student_id); connection = connect_to_shard(shard)
        try:
            cursor = connection.cursor(); cursor.execute("UPDATE students SET name=%s,email=%s,department=%s WHERE student_id=%s AND is_replica=FALSE", (student.name, student.email, student.department, student_id)); connection.commit(); changed = cursor.rowcount; cursor.close()
        finally: connection.close()
        if not changed: raise HTTPException(404, "Student not found")
        record_operation("UPDATE_STUDENT", f"{student_id} on {shard}")
        return {"student_id": student_id, "shard": shard, "status": "updated"}
    except HTTPException: raise
    except Exception as exc: db_error(exc)


@app.delete("/api/students/{student_id}")
def delete_student(student_id: int):
    try:
        shard = get_shard(student_id); connection = connect_to_shard(shard)
        try:
            cursor = connection.cursor(); cursor.execute("DELETE FROM students WHERE student_id=%s AND is_replica=FALSE", (student_id,)); connection.commit(); changed = cursor.rowcount; cursor.close()
        finally: connection.close()
        if not changed: raise HTTPException(404, "Student not found")
        record_operation("DELETE_STUDENT", f"{student_id} on {shard}")
        return {"student_id": student_id, "shard": shard, "status": "deleted"}
    except HTTPException: raise
    except Exception as exc: db_error(exc)


@app.get("/api/explorer")
def explorer():
    return [{"database": "shard_db", "tables": ["students"]}]


@app.get("/api/replication")
def replication():
    configs = {item["config_key"]: item["config_value"] for item in get_cluster_config()}
    return {"enabled": configs.get("replication_enabled", "false").lower() == "true", "items": []}


@app.get("/api/migrations")
def migrations():
    conn = connect_to_metadata()
    try:
        cur = conn.cursor(dictionary=True); cur.execute("SELECT * FROM migration_jobs ORDER BY job_id DESC"); return cur.fetchall()
    finally: conn.close()


@app.post("/api/query")
def execute_query(body: dict):
    sql = str(body.get("sql", "")).strip().rstrip(";")
    if not sql or ";" in sql or not re.match(r"(?is)^select\s+", sql):
        raise HTTPException(400, "Query Console accepts one read-only SELECT statement")
    if not re.search(r"(?i)\bFROM\s+students\b", sql):
        raise HTTPException(400, "Queries must read from the students table")
    # Fan out SELECT over all healthy shards, then merge results.
    results = []
    for node in get_all_nodes():
        try: results.extend(rows_on_shard(node["node_name"], sql))
        except (mysql.connector.InterfaceError, mysql.connector.OperationalError, ValueError): continue
        except mysql.connector.Error as exc: raise HTTPException(400, f"MySQL rejected query: {exc.msg}")
    return {"columns": list(results[0].keys()) if results else [], "rows": results, "row_count": len(results)}


@app.get("/api/config")
def config(): return get_cluster_config()
