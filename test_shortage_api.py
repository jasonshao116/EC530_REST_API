import requests
import json
from datetime import datetime
from urllib.parse import urljoin

BASE_ROOT = "http://localhost:8000"
BASE_URL = urljoin(BASE_ROOT, "/v1/shortages")

TIMEOUT_SECS = 10


def pretty_print(resp: requests.Response):
    print(f"\nStatus Code: {resp.status_code}")
    ctype = resp.headers.get("content-type", "")
    if "application/json" in ctype:
        print(json.dumps(resp.json(), indent=2))
    else:
        print(resp.text)


def safe_get(url, params=None):
    try:
        return requests.get(url, params=params, timeout=TIMEOUT_SECS)
    except requests.exceptions.ConnectionError:
        print(f"\n❌ Connection refused: {url}")
        print("   Your API server is not running OR not listening on this host/port.")
        print(f"   Expected base: {BASE_ROOT}")
        print("   Fix: start your server (FastAPI/Flask/etc.) or change BASE_ROOT/port.")
        return None
    except requests.exceptions.Timeout:
        print(f"\n❌ Timeout after {TIMEOUT_SECS}s: {url}")
        return None


def test_server_reachable():
    print("\n=== Checking server reachability ===")
    # Try a health endpoint first; if you don't have it, this will 404 (that's still reachable)
    health_url = urljoin(BASE_ROOT, "/health")
    resp = safe_get(health_url)
    if resp is None:
        return False

    print(f"✅ Server reachable at {BASE_ROOT} (GET /health returned {resp.status_code})")
    return True


def test_current_shortages():
    print("\n=== Testing: GET /v1/shortages/current ===")
    resp = safe_get(f"{BASE_URL}/current", params={"limit": 5})
    if resp is None:
        return None

    pretty_print(resp)
    if resp.status_code != 200:
        return None

    data = resp.json()
    results = data.get("results") or []
    if not results:
        print("⚠️ No results returned from /current")
        return None

    # Try to extract a shortage_id from the first result
    first = results[0]
    shortage_id = first.get("shortage_id") or first.get("id")
    if shortage_id:
        print(f"\n✅ Extracted shortage_id for follow-up tests: {shortage_id}")
        return shortage_id

    print("\n⚠️ Could not find 'shortage_id' in the first result. "
          "Update your API to return shortage_id, or edit extraction logic here.")
    return None


def test_search_shortages():
    print("\n=== Testing: GET /v1/shortages/search ===")
    resp = safe_get(f"{BASE_URL}/search", params={"q": "amoxicillin", "status": "any", "limit": 5})
    if resp is None:
        return
    pretty_print(resp)


def test_single_shortage(shortage_id: str):
    print("\n=== Testing: GET /v1/shortages/{shortage_id} ===")
    resp = safe_get(f"{BASE_URL}/{shortage_id}")
    if resp is None:
        return
    pretty_print(resp)


def test_update_type_stats():
    print("\n=== Testing: GET /v1/shortages/stats/update-types ===")
    resp = safe_get(f"{BASE_URL}/stats/update-types", params={"status": "current"})
    if resp is None:
        return
    pretty_print(resp)


if __name__ == "__main__":
    print("Drug Shortage API Test Suite")
    print(f"Testing API at: {BASE_URL}")
    print(f"Time: {datetime.now()}")

    if not test_server_reachable():
        raise SystemExit(1)

    shortage_id = test_current_shortages()
    test_search_shortages()
    if shortage_id:
        test_single_shortage(shortage_id)
    test_update_type_stats()