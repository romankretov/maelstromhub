# Backend

Run tests:

```bash
go test ./...
```

Run locally against Docker Postgres/Redis:

```bash
go run ./cmd/server
```

The server runs migrations from `MIGRATIONS_DIR` or `backend/migrations` by default.
