"""
Embedding module for semantic retrieval.

Uses sentence-transformers for encoding medical text into embeddings.
Optimized for medical domain with lightweight model (all-MiniLM-L6-v2).
"""
from __future__ import annotations

import logging
import numpy as np
from typing import Optional

logger = logging.getLogger(__name__)

try:
    from sentence_transformers import SentenceTransformer
    SEMANTIC_SEARCH_AVAILABLE = True
except Exception as exc:
    SentenceTransformer = None  # type: ignore[assignment]
    SEMANTIC_SEARCH_AVAILABLE = False
    logger.warning(
        "[embeddings] sentence_transformers unavailable, semantic search disabled: %s",
        exc,
    )

# Global embedding model (lazy-loaded)
_EMBEDDING_MODEL: Optional[SentenceTransformer] = None # pyright: ignore[reportInvalidTypeForm]

# Model configuration
MODEL_NAME = "all-MiniLM-L6-v2"
EMBEDDING_DIMENSION = 384


def get_embedding_model() -> Optional[SentenceTransformer]: # pyright: ignore[reportInvalidTypeForm]
    """
    Load and cache the embedding model.
    Returns None if loading fails or the sentence-transformers package is unavailable.
    """
    global _EMBEDDING_MODEL

    if _EMBEDDING_MODEL is not None:
        return _EMBEDDING_MODEL

    if not SEMANTIC_SEARCH_AVAILABLE or SentenceTransformer is None:
        logger.warning(
            "[embeddings] sentence_transformers unavailable, semantic search is disabled"
        )
        return None

    try:
        logger.info("[embeddings] loading model: %s", MODEL_NAME)
        _EMBEDDING_MODEL = SentenceTransformer(MODEL_NAME)
        logger.info("[embeddings] model loaded successfully (dimension=%d)", EMBEDDING_DIMENSION)
        return _EMBEDDING_MODEL
    except Exception as exc:
        logger.error("[embeddings] failed to load model %s: %s", MODEL_NAME, exc)
        return None


def embed_text(text: str) -> Optional[np.ndarray]:
    """
    Embed a single text string into a vector (L2 normalized).
    """
    if not text or not isinstance(text, str):
        return None

    model = get_embedding_model()
    if model is None:
        logger.warning("[embeddings] model not loaded, cannot embed text")
        return None

    try:
        text = text.strip()
        if not text:
            return None

        # Encode (internal normalization)
        embedding = model.encode(text, convert_to_numpy=True, normalize_embeddings=True)
        return embedding.astype(np.float32)
    except Exception as exc:
        logger.error("[embeddings] embedding failed for text '%s': %s", text[:50], exc)
        return None


def embed_texts_batch(texts: list[str]) -> list[Optional[np.ndarray]]:
    """
    Embed multiple texts efficiently (L2 normalized).
    """
    if not texts:
        return []

    model = get_embedding_model()
    if model is None:
        logger.warning("[embeddings] model not loaded, cannot embed batch")
        return [None] * len(texts)

    try:
        # Filter out empty texts but track their indices
        valid_texts = []
        indices_map = []
        for i, text in enumerate(texts):
            if text and isinstance(text, str):
                text = text.strip()
                if text:
                    valid_texts.append(text)
                    indices_map.append(i)

        if not valid_texts:
            return [None] * len(texts)

        # Embed all valid texts with normalization
        embeddings_array = model.encode(valid_texts, convert_to_numpy=True, normalize_embeddings=True)
        embeddings_array = embeddings_array.astype(np.float32)

        # Map back to original indices
        result = [None] * len(texts)
        for i, emb in enumerate(embeddings_array):
            result[indices_map[i]] = emb

        return result
    except Exception as exc:
        logger.error("[embeddings] batch embedding failed: %s", exc)
        return [None] * len(texts)


def similarity_score(embedding1: np.ndarray, embedding2: np.ndarray) -> float:
    """Compute cosine similarity between two embeddings"""
    if embedding1 is None or embedding2 is None:
        return 0.0

    try:
        # Normalize vectors
        e1 = embedding1.astype(np.float64)
        e2 = embedding2.astype(np.float64)

        norm1 = np.linalg.norm(e1)
        norm2 = np.linalg.norm(e2)

        if norm1 == 0 or norm2 == 0:
            return 0.0

        # Cosine similarity
        similarity = np.dot(e1, e2) / (norm1 * norm2)
        return float(np.clip(similarity, 0.0, 1.0))
    except Exception as exc:
        logger.error("[embeddings] similarity computation failed: %s", exc)
        return 0.0
