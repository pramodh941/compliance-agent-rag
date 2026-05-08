#!/usr/bin/env python3
"""
Qdrant Collection Diagnostic

Tests Qdrant collection configuration and indexing status.
"""

import requests
import json
import sys

def check_qdrant_collection():
    """Check Qdrant collection configuration."""
    
    QDRANT_URL = "http://localhost:6333"
    
    print("Checking Qdrant collection configuration...\n")
    
    try:
        # Test 1: Qdrant health
        print("1. Testing Qdrant connectivity...")
        response = requests.get(f"{QDRANT_URL}/health", timeout=5)
        if response.status_code != 200:
            print(f"   ✗ Qdrant not responding (status {response.status_code})")
            return False
        
        health = response.json()
        print(f"   ✓ Qdrant is running")
        print(f"   Version: {health.get('version')}")
        
        # Test 2: List collections
        print("\n2. Listing collections...")
        collections_response = requests.get(f"{QDRANT_URL}/collections", timeout=5)
        if collections_response.status_code != 200:
            print(f"   ✗ Cannot list collections (status {collections_response.status_code})")
            return False
        
        collections = collections_response.json().get("collections", [])
        print(f"   Found {len(collections)} collections")
        
        for coll in collections:
            print(f"     - {coll.get('name')}")
        
        # Test 3: Get policies collection details
        print("\n3. Checking 'policies' collection...")
        policies_response = requests.get(f"{QDRANT_URL}/collections/policies", timeout=5)
        
        if policies_response.status_code != 200:
            print(f"   ✗ 'policies' collection not found (status {policies_response.status_code})")
            return False
        
        print("   ✓ 'policies' collection exists")
        
        collection_data = policies_response.json().get("result", {})
        
        # Test 4: Check collection stats
        print("\n4. Collection statistics...")
        points_count = collection_data.get("points_count", 0)
        indexed_vectors = collection_data.get("indexed_vectors_count", 0)
        
        print(f"   Points count: {points_count}")
        print(f"   Indexed vectors count: {indexed_vectors}")
        
        if points_count > 0 and indexed_vectors == 0:
            print(f"   ✗ CRITICAL: {points_count} points but 0 indexed vectors!")
        elif indexed_vectors == points_count and points_count > 0:
            print(f"   ✓ All {points_count} points are properly indexed")
        
        # Test 5: Check vector configuration
        print("\n5. Vector configuration...")
        config = collection_data.get("config", {})
        params = config.get("params", {})
        vectors_config = params.get("vectors", {})
        
        print(f"   Vectors config type: {type(vectors_config).__name__}")
        
        if isinstance(vectors_config, dict):
            print(f"   Size: {vectors_config.get('size')}")
            print(f"   Distance: {vectors_config.get('distance')}")
        elif isinstance(vectors_config, list):
            print(f"   Vectors config is a list with {len(vectors_config)} elements")
            for i, v in enumerate(vectors_config[:3]):
                print(f"     [{i}]: {v}")
        else:
            print(f"   Vectors config: {vectors_config}")
        
        # Test 6: Check indexing config
        print("\n6. Indexing configuration...")
        index_config = params.get("index_config", {})
        print(f"   Index config: {json.dumps(index_config, indent=6)}")
        
        # Test 7: Query points
        print("\n7. Querying collection points...")
        query_response = requests.post(
            f"{QDRANT_URL}/collections/policies/points/search",
            json={
                "vector": [0.1] * 768,  # Dummy vector
                "limit": 1,
                "score_threshold": 0.0
            },
            timeout=5
        )
        
        if query_response.status_code == 200:
            search_result = query_response.json()
            result = search_result.get("result", [])
            print(f"   ✓ Search query works, found {len(result)} results")
        else:
            print(f"   ✗ Search query failed (status {query_response.status_code})")
            print(f"   Response: {query_response.text}")
        
        # Test 8: Get a sample point
        if points_count > 0:
            print("\n8. Checking sample points...")
            scroll_response = requests.post(
                f"{QDRANT_URL}/collections/policies/points/scroll",
                json={
                    "limit": 1,
                    "with_payload": True,
                    "with_vectors": True
                },
                timeout=5
            )
            
            if scroll_response.status_code == 200:
                scroll_result = scroll_response.json().get("result", {})
                points = scroll_result.get("points", [])
                
                if points:
                    point = points[0]
                    print(f"   Point ID: {point.get('id')}")
                    
                    vector = point.get('vector')
                    if vector:
                        print(f"   Vector type: {type(vector).__name__}")
                        print(f"   Vector length: {len(vector) if isinstance(vector, (list, tuple)) else 'N/A'}")
                        if isinstance(vector, (list, tuple)):
                            print(f"   First 3 values: [{vector[0]:.6f}, {vector[1]:.6f}, {vector[2]:.6f}]")
                    else:
                        print(f"   Vector: MISSING!")
                    
                    payload = point.get('payload', {})
                    print(f"   Payload keys: {list(payload.keys())}")
        
        print("\n" + "="*60)
        print("Qdrant collection check complete")
        print("="*60)
        
        if indexed_vectors == 0 and points_count > 0:
            print("\n⚠️  ISSUE FOUND: Points are stored but not indexed!")
            print("\nPossible causes:")
            print("  1. Vector indexing failed silently")
            print("  2. Collection configuration doesn't match vectors")
            print("  3. Vectors have invalid data types")
            print("  4. Qdrant database corruption")
            return False
        
        return True
        
    except requests.exceptions.ConnectionError as e:
        print(f"   ✗ Connection error: {e}")
        print(f"   Is Qdrant running at {QDRANT_URL}?")
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
    success = check_qdrant_collection()
    sys.exit(0 if success else 1)
