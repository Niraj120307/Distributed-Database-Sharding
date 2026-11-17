# ShardX — Distributed Database Sharding Engine

ShardX is a React dashboard backed by a FastAPI service and four independent MySQL shard databases plus one metadata database. Student records are horizontally partitioned: `student_id % 4` selects the primary shard from the fixed configured node list. A student ID is never stored as a primary on another shard. Scatter/gather reads query reachable shards and merge the results.

## Requirements

- Docker Desktop with its Linux container engine running; Compose v2 (`docker compose`)
- Node.js 18+ and npm (only needed to run the Vite development server locally)
- MySQL Workbench (optional, for inspecting physical shard storage)

The root `.env` already contains `MYSQL_ROOT_PASSWORD`. Change it to a strong local password before use. Keep `.env` private; do not commit it. The same password is used by Compose and the API.

## Start the complete stack

From the repository root:

```powershell
docker compose up --build -d
docker compose ps
docker compose logs -f backend
```

The services are four MySQL shards, one metadata database, and the API. On first start, MySQL creates `shard_db` on each shard and `cluster_metadata` on the metadata service. SQL initialization creates the student schema, indexes, node/config tables, and migration history. The API registers all four nodes and applies compatible schema upgrades to existing named Docker volumes. Wait for the API log to show Uvicorn running, then open `http://localhost:8000/health` or API docs at `http://localhost:8000/docs`.

Start the existing UI in a second terminal:

```powershell
cd frontend
npm install
npm run dev
```

Open the Vite URL printed by npm, usually `http://localhost:5173`. Settings defaults to `http://localhost:8000`; use **Test connection** to verify API and MySQL connectivity. To build the UI, run `npm run build` from `frontend`.

To stop the services while retaining records, run `docker compose down`. To erase every database and start from empty volumes, run `docker compose down -v` (this permanently deletes stored records).

## MySQL Workbench connections

Create five MySQL connections (Standard TCP/IP):

| Connection | Hostname | Port | Username | Password | Schema |
|---|---|---:|---|---|---|
| Shard 1 | `127.0.0.1` | `3307` | `root` | `.env` value | `shard_db` |
| Shard 2 | `127.0.0.1` | `3308` | `root` | `.env` value | `shard_db` |
| Shard 3 | `127.0.0.1` | `3309` | `root` | `.env` value | `shard_db` |
| Shard 4 | `127.0.0.1` | `3311` | `root` | `.env` value | `shard_db` |
| Metadata | `127.0.0.1` | `3310` | `root` | `.env` value | `cluster_metadata` |

Use **Test Connection**, then open the connection and select the listed schema. Each shard is an independent MySQL server; identical schema names do not mean shared storage.

## Verify real shard distribution

1. In the UI, open **Data Explorer** and add records with IDs `1001`, `1002`, `1003`, and `1004` (name, email, and department are required). The API response routes them by modulo across four active shards.
2. In Workbench, run this on each shard connection:

   ```sql
   SELECT student_id, name, email, department, is_replica
   FROM shard_db.students
   ORDER BY student_id;
   ```

   IDs 1001, 1002, 1003, and 1004 should appear respectively on shard 2, 3, 4, and 1 (the numeric suffix is one-based; route is `(ID % 4) + 1`). Each ID should appear on one shard as a primary (`is_replica = 0`).
3. Run the aggregate on each connection and compare counts:

   ```sql
   SELECT @@port AS connected_port, COUNT(*) AS primary_records
   FROM shard_db.students WHERE is_replica = 0;
   ```

4. Search those IDs in **Data Explorer** or run the default SELECT in **Query Console** to see the API scatter/gather across shards.
5. Update and delete a record from Data Explorer. Re-run the Workbench queries to confirm MySQL changed. CRUD endpoints are also documented at `/docs`.

The metadata schema has `shard_nodes`, `cluster_config`, `migration_jobs`, and `migration_records`. Shard tables have indexes for email, department, and primary/replica lookup. The Query Console only accepts read-only SELECT statements against `students`; writes go through CRUD endpoints so shard-key routing remains enforced.

## Node failure behavior

Stop a shard container, then refresh the UI or request `http://localhost:8000/health`. The failed node is marked `INACTIVE` in metadata. Reads scatter to remaining reachable shards; writes whose fixed shard-key destination is unavailable fail rather than silently moving existing IDs to a different shard. Restart its container, open **Nodes**, and choose **Enable** for that node. Re-enabling a node does not rebalance records. Rebalancing is an explicit operation and should be performed after inspecting a dry run.

```powershell
docker compose stop shard2
docker compose start shard2
```

For direct API checks: `GET /health`, `GET /api/dashboard`, `GET /api/nodes`, `GET /api/shards`, `GET /api/students`, `POST /api/students`, `PUT /api/students/{id}`, and `DELETE /api/students/{id}`. FastAPI interactive docs at `/docs` provide request forms. The API manages node active/inactive status; adding physical databases requires adding a Compose service and node configuration.

## Local backend development (without API container)

Keep the MySQL Compose services running and install backend dependencies:

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn api:app --reload --host 0.0.0.0 --port 8000
```

Local Python expects MySQL on host ports above. Use only one backend at a time (container or local) because both use port 8000.

## Project map

- `backend/api.py` — HTTP API, health checks, CRUD, dashboards, query endpoint
- `backend/shard_router.py` — shard-key routing
- `backend/database.py`, `backend/metadata_manager.py` — MySQL connections and node metadata
- `sql/init.sql`, `sql/metadata_init.sql` — fresh database schemas
- `docker-compose.yml` — four independent shards, metadata database, API service
- `frontend/src` — existing React UI and API integration

If initialization fails after a password change while old volumes remain, the MySQL volume still contains the old credentials. Either restore the original password or deliberately recreate the volumes with `docker compose down -v`; that command deletes database contents.
