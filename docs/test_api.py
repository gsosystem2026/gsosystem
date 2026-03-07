#!/usr/bin/env python3
"""
Quick script to verify the GSO API is reachable and authentication works.
Run with: python docs/test_api.py
Requires: requests (pip install requests)

Uses default base URL http://127.0.0.1:8000 and sample user requestor/sample123.
Override with env: GSO_API_BASE_URL, GSO_API_USER, GSO_API_PASSWORD
"""
import os
import sys

try:
    import requests
except ImportError:
    print("Install requests: pip install requests")
    sys.exit(1)

BASE = os.environ.get("GSO_API_BASE_URL", "http://127.0.0.1:8000").rstrip("/")
USER = os.environ.get("GSO_API_USER", "requestor")
PASS = os.environ.get("GSO_API_PASSWORD", "sample123")
API = f"{BASE}/api/v1"

def main():
    print("GSO API connectivity check")
    print("=" * 50)
    print(f"Base URL: {BASE}")
    print(f"API root: {API}/")
    print()

    try:
        # 1. API root (no auth)
        print("1. GET /api/v1/ (no auth)...")
        r = requests.get(f"{API}/", timeout=10)
    except requests.exceptions.ConnectionError:
        print("   Cannot connect to the server.")
        print()
        print("   Start the GSO server first in another terminal:")
        print("   python manage.py runserver")
        print()
        print("   Then run this script again.")
        return 1

    if r.status_code != 200:
        print(f"   FAILED: {r.status_code}")
        return 1
    data = r.json()
    print(f"   OK: {data.get('name', '')} v{data.get('version', '')}")
    print()

    # 2. Units (no auth for list)
    print("2. GET /api/v1/units/ (no auth)...")
    r = requests.get(f"{API}/units/", timeout=10)
    if r.status_code != 200:
        print(f"   FAILED: {r.status_code}")
        return 1
    data = r.json()
    results = data.get("results", []) if isinstance(data, dict) else data
    n = len(results) if isinstance(results, list) else data.get("count", "?")
    print(f"   OK: units listed ({n} items)")
    print()

    # 3. Get JWT token
    print("3. POST /api/v1/auth/token/ (obtain JWT)...")
    r = requests.post(
        f"{API}/auth/token/",
        json={"username": USER, "password": PASS},
        headers={"Content-Type": "application/json"},
        timeout=10,
    )
    if r.status_code != 200:
        print(f"   FAILED: {r.status_code} - {r.text[:200]}")
        print("   Tip: Create sample users: python manage.py create_sample_users")
        return 1
    tokens = r.json()
    access = tokens.get("access")
    if not access:
        print("   FAILED: no 'access' in response")
        return 1
    print("   OK: token received")
    print()

    # 4. List requests (with auth)
    print("4. GET /api/v1/requests/ (with Bearer token)...")
    r = requests.get(
        f"{API}/requests/",
        headers={"Authorization": f"Bearer {access}"},
        timeout=10,
    )
    if r.status_code != 200:
        print(f"   FAILED: {r.status_code} - {r.text[:200]}")
        return 1
    data = r.json()
    results = data.get("results", []) if isinstance(data, dict) else data
    n = len(results) if isinstance(results, list) else data.get("count", "?")
    print(f"   OK: requests listed ({n} items)")
    print()

    print("=" * 50)
    print("All checks passed. API is ready for external connections.")
    return 0

if __name__ == "__main__":
    sys.exit(main())
