# Docker Compose

The canonical local topology remains at [`../compose.yaml`](../compose.yaml) for compatibility with `start.bat`, CI, and existing operator commands.

It builds `northstar/web` from `frontend/Dockerfile` and `northstar/api` from `backend/Dockerfile`. The shared backend image runs separate API, migration, Celery, dispatcher, outbox, analytics, and cleanup processes. PostgreSQL, Redis, RabbitMQ, Kafka, and MinIO remain independent infrastructure containers.

## Local object storage

MinIO's community distribution is source-only. `docker/minio/Dockerfile` builds an exact upstream commit from a checksum-verified archive using a pinned Go compiler and a non-root Alpine runtime. The SDK bootstrap uses the existing API image instead of the withdrawn `minio/mc` image. AWS staging and production use managed S3; this server is for local development and CI.

Fresh volumes are created for UID/GID 10001. For an existing volume created by the older root-owned image, migrate ownership once, preserving all object bytes and versions:

```sh
docker compose build minio
docker compose stop minio
docker compose run --rm --no-deps --user 0:0 --entrypoint sh minio -c 'chown -R 10001:10001 /data'
docker compose up -d minio minio-init
```

Run this from the intended Compose project and verify its volume before changing ownership. Do not remove or recreate the data volume. Other Compose projects do not require a change.
