# Local infrastructure

Run `make configure-local` once to generate ignored unique credentials, then `make infra-check` and `make infra-up`. Data volumes persist across `make infra-down`; no deletion target is supplied. `make stack-up` builds/starts the API and dashboard with backing services. All published ports bind to loopback.

| Service             | Host address                    | Scope                                                        |
| ------------------- | ------------------------------- | ------------------------------------------------------------ |
| Dashboard           | http://127.0.0.1:3000           | app profile                                                  |
| API                 | http://127.0.0.1:8000           | app profile; liveness is not execution readiness             |
| PostgreSQL          | 127.0.0.1:15432                 | Generated credentials; Alembic baseline only                 |
| Redis               | Internal service network        | No host port or product scheduler yet                        |
| MinIO API / console | http://127.0.0.1:19000 / :19001 | Generated credentials; no automatic evidence ingestion       |
| Prometheus          | http://127.0.0.1:19090          | monitoring profile; actual HTTP counter only                 |
| Grafana             | http://127.0.0.1:13001          | monitoring profile; generated admin password                 |
| TLS relay           | https://localhost:18443         | app + relay profiles; requires supplied trusted certificates |

MinIO uses its documented [Quay container registry](https://min.io/docs/minio/container/operations/install-deploy-manage/deploy-minio-single-node-single-drive.html), with an explicit release tag. The initial Docker Hub pull was unavailable on this machine; no storage mock was substituted. Pin reviewed image digests and re-evaluate upstream maintenance/security during P10 before production deployment. These images and plaintext internal service connections are for the isolated local development stack.

`docker compose --env-file .env -f infra/docker/compose.yaml --profile app --profile monitoring up -d` enables monitoring. `relay` requires the certificates described in `nginx/README.md`. Do not claim TLS/mTLS acceptance from config validation alone. Runtime OTLP wiring and tenant-scoped object storage are future work.
