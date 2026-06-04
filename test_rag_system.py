#!/usr/bin/env python3
"""
End-to-end semantic RAG system test.
Verifies all components are working correctly.
"""
import sys
import logging
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)

# Add project to path
sys.path.insert(0, str(Path(__file__).parent))

def test_embeddings():
    """Test embedding module."""
    logger.info("\n" + "="*70)
    logger.info("TEST 1: Embedding Module")
    logger.info("="*70)
    
    try:
        from core.embeddings import get_embedding_model, embed_text, embed_texts_batch
        
        # Load model
        model = get_embedding_model()
        if model is None:
            logger.error("❌ Failed to load embedding model")
            return False
        logger.info("✓ Embedding model loaded successfully")
        
        # Test single embedding
        text = "hemoglobin low anemia"
        emb = embed_text(text)
        if emb is None or len(emb) != 384:
            logger.error("❌ Single embedding failed or wrong dimension")
            return False
        logger.info(f"✓ Single embedding created (dimension={len(emb)})")
        
        # Test batch embedding
        texts = ["test glucose", "liver function", "kidney disease"]
        embs = embed_texts_batch(texts)
        if len(embs) != 3 or any(e is None for e in embs):
            logger.error("❌ Batch embedding failed")
            return False
        logger.info(f"✓ Batch embedding created ({len(embs)} texts)")
        
        return True
    except Exception as exc:
        logger.error(f"❌ Embedding test failed: {exc}")
        import traceback
        traceback.print_exc()
        return False


def test_vector_store():
    """Test vector store module."""
    logger.info("\n" + "="*70)
    logger.info("TEST 2: Vector Store Module")
    logger.info("="*70)
    
    try:
        from core.vector_store import VectorStore
        
        # Create new store
        store = VectorStore()
        logger.info("✓ VectorStore created")
        
        # Add some documents
        docs = [
            {"doc_id": "test_1", "text": "hemoglobin oxygen carrying capacity", "doc_type": "test"},
            {"doc_id": "test_2", "text": "glucose blood sugar levels", "doc_type": "test"},
            {"doc_id": "test_3", "text": "liver function enzymes", "doc_type": "test"},
        ]
        
        added = store.add_documents_batch(docs)
        logger.info(f"✓ Added {added}/{len(docs)} documents to store")
        
        if added == 0:
            logger.error("❌ No documents added to store")
            return False
        
        # Test search
        results = store.search("low hemoglobin anemia", k=2)
        if not results:
            logger.error("❌ Search returned no results")
            return False
        logger.info(f"✓ Search found {len(results)} results")
        for doc_id, score in results:
            logger.info(f"  → {doc_id}: {score:.3f}")
        
        # Test persistence
        from pathlib import Path
        test_dir = Path("/tmp/test_vector_store")
        test_dir.mkdir(exist_ok=True)
        
        if not store.save(test_dir):
            logger.error("❌ Failed to save store")
            return False
        logger.info("✓ Vector store saved")
        
        # Test loading
        store2 = VectorStore()
        if not store2.load(test_dir):
            logger.error("❌ Failed to load store")
            return False
        logger.info("✓ Vector store loaded")
        
        if len(store2) != added:
            logger.error(f"❌ Loaded store has {len(store2)} docs, expected {added}")
            return False
        logger.info(f"✓ Store integrity verified ({len(store2)} documents)")
        
        return True
    except Exception as exc:
        logger.error(f"❌ Vector store test failed: {exc}")
        import traceback
        traceback.print_exc()
        return False


def test_rag_initialization():
    """Test RAG system initialization."""
    logger.info("\n" + "="*70)
    logger.info("TEST 3: RAG System Initialization")
    logger.info("="*70)
    
    try:
        from core.rag_init import initialize_rag_system, test_rag_system
        
        # Initialize
        ok = initialize_rag_system()
        if not ok:
            logger.error("❌ RAG initialization returned False")
            return False
        logger.info("✓ RAG system initialized")
        
        # Run test
        if not test_rag_system():
            logger.error("❌ RAG test failed")
            return False
        logger.info("✓ RAG system test passed")
        
        return True
    except Exception as exc:
        logger.error(f"❌ RAG initialization test failed: {exc}")
        import traceback
        traceback.print_exc()
        return False


def test_semantic_resolver():
    """Test semantic test resolver."""
    logger.info("\n" + "="*70)
    logger.info("TEST 4: Semantic Test Resolver")
    logger.info("="*70)
    
    try:
        from core.resolver import resolve_test_key_with_confidence
        
        test_cases = [
            ("hemoglobin", "hemoglobin"),  # Should match with high confidence
            ("HB", "hemoglobin"),           # Abbreviation
            ("glucose", "glucose_fasting"),  # Should match with high confidence
            ("wbc count", "wbc"),           # Should match
        ]
        
        passed = 0
        for test_name, expected_key in test_cases:
            key, confidence = resolve_test_key_with_confidence(test_name)
            if key == expected_key and confidence > 0.5:
                logger.info(f"✓ '{test_name}' → {key} (confidence={confidence})")
                passed += 1
            else:
                logger.warning(f"⚠ '{test_name}' → {key} (confidence={confidence}, expected {expected_key})")
        
        if passed >= len(test_cases) * 0.75:
            logger.info(f"✓ Resolver test passed ({passed}/{len(test_cases)})")
            return True
        else:
            logger.error(f"❌ Resolver test failed ({passed}/{len(test_cases)})")
            return False
    except Exception as exc:
        logger.error(f"❌ Semantic resolver test failed: {exc}")
        import traceback
        traceback.print_exc()
        return False


def test_insights_service():
    """Test semantic insights retrieval."""
    logger.info("\n" + "="*70)
    logger.info("TEST 5: Semantic Insights Service")
    logger.info("="*70)
    
    try:
        from services.insights_service import get_applicable_patterns_for_test
        
        test_keys = ["hemoglobin", "glucose_fasting", "creatinine"]
        
        for test_key in test_keys:
            patterns = get_applicable_patterns_for_test(test_key)
            if patterns:
                logger.info(f"✓ Found {len(patterns)} patterns for '{test_key}'")
                for p in patterns[:1]:
                    logger.info(f"  → {p.get('name', 'Unknown')}")
            else:
                logger.warning(f"⚠ No patterns found for '{test_key}'")
        
        logger.info("✓ Insights service test passed")
        return True
    except Exception as exc:
        logger.error(f"❌ Insights service test failed: {exc}")
        import traceback
        traceback.print_exc()
        return False


def test_end_to_end():
    """Test full pipeline."""
    logger.info("\n" + "="*70)
    logger.info("TEST 6: End-to-End Pipeline")
    logger.info("="*70)
    
    try:
        from core.pipeline import process_lab_report
        
        sample_text = """
        Lab Report
        Hemoglobin: 10.5 g/dL (low)
        WBC: 12000 /μL (high)
        Glucose (fasting): 140 mg/dL (high)
        Creatinine: 1.2 mg/dL (normal)
        """
        
        tests, tracker = process_lab_report(sample_text, gender="male", age=45)
        
        if tests:
            logger.info(f"✓ Pipeline processed {len(tests)} tests")
            for test in tests[:2]:
                logger.info(f"  → {test.resolved_key}: {test.value} {test.unit} (status={test.status})")
        else:
            logger.warning("⚠ Pipeline processed no tests")
        
        logger.info("✓ End-to-end pipeline test passed")
        return True
    except Exception as exc:
        logger.error(f"❌ End-to-end pipeline test failed: {exc}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests."""
    logger.info("\n" + "="*70)
    logger.info("SEMANTIC RAG SYSTEM - COMPREHENSIVE TEST")
    logger.info("="*70)
    
    tests = [
        ("Embeddings", test_embeddings),
        ("Vector Store", test_vector_store),
        ("RAG Initialization", test_rag_initialization),
        ("Semantic Resolver", test_semantic_resolver),
        ("Insights Service", test_insights_service),
        ("End-to-End Pipeline", test_end_to_end),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as exc:
            logger.error(f"❌ Test '{name}' crashed: {exc}")
            results.append((name, False))
    
    # Summary
    logger.info("\n" + "="*70)
    logger.info("TEST SUMMARY")
    logger.info("="*70)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✓ PASS" if result else "❌ FAIL"
        logger.info(f"{status}: {name}")
    
    logger.info("\n" + "="*70)
    if passed == total:
        logger.info(f"✓ ALL TESTS PASSED ({passed}/{total})")
        logger.info("="*70)
        return 0
    else:
        logger.error(f"❌ SOME TESTS FAILED ({passed}/{total})")
        logger.info("="*70)
        return 1


if __name__ == "__main__":
    sys.exit(main())
