from __future__ import annotations

"""知识库检索与规则匹配服务

- retrieve_citations: 基于 token 匹配 + 语义检索（bge-m3）混合打分检索 KB 条目
- match_rule: 按 severity、命中数和规则顺序匹配安全规则
- should_enforce_terminal_rule: 判断是否触发终止动作（refuse / redirect_emergency / ask_for_more_info）
"""

import os
from typing import Any

from ..models import Citation
from ..repositories import (
    DEFAULT_TOP_K,
    SEVERITY_SCORE,
    TERMINAL_ACTIONS,
    REFUSE_INTENT_MARKERS,
    EMERGENCY_INTENT_MARKERS,
    normalize_search_text,
    extract_tokens,
    get_kb_entries,
    get_rules_config,
    KB_FILE,
)

# 语义检索可选依赖：未安装时自动 fallback 到纯文本检索
try:
    from libs.embedding_utils import semantic_search

    _EMBEDDING_AVAILABLE = True
except ImportError:  # pragma: no cover
    _EMBEDDING_AVAILABLE = False

_EMBEDDING_CACHE_DIR = KB_FILE.parent / ".cache" / "embedding"
_SEMANTIC_WEIGHT = float(os.getenv("SEMANTIC_WEIGHT", "12.0"))


def retrieve_citations(question: str, top_k: int = DEFAULT_TOP_K) -> list[Citation]:
    entries = get_kb_entries()

    # ---- 语义检索（可选） ----
    semantic_scores: dict[str, float] = {}
    if _EMBEDDING_AVAILABLE and entries:
        try:
            mtime = os.path.getmtime(KB_FILE) if KB_FILE.exists() else 0.0
            texts = [
                " ".join(
                    [
                        row.get("title", ""),
                        row.get("question", ""),
                        row.get("answer", ""),
                        row.get("steps", ""),
                        row.get("forbidden", ""),
                        row.get("emergency", ""),
                        row.get("ppe", ""),
                        row.get("hazard_types", ""),
                        row.get("tags", ""),
                    ]
                )
                for row in entries
            ]
            semantic_results = semantic_search(
                query=question,
                entries=entries,
                texts=texts,
                cache_dir=_EMBEDDING_CACHE_DIR,
                kb_file_mtime=mtime,
                top_k=max(1, top_k) * 3,
            )
            if semantic_results:
                for score, row in semantic_results:
                    semantic_scores[row.get("id", "")] = score
        except Exception:
            pass  # fallback 到纯文本检索

    # ---- 文本检索（原有逻辑） ----
    q = normalize_search_text(question)
    q_tokens = extract_tokens(question)
    scored: list[tuple[float, dict[str, str]]] = []
    for row in entries:
        score = 0.0
        blob = row.get("blob", "")
        title_blob = row.get("title_blob", "")
        tag_blob = row.get("tag_blob", "")
        body_blob = row.get("body_blob", "")
        row_question = normalize_search_text(row.get("question", ""))
        row_title = normalize_search_text(row.get("title", ""))
        if row_question and row_question == q:
            score += 10.0
        elif row_question and (row_question in q or q in row_question):
            score += 5.2
        if row_title and row_title == q:
            score += 8.0
        elif row_title and (row_title in q or q in row_title):
            score += 4.0
        for token in q_tokens:
            if token in title_blob:
                score += 1.9 + min(len(token), 4) * 0.2
            elif token in tag_blob:
                score += 1.35 + min(len(token), 4) * 0.15
            elif token in body_blob:
                score += 0.95 + min(len(token), 4) * 0.11
            elif token in blob:
                score += 0.65 + min(len(token), 4) * 0.08

        # ---- 混合加权：语义分数加成 ----
        sem_score = semantic_scores.get(row.get("id", ""), 0.0)
        if sem_score > 0:
            score += sem_score * _SEMANTIC_WEIGHT

        if score > 0:
            scored.append((score, row))
    scored.sort(key=lambda item: item[0], reverse=True)
    selected = scored[: max(1, top_k)]
    if not selected:
        selected = [(0.1, row) for row in get_kb_entries()[: max(1, top_k)]]

    citations: list[Citation] = []
    for score, row in selected:
        snippet = " ".join(
            part for part in [row.get("answer", ""), row.get("steps", ""), row.get("forbidden", "")] if part
        )[:220]
        citations.append(
            Citation(
                kb_id=row.get("id", ""),
                title=row.get("title", ""),
                source_title=row.get("source_title", ""),
                source_org=row.get("source_org", ""),
                source_url=row.get("source_url", ""),
                risk_level=row.get("risk_level", ""),
                snippet=snippet,
                score=round(score, 3),
            )
        )
    return citations


def match_rule(question: str) -> dict[str, Any] | None:
    q = normalize_search_text(question)
    best: dict[str, Any] | None = None
    for order, rule in enumerate(get_rules_config().get("rules") or []):
        if not isinstance(rule, dict):
            continue
        patterns = [str(item).strip() for item in (rule.get("patterns") or []) if str(item).strip()]
        hits = [pattern for pattern in patterns if normalize_search_text(pattern) in q]
        if not hits:
            continue
        severity = str(rule.get("severity") or "low").lower()
        candidate = {
            "id": str(rule.get("id") or ""),
            "action": str(rule.get("action") or "safe_answer"),
            "severity": severity,
            "response": str(rule.get("response") or ""),
            "score": (SEVERITY_SCORE.get(severity, 1), len(hits), -order),
        }
        if best is None or candidate["score"] > best["score"]:
            best = candidate
    return best


def should_enforce_terminal_rule(question: str, rule: dict[str, Any] | None) -> bool:
    if not rule:
        return False
    action = str(rule.get("action") or "").strip()
    if action not in TERMINAL_ACTIONS:
        return False
    q = normalize_search_text(question)
    category = str(rule.get("id") or "")

    if action == "ask_for_more_info":
        return True

    if action == "refuse":
        always_refuse = {"R-006", "R-007", "R-023", "R-024"}
        if category in always_refuse:
            return True
        return any(marker in q for marker in REFUSE_INTENT_MARKERS)

    if action == "redirect_emergency":
        return any(marker in q for marker in EMERGENCY_INTENT_MARKERS)

    return False
