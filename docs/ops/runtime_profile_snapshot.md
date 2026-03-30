# Runtime Profile Snapshot

- Generated: `2026-03-30T21:03:46+08:00`
- Hostname: `VM-0-11-ubuntu`
- Platform: `Linux-6.8.0-49-generic-x86_64-with-glibc2.39`
- Python: `3.12.3`

## Git
- Branch: `main`
- HEAD: `bf8f3f690d94d30f2cada0597af4db1128c51a0d`
- Dirty: `True`

## Env (Sanitized)
- `DIFY_API_BASE` = `http://127.0.0.1:8080`
- `DIFY_API_CONTAINER` = `docker-api-1`
- `DIFY_APP_TOKEN` = `app***KX1`
- `DIFY_ENDPOINT_MODEL_NAME` = `gpt-5.2-codex`
- `DIFY_ENDPOINT_URL` = `http://ai.little100.cn:3000/v1`
- `DIFY_FALLBACK_MODEL` = `gpt-5.2-codex`
- `DIFY_MODEL_NAME` = `gpt-5.2-codex`
- `DIFY_MODEL_TYPE` = `text-generation`
- `DIFY_PROVIDER_NAME` = `langgenius/openai_api_compatible/openai_api_compatible`
- `DIFY_SMOKE_QUERY` = `What should I do first if chemical spill happens in lab?`
- `DIFY_SMOKE_TIMEOUT_SEC` = `240`
- `DIFY_SMOKE_USER` = `go-live-bundle`
- `DIFY_TENANT_ID` = `7980ac46-b7f0-4f67-b94e-fbcc0bf48a46`
- `DIFY_WORKFLOW_ID` = `d3e2be2d-c487-4dea-b9ed-8e374ba7ea07`
- `OPENAI_COMPAT_API_KEY` = `sk-***j2L`
- `RELEASE_DIR` = `release_exports/v8.1`
- `RELEASE_POLICY_ENFORCE_SECONDARY` = `0`
- `RELEASE_POLICY_PROFILE` = `demo`
- `RELEASE_POLICY_RUN_SECONDARY` = `0`
- `RELEASE_POLICY_SECONDARY_PROFILE` = `prod`
- `RELEASE_POLICY_STRICT` = `0`
- `STABILITY_DIFY_TIMEOUT` = `90`
- `STABILITY_EVAL_CONCURRENCY` = `1`
- `STABILITY_FAILOVER_DAYS` = `1`
- `STABILITY_FAIL_STREAK_THRESHOLD` = `2`
- `STABILITY_INTERVAL_SEC` = `5`
- `STABILITY_LIMIT` = `3`
- `STABILITY_RETRY_ON_TIMEOUT` = `1`
- `STABILITY_ROUNDS` = `1`
- `STABILITY_SKIP_CANARY` = `1`
- `STABILITY_SKIP_HEALTH_CHECK` = `0`
- `WEB_HEALTH_URL` = `http://127.0.0.1:8088/health`

## Docker Containers
- `fake-ollama` | `python:3.11-slim` | `Up 3 hours`
- `docker-plugin_daemon-1` | `langgenius/dify-plugin-daemon:0.5.3-local` | `Up 6 hours`
- `docker-api-1` | `langgenius/dify-api:1.13.0` | `Up 6 hours`
- `docker-worker_beat-1` | `langgenius/dify-api:1.13.0` | `Up 6 hours`
- `docker-worker-1` | `langgenius/dify-api:1.13.0` | `Up 6 hours`
- `docker-nginx-1` | `nginx:latest` | `Up 6 hours`
- `docker-web-1` | `langgenius/dify-web:1.13.0` | `Up 7 hours`
- `docker-sandbox-1` | `langgenius/dify-sandbox:0.2.12` | `Restarting (2) 8 seconds ago`
- `docker-db_postgres-1` | `postgres:15-alpine` | `Up 7 hours (healthy)`
- `docker-redis-1` | `redis:6-alpine` | `Up 7 hours (healthy)`
- `docker-ssrf_proxy-1` | `ubuntu/squid:latest` | `Up 7 hours`
- `docker-qdrant-1` | `langgenius/qdrant:v1.8.3` | `Up 7 hours`
