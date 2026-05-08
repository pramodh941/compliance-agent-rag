#!/usr/bin/env python3
"""
Direct Ollama Embedding Test

Tests the raw response from Ollama to diagnose embedding issues.
"""

import requests
import json
import sys

def test_ollama_embedding():
    """Test raw Ollama embedding response."""
    
    OLLAMA_URL = "http://localhost:11434"
    
    print("Testing Ollama embedding response format...\n")
    
    try:
        # Test 1: Check Ollama is running
        print("1. Testing Ollama connectivity...")
        response = requests.get(f"{OLLAMA_URL}/api/tags", timeout=5)
        if response.status_code != 200:
            print(f"   ✗ Ollama not responding (status {response.status_code})")
            return False
        
        models = response.json().get("models", [])
        print(f"   ✓ Ollama is running with {len(models)} models")
        
        has_nomic = any(m.get("name", "").startswith("nomic") for m in models)
        if not has_nomic:
            print("   ✗ nomic-embed-text model not found!")
            print(f"   Available models: {[m.get('name') for m in models]}")
            return False
        print("   ✓ nomic-embed-text model is loaded")
        
        # Test 2: Get embedding
        print("\n2. Requesting embedding from Ollama...")
        embedding_response = requests.post(
            f"{OLLAMA_URL}/api/embeddings",
            json={"model": "nomic-embed-text", "prompt": "test embedding"},
            timeout=30
        )
        
        if embedding_response.status_code != 200:
            print(f"   ✗ Embedding request failed (status {embedding_response.status_code})")
            print(f"   Response: {embedding_response.text}")
            return False
        
        print("   ✓ Embedding request successful")
        
        # Test 3: Analyze response
        print("\n3. Analyzing response structure...")
        data = embedding_response.json()
        
        print(f"   Response keys: {list(data.keys())}")
        
        if "embedding" not in data:
            print("   ✗ 'embedding' field not found in response!")
            print(f"   Full response: {json.dumps(data, indent=2)}")
            return False
        
        embedding = data["embedding"]
        print(f"   ✓ 'embedding' field found")
        
        # Test 4: Check embedding type
        print(f"\n4. Checking embedding type...")
        print(f"   Type: {type(embedding).__name__}")
        print(f"   Is list: {isinstance(embedding, list)}")
        print(f"   Is tuple: {isinstance(embedding, tuple)}")
        
        # Convert if needed
        if not isinstance(embedding, (list, tuple)):
            print(f"   Converting {type(embedding).__name__} to list...")
            if hasattr(embedding, 'tolist'):
                embedding = embedding.tolist()
            else:
                embedding = list(embedding)
        else:
            embedding = list(embedding)
        
        # Test 5: Check dimensions
        print(f"\n5. Checking embedding dimensions...")
        print(f"   Length: {len(embedding)}")
        if len(embedding) != 768:
            print(f"   ✗ Expected 768 dimensions, got {len(embedding)}!")
            return False
        print(f"   ✓ Correct dimension: 768")
        
        # Test 6: Check element types
        print(f"\n6. Checking element types...")
        first_elem = embedding[0]
        print(f"   First element type: {type(first_elem).__name__}")
        print(f"   First element value: {first_elem}")
        
        # Check if values are numeric
        non_numeric = []
        for i, v in enumerate(embedding):
            if not isinstance(v, (int, float)):
                non_numeric.append((i, type(v).__name__))
        
        if non_numeric:
            print(f"   ✗ Found {len(non_numeric)} non-numeric elements!")
            print(f"   Examples: {non_numeric[:5]}")
            return False
        print(f"   ✓ All elements are numeric")
        
        # Test 7: Check for special values
        print(f"\n7. Checking for special values...")
        
        nan_count = sum(1 for v in embedding if v != v)  # NaN check
        inf_count = sum(1 for v in embedding if abs(v) == float('inf'))
        
        if nan_count > 0:
            print(f"   ✗ Found {nan_count} NaN values!")
            return False
        if inf_count > 0:
            print(f"   ✗ Found {inf_count} Inf values!")
            return False
        
        print(f"   ✓ No NaN or Inf values")
        
        # Test 8: Check value range
        print(f"\n8. Checking value range...")
        min_val = min(embedding)
        max_val = max(embedding)
        avg_val = sum(embedding) / len(embedding)
        
        print(f"   Min: {min_val:.6f}")
        print(f"   Max: {max_val:.6f}")
        print(f"   Avg: {avg_val:.6f}")
        
        # Check if values are reasonable (embeddings are typically normalized)
        if min_val < -100 or max_val > 100:
            print(f"   ⚠ Values seem unusual (typical embeddings are ~[-1, 1])")
        else:
            print(f"   ✓ Value range is reasonable")
        
        # Test 9: Show sample
        print(f"\n9. Sample embedding values...")
        print(f"   [{embedding[0]:.6f}, {embedding[1]:.6f}, {embedding[2]:.6f}, {embedding[3]:.6f}, ...]")
        
        # Test 10: Convert to Python floats
        print(f"\n10. Converting to Python floats...")
        embedding_floats = [float(v) for v in embedding]
        
        # Check if conversion changed anything
        print(f"   ✓ Conversion successful")
        print(f"   Sample after conversion: [{embedding_floats[0]:.6f}, {embedding_floats[1]:.6f}, ...]")
        
        print("\n" + "="*60)
        print("✓✓✓ ALL TESTS PASSED ✓✓✓")
        print("="*60)
        print("\nOllama embedding format is CORRECT and ready for Qdrant!")
        
        return True
        
    except requests.exceptions.ConnectionError as e:
        print(f"   ✗ Connection error: {e}")
        print(f"   Is Ollama running at {OLLAMA_URL}?")
        return False
    except requests.exceptions.Timeout as e:
        print(f"   ✗ Timeout: {e}")
        return False
    except Exception as e:
        print(f"   ✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_ollama_embedding()
    sys.exit(0 if success else 1)
