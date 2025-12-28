#!/usr/bin/env python3
"""Test script for the enhanced Yomisub API endpoints.

Run the server first:
  cd src && python main.py

Then run this test:
  python scripts/test_api.py
"""

import json
import sys

try:
    import httpx
except ImportError:
    print("Please install httpx: pip install httpx")
    sys.exit(1)

BASE_URL = "http://localhost:8000"


def test_endpoint(name: str, method: str, path: str, data: dict | None = None):
    """Test an API endpoint and print results."""
    print(f"\n{'='*60}")
    print(f"TEST: {name}")
    print(f"{'='*60}")
    
    url = f"{BASE_URL}{path}"
    print(f"{method} {path}")
    if data:
        print(f"Request: {json.dumps(data, ensure_ascii=False)}")
    
    try:
        with httpx.Client(timeout=30) as client:
            if method == "GET":
                response = client.get(url)
            else:
                response = client.post(url, json=data)
        
        print(f"\nStatus: {response.status_code}")
        
        result = response.json()
        print(f"Response:\n{json.dumps(result, ensure_ascii=False, indent=2)}")
        
        return response.status_code == 200
    except httpx.ConnectError:
        print("❌ Could not connect to server. Is it running?")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def main():
    print("="*60)
    print("YOMISUB API TEST SUITE")
    print("="*60)
    
    # Health check
    if not test_endpoint("Health Check", "GET", "/"):
        print("\n⚠️  Server not running. Start with: cd src && python main.py")
        return
    
    # Test /analyze with complex verb
    test_endpoint(
        "Analyze - Complex Verb",
        "POST", "/analyze",
        {"text": "食べられなかった"}
    )
    
    # Test /analyze_simple
    test_endpoint(
        "Analyze Simple - Vocabulary Focus",
        "POST", "/analyze_simple",
        {"text": "日本語を勉強しています。難しいですが、面白いです。"}
    )
    
    # Test /analyze_full
    test_endpoint(
        "Analyze Full - Grammar Study",
        "POST", "/analyze_full",
        {"text": "言われてみれば分かる"}
    )
    
    test_endpoint(
        "Analyze Full - Names (JMNedict)",
        "POST", "/analyze_full",
        # Expect Suzuki and Tanaka
        {"text": "鈴木さんは田中さんです"}
    )
    
    # Test /deconjugate
    test_endpoint(
        "Deconjugate - Complex Form",
        "POST", "/deconjugate",
        {"word": "食べられなかった"}
    )
    
    test_endpoint(
        "Deconjugate - Passive + Miru",
        "POST", "/deconjugate",
        {"word": "言われてみれば", "dictionary_form": "言う"}
    )
    
    # Test /conjugate - verb
    test_endpoint(
        "Conjugate - Verb Forms",
        "POST", "/conjugate",
        {"word": "食べる", "word_type": "verb"}
    )
    
    # Test /conjugate - i-adjective
    test_endpoint(
        "Conjugate - i-Adjective",
        "POST", "/conjugate",
        {"word": "高い", "word_type": "i-adjective"}
    )
    
    # Test /conjugate - na-adjective
    test_endpoint(
        "Conjugate - na-Adjective",
        "POST", "/conjugate",
        {"word": "静か", "word_type": "na-adjective"}
    )
    
    print("\n" + "="*60)
    print("TEST SUITE COMPLETE")
    print("="*60)


if __name__ == "__main__":
    main()
