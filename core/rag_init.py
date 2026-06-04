"""
RAG System initialization and medical knowledge indexing.

Populates the vector store with medical knowledge:
- Test definitions (names, units, descriptions)
- Clinical patterns (conditions, keywords, descriptions)
- Reference ranges (clinical context)

Designed to be called once on system startup.
"""
from __future__ import annotations

import logging
from pathlib import Path

from core.vector_store import get_vector_store, is_vector_store_available
from medical.reference_db import LabReferenceDB
from medical.clinical_kb import CLINICAL_PATTERNS, TEST_KEY_TO_CATEGORY

logger = logging.getLogger(__name__)


def initialize_rag_system() -> bool:
    """
    Initialize the RAG system by:
    1. Loading embeddings model
    2. Trying to load persisted vector store from disk
    3. If not found, building it from medical knowledge
    
    Returns:
        True if RAG system is operational, False otherwise
    """
    logger.info("[rag_init] initializing RAG system...")
    
    store = get_vector_store()
    
    # Try to load from disk first
    if store.load():
        logger.info("[rag_init] loaded existing vector store from disk")
        return is_vector_store_available()
    
    # If not found, build from scratch
    logger.info("[rag_init] building vector store from medical knowledge...")
    
    # Index test definitions
    added_tests = _index_test_definitions(store)
    logger.info("[rag_init] indexed %d test definitions", added_tests)
    
    # Index clinical patterns
    added_patterns = _index_clinical_patterns(store)
    logger.info("[rag_init] indexed %d clinical patterns", added_patterns)
    
    # Save to disk for future startup
    if store.is_available():
        store.save()
        logger.info("[rag_init] saved vector store to disk")
    
    logger.info("[rag_init] RAG initialization complete (%d total documents)", len(store))
    return is_vector_store_available()


def _index_test_definitions(store) -> int:
    """
    Index all test definitions from the reference database.
    Creates semantic entries for test name, description, aliases, and clinical context.
    
    Returns: Number of tests indexed
    """
    documents = []
    db = LabReferenceDB()

    try:
        from core.resolver import ALIASES
    except Exception:
        ALIASES = {}
        logger.debug("[rag_init] could not import resolver aliases for vector store indexing")

    for test_key, test_def in db.get_all_tests().items():
        # Main test entry
        doc_id = f"test_{test_key}"
        category = TEST_KEY_TO_CATEGORY.get(test_key, "Unknown")
        alias_list = [alias for alias, canonical in ALIASES.items() if canonical == test_key]
        alias_text = f"Aliases: {', '.join(alias_list)}." if alias_list else ""
        
        # Combine test name, description and aliases for better semantic matching
        text = (
            f"{test_def.display_name}. {test_def.what_it_measures}. "
            f"{alias_text} Category: {category}"
        ).strip()
        
        documents.append({
            "doc_id": doc_id,
            "text": text,
            "doc_type": "test_definition",
            "category": category,
        })
        
        # Also index the "what it measures" as a separate entry for clinical context
        doc_id_clinical = f"test_clinical_{test_key}"
        text_clinical = f"{test_def.display_name} clinical significance. {test_def.what_it_measures}"
        
        documents.append({
            "doc_id": doc_id_clinical,
            "text": text_clinical,
            "doc_type": "test_clinical_context",
            "category": category,
        })
    
    return store.add_documents_batch(documents)


def _index_clinical_patterns(store) -> int:
    """
    Index all clinical patterns from the knowledge base.
    Creates semantic entries for condition names, descriptions, and keywords.
    
    Returns: Number of patterns indexed
    """
    documents = []
    
    for pattern in CLINICAL_PATTERNS:
        # Main pattern entry
        doc_id = f"pattern_{pattern.pattern_id}"
        
        # Combine all semantic information
        text = (
            f"{pattern.condition_name}. "
            f"Description: {pattern.description}. "
            f"Keywords: {', '.join(pattern.keywords)}. "
            f"Severity: {pattern.severity_level}. "
            f"Possible causes: {', '.join(pattern.possible_causes)}"
        )
        
        documents.append({
            "doc_id": doc_id,
            "text": text,
            "doc_type": "clinical_pattern",
            "category": None,
        })
        
        # Also index the keywords separately for targeted searches
        doc_id_keywords = f"pattern_keywords_{pattern.pattern_id}"
        keywords_text = f"{pattern.condition_name} keywords: {' '.join(pattern.keywords)}"
        
        documents.append({
            "doc_id": doc_id_keywords,
            "text": keywords_text,
            "doc_type": "pattern_keywords",
            "category": None,
        })
    
    return store.add_documents_batch(documents)


def test_rag_system() -> bool:
    """
    Quick test to verify RAG system is operational.
    Performs a simple semantic search and logs results.
    
    Returns:
        True if test successful, False otherwise
    """
    try:
        if not is_vector_store_available():
            logger.error("[rag_test] vector store not available")
            return False
        
        store = get_vector_store()
        
        # Test search queries
        test_queries = [
            "hemoglobin low",
            "high blood sugar diabetes",
            "liver inflammation",
        ]
        
        for query in test_queries:
            results = store.search(query, k=3)
            if results:
                logger.info("[rag_test] search for '%s': found %d results", query, len(results))
                for doc_id, score in results[:1]:
                    logger.info("[rag_test]   → %s (score=%.3f)", doc_id, score)
            else:
                logger.warning("[rag_test] search for '%s': no results", query)
        
        logger.info("[rag_test] RAG system test passed")
        return True
    except Exception as exc:
        logger.error("[rag_test] test failed: %s", exc)
        return False
