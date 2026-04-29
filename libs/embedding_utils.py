"""本地 Embedding 工具（bge-m3）

提供基于 sentence-transformers 或 Ollama API 的语义检索能力：
- 自动加载本地或 HuggingFace 上的 bge-m3 模型
- 为知识库条目预计算 Embedding 并持久化到 .cache/embedding/
- 通过 numpy 矩阵乘法实现高效的 cosine-similarity top-k 检索
- 所有异常均内部捕获，调用方可安全 fallback 到文本检索
"""

from __future__ import annotations

import os
import pickle
import threading
from pathlib import Path
from typing import Any

import numpy as np

try:
    from sentence_transformers import SentenceTransformer

    ST_AVAILABLE = True
except ImportError:  # pragma: no cover
    ST_AVAILABLE = False

try:
    import requests

    REQUESTS_AVAILABLE = True
except ImportError:  # pragma: no cover
    REQUESTS_AVAILABLE = False

EMBEDDING_BACKEND = os.getenv("EMBEDDING_BACKEND", "sentence-transformers")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "BAAI/bge-m3")
EMBEDDING_DEVICE = os.getenv("EMBEDDING_DEVICE", "cpu")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

_lock = threading.Lock()
_model: Any = None
_index_states: dict[str, dict[str, Any]] = {}


def _get_model() -> Any:
    """懒加载 SentenceTransformer 模型（单例线程安全）。"""
    global _model
    if _model is not None:
        return _model
    if not ST_AVAILABLE or os.getenv("ENABLE_EMBEDDING", "1") != "1":
        return None
    with _lock:
        if _model is not None:
            return _model
        try:
            _model = SentenceTransformer(EMBEDDING_MODEL, device=EMBEDDING_DEVICE)
        except Exception:
            _model = None
        return _model


def _encode_texts_ollama(texts: list[str], batch_size: int = 32) -> np.ndarray | None:
    """通过 Ollama /api/embed 批量获取 embedding 并归一化。"""
    if not REQUESTS_AVAILABLE or not texts:
        return None
    url = f"{OLLAMA_BASE_URL}/api/embed"
    all_embeddings: list[list[float]] = []
    try:
        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]
            resp = requests.post(url, json={"model": EMBEDDING_MODEL, "input": batch}, timeout=300)
            resp.raise_for_status()
            data = resp.json()
            embeddings = data.get("embeddings", [])
            if len(embeddings) != len(batch):
                return None
            all_embeddings.extend(embeddings)
        arr = np.array(all_embeddings, dtype=np.float32)
        norms = np.linalg.norm(arr, axis=1, keepdims=True) + 1e-10
        return arr / norms
    except Exception:
        return None


def _encode_texts(texts: list[str], batch_size: int = 32) -> np.ndarray | None:
    """批量编码文本为归一化 Embedding 向量。"""
    if EMBEDDING_BACKEND == "ollama":
        return _encode_texts_ollama(texts, batch_size)

    model = _get_model()
    if model is None or not texts:
        return None
    try:
        embeddings = model.encode(
            texts,
            batch_size=batch_size,
            show_progress_bar=False,
            normalize_embeddings=True,
            convert_to_numpy=True,
        )
        return np.asarray(embeddings, dtype=np.float32)
    except Exception:
        return None


def _load_cached_index(cache_dir: Path) -> dict[str, Any] | None:
    """从本地缓存加载 embedding 矩阵和元数据。"""
    emb_path = cache_dir / "embeddings.npy"
    meta_path = cache_dir / "meta.pkl"
    if not emb_path.exists() or not meta_path.exists():
        return None
    try:
        embeddings = np.load(emb_path)
        with open(meta_path, "rb") as f:
            meta = pickle.load(f)
        return {"embeddings": embeddings, "mtime": meta.get("mtime"), "count": meta.get("count")}
    except Exception:
        return None


def _save_cached_index(embeddings: np.ndarray, mtime: float, count: int, cache_dir: Path) -> None:
    """将 embedding 矩阵和元数据持久化到本地缓存。"""
    cache_dir.mkdir(parents=True, exist_ok=True)
    np.save(cache_dir / "embeddings.npy", embeddings)
    with open(cache_dir / "meta.pkl", "wb") as f:
        pickle.dump({"mtime": mtime, "count": count}, f)


def build_kb_index(texts: list[str], kb_file_mtime: float, cache_dir: Path) -> np.ndarray | None:
    """为知识库文本列表构建 embedding 索引并缓存。"""
    embeddings = _encode_texts(texts)
    if embeddings is None:
        return None
    _save_cached_index(embeddings, kb_file_mtime, len(texts), cache_dir)
    return embeddings


def semantic_search(
    query: str,
    entries: list[dict[str, str]],
    texts: list[str],
    cache_dir: Path,
    kb_file_mtime: float,
    top_k: int = 10,
) -> list[tuple[float, dict[str, str]]] | None:
    """基于 bge-m3 的语义检索。

    返回 (cosine_similarity, entry) 列表，按相似度降序。
    如果依赖不可用、模型加载失败或发生异常，返回 None，调用方应 fallback 到文本检索。
    """
    global _index_states
    if os.getenv("ENABLE_EMBEDDING", "1") != "1":
        return None
    if EMBEDDING_BACKEND == "sentence-transformers" and not ST_AVAILABLE:
        return None
    if EMBEDDING_BACKEND == "ollama" and not REQUESTS_AVAILABLE:
        return None

    cache_key = str(cache_dir)
    with _lock:
        state = _index_states.get(cache_key)
        need_rebuild = (
            state is None
            or state.get("mtime") != kb_file_mtime
            or state.get("count") != len(entries)
        )
        if need_rebuild:
            cached = _load_cached_index(cache_dir)
            if cached and cached["mtime"] == kb_file_mtime and cached["count"] == len(entries):
                state = {
                    "embeddings": cached["embeddings"],
                    "entries": entries,
                    "mtime": kb_file_mtime,
                    "count": len(entries),
                }
            else:
                embeddings = build_kb_index(texts, kb_file_mtime, cache_dir)
                if embeddings is None:
                    _index_states.pop(cache_key, None)
                    return None
                state = {
                    "embeddings": embeddings,
                    "entries": entries,
                    "mtime": kb_file_mtime,
                    "count": len(entries),
                }
            _index_states[cache_key] = state

    if state is None:
        return None

    embeddings: np.ndarray = state["embeddings"]
    q_emb = _encode_texts([query])
    if q_emb is None:
        return None

    # embeddings 已归一化，点积即 cosine similarity
    scores = (embeddings @ q_emb.T).flatten()
    top_indices = np.argsort(scores)[::-1][:top_k]

    results: list[tuple[float, dict[str, str]]] = []
    for idx in top_indices:
        score = float(scores[idx])
        if score <= 0:
            continue
        results.append((score, entries[idx]))
    return results
