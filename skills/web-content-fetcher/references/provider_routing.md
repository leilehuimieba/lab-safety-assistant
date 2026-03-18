# Provider Routing

## Default Order

1. `jina`
2. `scrapling`
3. `direct`

## Domain-Based Override

Move `scrapling` to first when URL host is likely to block reader-mode extraction:

- `weixin.qq.com`
- `mp.weixin.qq.com`
- `xiaohongshu.com`

## Stop Conditions

- `status=ok`: stop and return result.
- `status=blocked`: stop and return explicit blocked reason.
- `status=error`: continue to next provider.

## Quality Hint

The script computes `quality_score` from:

- extracted length
- sentence density
- text density

Use this value for downstream triage:

- `>= 0.65`: good for summarization and ingestion
- `0.35~0.65`: usable, recommend spot-check
- `< 0.35`: likely low quality, send to manual review queue

