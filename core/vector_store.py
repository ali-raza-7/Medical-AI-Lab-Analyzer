"""
Vector store layer for semantic retrieval.

Uses FAISS for efficient similarity search over medical knowledge base.
Persists embeddings to disk for fast startup and reduced computation.
"""
from __future__ import annotations

import logging
import os
import pickle
import numpy as np
from functools import lru_cache
from typing import Optional, NamedTuple
from pathlib import Path

try:
    import faiss
except ImportError:
    faiss = None

from core.embeddings import embed_text, embed_texts_batch, similarity_score, EMBEDDING_DIMENSION

logger = logging.getLogger(__name__)

# Storage configuration
VECTOR_STORE_DIR = Path(__file__).parent.parent / "data" / "vector_store"
INDEX_FILE = VECTOR_STORE_DIR / "faiss_index.bin"
METADATA_FILE = VECTOR_STORE_DIR / "metadata.pkl"


class DocumentMetadata(NamedTuple):
    """Metadata for a document in the vector store."""
    doc_id: str              # Unique identifier
    doc_type: str            # Type of document (test, pattern, definition, etc.)
    text: str                # Original text
    category: Optional[str]  # Optional category (e.g., CBC, Metabolic, etc.)


class VectorStore:
    """
    FAISS-based vector store for medical knowledge retrieval.
    
    Persists embeddings and metadata to disk for efficient reuse.
    Supports semantic similarity search with configurable k (top-k results).
    """
    
    def __init__(self):
        self.index: Optional[faiss.IndexFlatL2] = None
        self.documents: dict[int, DocumentMetadata] = {}
        self.doc_id_to_idx: dict[str, int] = {}
        self._embedding_count = 0
        self._loaded_from_disk = False
    
    def is_available(self) -> bool:
        """Check if vector store is properly initialized."""
        return self.index is not None and len(self.documents) > 0
    
    def add_document(
        self,
        doc_id: str,
        text: str,
        doc_type: str = "general",
        category: Optional[str] = None,
    ) -> bool:
        """
        Add a single document to the vector store.
        
        Args:
            doc_id: Unique document identifier
            text: Document text to embed
            doc_type: Type of document (test, pattern, definition, etc.)
            category: Optional category for bucketing
            
        Returns:
            True if successfully added, False otherwise
        """
        if doc_id in self.doc_id_to_idx:
            logger.debug("[vector_store] document %s already exists", doc_id)
            return False
        
        embedding = embed_text(text)
        if embedding is None:
            logger.warning("[vector_store] failed to embed document %s", doc_id)
            return False
        
        return self._add_embedding(
            doc_id=doc_id,
            embedding=embedding,
            text=text,
            doc_type=doc_type,
            category=category,
        )
    
    def add_documents_batch(
        self,
        documents: list[dict],
    ) -> int:
        """
        Batch add multiple documents efficiently.
        
        Each document dict should contain:
        - doc_id: unique identifier
        - text: text to embed
        - doc_type: (optional) document type
        - category: (optional) category
        
        Returns:
            Number of documents successfully added
        """
        if not documents:
            return 0
        
        # Extract texts in order
        texts = [doc.get("text", "") for doc in documents]
        embeddings_list = embed_texts_batch(texts)
        
        added_count = 0
        for i, (doc, embedding) in enumerate(zip(documents, embeddings_list)):
            if embedding is not None:
                success = self._add_embedding(
                    doc_id=doc.get("doc_id", ""),
                    embedding=embedding,
                    text=doc.get("text", ""),
                    doc_type=doc.get("doc_type", "general"),
                    category=doc.get("category", None),
                )
                if success:
                    added_count += 1
        
        logger.info("[vector_store] batch add: %d/%d documents added", added_count, len(documents))
        return added_count
    
    def _add_embedding(
        self,
        doc_id: str,
        embedding: np.ndarray,
        text: str,
        doc_type: str,
        category: Optional[str],
    ) -> bool:
        """Internal method to add embedding to index."""
        if not doc_id or doc_id in self.doc_id_to_idx:
            return False
        
        # Initialize index on first embedding
        if self.index is None:
            if faiss is None:
                logger.warning("[vector_store] cannot initialize FAISS index: faiss unavailable")
                return False
            try:
                self.index = faiss.IndexFlatL2(EMBEDDING_DIMENSION)
            except Exception as exc:
                logger.error("[vector_store] failed to create FAISS index: %s", exc)
                return False
        
        try:
            # Convert embedding to float32 and reshape for FAISS
            embedding = embedding.astype(np.float32).reshape(1, -1)
            
            # Add to index
            idx = self.index.ntotal
            self.index.add(embedding)
            
            # Store metadata
            metadata = DocumentMetadata(
                doc_id=doc_id,
                doc_type=doc_type,
                text=text,
                category=category,
            )
            self.documents[idx] = metadata
            self.doc_id_to_idx[doc_id] = idx
            self._embedding_count += 1
            
            return True
        except Exception as exc:
            logger.error("[vector_store] failed to add embedding for %s: %s", doc_id, exc)
            return False
    
    @lru_cache(maxsize=1024)
    def cached_search(
        self,
        query_text: str,
        k: int = 5,
        threshold: float = 0.0,
    ) -> list[tuple[str, float]]:
        """Cached version of search for repeated queries."""
        return self.search(query_text, k, threshold)

    def search(
        self,
        query_text: str,
        k: int = 5,
        threshold: float = 0.0,
    ) -> list[tuple[str, float]]:
        """
        Search for similar documents in the vector store.
        
        Args:
            query_text: Query text to search
            k: Number of top results to return
            threshold: Minimum similarity score (0.0 to 1.0)
            
        Returns:
            List of (doc_id, similarity_score) tuples, sorted by score (descending)
        """
        if faiss is None:
            logger.warning("[vector_store] search unavailable: faiss not installed")
            return []
        if not self.is_available():
            logger.warning("[vector_store] search called on unavailable store")
            return []
        
        if not query_text or not isinstance(query_text, str):
            return []
        
        try:
            query_embedding = embed_text(query_text)
            if query_embedding is None:
                logger.warning("[vector_store] failed to embed query: %s", query_text[:50])
                return []
            
            # Reshape for FAISS
            query_embedding = query_embedding.astype(np.float32).reshape(1, -1)
            
            # Search (FAISS returns L2 distances, need to convert to similarity)
            k_search = min(k * 2, self.index.ntotal)  # Get more results for filtering
            distances, indices = self.index.search(query_embedding, k_search)
            
            # Convert threshold to Python float
            threshold_float = float(threshold)
            
            results = []
            # FAISS returns (1, k_search) arrays, get the first row
            distances_row = distances[0].tolist()  # Convert to Python list
            indices_row = indices[0].tolist()  # Convert to Python list
            
            for dist, idx in zip(distances_row, indices_row):
                if int(idx) == -1:  # Invalid result
                    continue
                
                # Convert L2 distance to similarity score
                # For normalized vectors: similarity = 1 / (1 + distance)
                similarity = 1.0 / (1.0 + float(dist))
                
                # Apply threshold
                if similarity >= threshold_float:
                    metadata = self.documents.get(int(idx))
                    if metadata is not None:
                        results.append((metadata.doc_id, similarity))
            
            # Sort by similarity (descending) and return top k
            results.sort(key=lambda x: x[1], reverse=True)
            return results[:k]
        
        except Exception as exc:
            logger.error("[vector_store] search failed for query '%s': %s", query_text[:50], exc)
            return []
    
    def get_document(self, doc_id: str) -> Optional[DocumentMetadata]:
        """Retrieve metadata for a document by ID."""
        if doc_id not in self.doc_id_to_idx:
            return None
        idx = self.doc_id_to_idx[doc_id]
        return self.documents.get(idx)
    
    def save(self, path: Optional[Path] = None) -> bool:
        """
        Save the vector store to disk.
        
        Args:
            path: Optional custom path (defaults to VECTOR_STORE_DIR)
            
        Returns:
            True if successfully saved, False otherwise
        """
        if path is None:
            path = INDEX_FILE.parent
        
        try:
            path.mkdir(parents=True, exist_ok=True)
            
            if faiss is None:
                logger.warning("[vector_store] cannot save: faiss not installed")
                return False
            
            if self.index is None:
                logger.warning("[vector_store] cannot save: index is None")
                return False
            
            # Save FAISS index
            faiss.write_index(self.index, str(path / "faiss_index.bin"))
            
            # Save metadata
            metadata_to_save = {
                "documents": self.documents,
                "doc_id_to_idx": self.doc_id_to_idx,
                "embedding_count": self._embedding_count,
            }
            with open(path / "metadata.pkl", "wb") as f:
                pickle.dump(metadata_to_save, f)
            
            logger.info("[vector_store] saved to %s (%d documents)", path, len(self.documents))
            return True
        except Exception as exc:
            logger.error("[vector_store] save failed: %s", exc)
            return False
    
    def load(self, path: Optional[Path] = None) -> bool:
        """
        Load the vector store from disk.
        
        Args:
            path: Optional custom path (defaults to VECTOR_STORE_DIR)
            
        Returns:
            True if successfully loaded, False otherwise
        """
        if path is None:
            path = INDEX_FILE.parent
        
        index_path = path / "faiss_index.bin"
        metadata_path = path / "metadata.pkl"
        
        if faiss is None:
            logger.warning("[vector_store] cannot load: faiss not installed")
            return False
        if not index_path.exists() or not metadata_path.exists():
            logger.info("[vector_store] no saved index found at %s", path)
            return False
        
        try:
            # Load FAISS index
            self.index = faiss.read_index(str(index_path))
            
            # Load metadata
            with open(metadata_path, "rb") as f:
                metadata = pickle.load(f)
            
            self.documents = metadata["documents"]
            self.doc_id_to_idx = metadata["doc_id_to_idx"]
            self._embedding_count = metadata["embedding_count"]
            self._loaded_from_disk = True
            
            logger.info("[vector_store] loaded from %s (%d documents)", path, len(self.documents))
            return True
        except Exception as exc:
            logger.error("[vector_store] load failed: %s", exc)
            return False
    
    def clear(self):
        """Clear all data from the vector store."""
        self.index = None
        self.documents.clear()
        self.doc_id_to_idx.clear()
        self._embedding_count = 0
        logger.info("[vector_store] cleared")
    
    def __len__(self) -> int:
        """Return number of documents in the store."""
        return len(self.documents)


# Global instance
_VECTOR_STORE: Optional[VectorStore] = None


def get_vector_store() -> VectorStore:
    """Get or create the global vector store instance."""
    global _VECTOR_STORE
    if _VECTOR_STORE is None:
        _VECTOR_STORE = VectorStore()
    return _VECTOR_STORE


def is_vector_store_available() -> bool:
    """Check if vector store is available for searches."""
    store = get_vector_store()
    return store.is_available()
