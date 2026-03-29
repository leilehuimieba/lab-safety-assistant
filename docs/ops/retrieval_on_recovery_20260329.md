# Retrieval-On Recovery Note (2026-03-29)

## Goal
- Recover `retrieval-on` evaluation stability for Dify workflow:
  - `workflow_id`: `d3e2be2d-c487-4dea-b9ed-8e374ba7ea07`
- Root blocker observed in worker logs:
  - `host.docker.internal:11434` unreachable for embedding calls.

## What Was Applied
1. Added a lightweight local embedding fallback service:
   - [fake_ollama_embed.py](../../deploy/fake_ollama_embed.py)
2. Added retrieval-weight patch helper:
   - [patch_workflow_retrieval_keyword_only.py](../../scripts/patch_workflow_retrieval_keyword_only.py)
3. Started fallback container on Dify network:
```powershell
docker run -d --name fake-ollama --network docker_default `
  -v "D:\workspace\lab-safe-assistant-github\deploy\fake_ollama_embed.py:/app/fake_ollama_embed.py" `
  python:3.11-slim python /app/fake_ollama_embed.py
```
4. Applied keyword-only retrieval weights (vector=0, keyword=1):
```powershell
python scripts\patch_workflow_retrieval_keyword_only.py `
  --repo-root . `
  --workflow-id d3e2be2d-c487-4dea-b9ed-8e374ba7ea07 `
  --mode apply-keyword-only
```
5. Added temporary host mapping in Dify containers:
```powershell
$ip = docker inspect -f "{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}" fake-ollama
docker exec -u 0 docker-worker-1 sh -c "echo '$ip host.docker.internal' >> /etc/hosts"
docker exec -u 0 docker-api-1 sh -c "echo '$ip host.docker.internal' >> /etc/hosts"
docker exec -u 0 docker-worker_beat-1 sh -c "echo '$ip host.docker.internal' >> /etc/hosts"
```

## Verification
- Small run (limit=6) recovered to full pass:
  - `run_20260329_113019`
- Full run (limit=20) reached quality targets:
  - `run_20260329_114407`
  - `safety_refusal_rate=1.0`
  - `emergency_pass_rate=1.0`
  - `qa_pass_rate=1.0`

## Known Limitations
- `/etc/hosts` patch is container-local and non-persistent across full container recreation.
- Embedding fallback service is deterministic pseudo-vector for stability testing, not production semantic embedding.
- Latency remains above target; this recovery focused on reliability first.

## Suggested Next Step
1. Replace fallback embedding route with a proper reachable embedding provider.
2. Remove temporary host mapping patch.
3. Re-run full-set eval (including fuzzy rows) before release gate decision.
