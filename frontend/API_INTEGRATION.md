# Backend integration

The Python project has no HTTP server or route handlers. Its modules connect
directly to MySQL, and `student_operations.py` is an interactive CLI. The
frontend cannot read or change database state until an HTTP API is added.

The interface does not include fabricated node, shard, query, replication, or
migration records. Query execution is disabled, and database mutations are not
offered. Empty tables explain the missing API. The Settings connection check
requests only the configured base URL; it reports HTTP reachability and does
not claim that database API routes exist.

`src/services/api.js` contains an Axios client and service stubs. Set
`VITE_API_BASE_URL` in a local `.env` file (copy `.env.example`) to configure
the base URL. This setting is not a credential store.

To enable live pages, add documented HTTP routes and response schemas to the
backend for:

- Node inventory, status, add, and remove.
- Shard allocation, record counts, and consistent hash ring metadata.
- Query execution and structured result/error responses.
- Database/table listing, schema inspection, and paginated record browsing.
- Replication state and event history.
- Migration history and a separately protected execution action.
- Database/API health and any metrics the UI should display.
