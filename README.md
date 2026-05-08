# IMS

Incident Management System (IMS) that ingests failure signals, deduplicates incidents, and serves a real-time dashboard.

## Quick Start

1. Start services:

```bash
docker compose up -d
```

2. Verify containers are running:

```bash
docker compose ps
```

3. Open the dashboard shell:

- http://localhost:3000

## Services

- API: http://localhost:8000
- Kafka: localhost:9092
- Redis: localhost:6379
- MongoDB: localhost:27017
- PostgreSQL/TimescaleDB: localhost:5432

## Notes

- Database schemas are initialized by [backend/db/init.sql](backend/db/init.sql).
- The worker is a placeholder until the Kafka pipeline is implemented.
