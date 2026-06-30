# Production secrets

This directory holds plain-text secret files mounted into containers
via Compose `secrets:` (see `compose.prod.yaml`). Compose mounts each
file at `/run/secrets/<name>` with mode `0400`, owned by root.

**Never commit anything here.** `secrets/.gitignore` blocks every file
in this directory except itself and this README.

## Expected files

Names below match the secret names in `compose.prod.yaml` and the
Pydantic field names in `seedbank.core.config.Settings` (lowercase, no
extension). `Settings(secrets_dir="/run/secrets")` reads each file
whose name matches a field; values that don't map to a field (e.g.
`postgres_password`, `grafana_admin_password`) are consumed by the
upstream image directly.

| File | Consumed by | How |
|---|---|---|
| `postgres_password` | postgres, api/workers | postgres reads `POSTGRES_PASSWORD_FILE`; api/workers read it inside an entrypoint shim |
| `jwt_secret` | api, workers | Pydantic `secrets_dir` → `Settings.jwt_secret` |
| `minio_access_key` | api, workers, minio | Pydantic + entrypoint shim (minio) |
| `minio_secret_key` | api, workers, minio | Pydantic + entrypoint shim (minio) |
| `clickhouse_password` | api, workers, clickhouse | Pydantic + entrypoint shim (clickhouse) |
| `roboflow_api_key` | api, workers | Pydantic `secrets_dir` (optional — file may be empty) |
| `sentry_dsn` | api, workers | Pydantic `secrets_dir` (optional — omit file to disable Sentry) |
| `grafana_admin_password` | grafana | `GF_SECURITY_ADMIN_PASSWORD__FILE` |

## First-time setup

```bash
cd secrets
umask 077
printf '%s' "$(openssl rand -hex 32)"            > jwt_secret
printf '%s' "$(openssl rand -base64 24)"         > postgres_password
printf '%s' "$(openssl rand -base64 24)"         > clickhouse_password
printf '%s' "$(openssl rand -base64 24)"         > grafana_admin_password
printf '%s' "seedbank"                           > minio_access_key
printf '%s' "$(openssl rand -base64 32)"         > minio_secret_key
printf '%s' ""                                   > roboflow_api_key
printf '%s' ""                                   > sentry_dsn
chmod 0400 *
```

Use `printf` (no trailing newline) over `echo`. Pydantic's secrets
loader strips trailing whitespace, but the upstream `_FILE`
conventions (Postgres, Grafana) read the file verbatim — a stray `\n`
is part of the password.

## Permission audit

`make secrets-check` walks this directory and fails if any file is
missing, world/group readable, or not exactly `0400`.

## Rotation

Replace the file, then restart the consuming container(s):

```bash
docker compose -f compose.yaml -f compose.prod.yaml restart api worker-cpu worker-inference
```

Postgres password rotation is a two-step (rotate the role first with
`ALTER USER`, then update the file and restart). There is no live
secret reload — `Settings` is constructed once per process.
