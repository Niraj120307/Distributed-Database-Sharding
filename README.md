\# Distributed Database Sharding Engine



A Python and MySQL-based distributed database system that demonstrates database sharding, replication, dynamic node management, and data migration.



\## Features



\- \*\*Horizontal Sharding:\*\* Distributes student records across multiple MySQL nodes.

\- \*\*Hash Sharding:\*\* Routes records using a hash-based shard selection strategy.

\- \*\*Range Sharding:\*\* Supports range-based record distribution.

\- \*\*Consistent Hashing:\*\* Uses virtual nodes to reduce data redistribution when cluster nodes change.

\- \*\*Dynamic Node Management:\*\* Maintains shard information through a metadata database.

\- \*\*Data Migration:\*\* Moves records between shards and tracks migration jobs.

\- \*\*Data Replication:\*\* Maintains replica copies across different shard nodes.

\- \*\*CRUD Operations:\*\* Supports adding, viewing, searching, updating, and deleting student records.



\## Technology Stack



\- Python

\- MySQL 8.0

\- Docker and Docker Compose

\- mysql-connector-python

\- python-dotenv



\## Architecture



The system consists of:

1\. Application Layer – Handles student operations.

2\. Middleware Layer – Handles shard routing, query execution, migration, and replication.

3\. Metadata Layer – Stores shard configuration and node information.

4\. Storage Layer – Contains independent MySQL shard databases.



\## Project Structure



```text

Distributed-Database-Sharding/

├── backend/

├── frontend/

├── sql/

├── docs/

├── screenshots/

├── docker-compose.yml

├── .gitignore

└── README.md

```



\## Setup Instructions



1\. Clone the repository.

2\. Install Docker Desktop.

3\. Start the Docker containers:



```bash

docker compose up -d

```



4\. Create a Python virtual environment:



```bash

python -m venv venv

```



5\. Activate it:



```bash

venv\\Scripts\\activate

```



6\. Install dependencies:



```bash

pip install mysql-connector-python python-dotenv

```



7\. Configure the database credentials in a local `.env` file.

8\. Run the application:



```bash

python backend/student\_operations.py

```



\## Future Improvements



\- Distributed query optimization.

\- Automatic shard rebalancing.

\- Node failure detection and recovery.

\- Distributed query execution.

\- Performance benchmarking.

\- Web-based monitoring dashboard.



\## Disclaimer



This project is an educational prototype developed to demonstrate distributed database concepts. It is not intended to replace a production-grade distributed database system.



