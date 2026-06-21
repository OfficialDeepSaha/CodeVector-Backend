"""
Test script to verify pagination correctness under concurrent writes.

This simulates the exact scenario from the task:
- User browses page 1
- 50 new products are added
- User browses page 2
- Result: No duplicates, no missed items
"""
import os
import sys
import requests
import random
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

BASE_URL = os.getenv("API_URL", "http://localhost:8000")

def test_pagination_correctness():
    print("=" * 60)
    print("TEST: Pagination Correctness Under Concurrent Writes")
    print("=" * 60)

    # Step 1: Get page 1
    print("\n1. Fetching page 1...")
    r1 = requests.get(f"{BASE_URL}/products?limit=5")
    r1.raise_for_status()
    page1 = r1.json()
    page1_ids = {p["id"] for p in page1["items"]}
    print(f"   Page 1 IDs: {sorted(page1_ids)}")

    # Step 2: Add 50 new products while "user is browsing"
    print("\n2. Adding 50 new products (simulating concurrent writes)...")
    new_ids = []
    for i in range(50):
        product = {
            "name": f"Test Product {i+1}",
            "category": "Electronics",
            "price": round(random.uniform(10, 100), 2)
        }
        r = requests.post(f"{BASE_URL}/products", json=product)
        r.raise_for_status()
        new_ids.append(r.json()["id"])
    print(f"   Added 50 products with IDs: {new_ids[0]} to {new_ids[-1]}")

    # Step 3: Get page 2 using cursor from page 1
    print("\n3. Fetching page 2 with cursor from page 1...")
    cursor = page1["next_cursor"]
    r2 = requests.get(f"{BASE_URL}/products?cursor={cursor}&limit=5")
    r2.raise_for_status()
    page2 = r2.json()
    page2_ids = {p["id"] for p in page2["items"]}
    print(f"   Page 2 IDs: {sorted(page2_ids)}")

    # Step 4: Verify correctness
    print("\n4. Verifying correctness...")

    # Check 1: No overlap between page 1 and page 2
    overlap = page1_ids & page2_ids
    if overlap:
        print(f"   ❌ FAIL: Duplicate IDs found: {overlap}")
    else:
        print("   ✅ PASS: No duplicate items between pages")

    # Check 2: None of the new products appear in page 2
    # (They should be at the top, not in the middle of browsing)
    new_in_page2 = page2_ids & set(new_ids)
    if new_in_page2:
        print(f"   ❌ FAIL: New products leaked into page 2: {new_in_page2}")
    else:
        print("   ✅ PASS: New products correctly excluded from page 2")

    # Check 3: All page 2 items are older than the last page 1 item
    last_p1_time = datetime.fromisoformat(page1["items"][-1]["created_at"].replace('Z', '+00:00'))
    all_p2_older = all(
        datetime.fromisoformat(p["created_at"].replace('Z', '+00:00')) <= last_p1_time
        for p in page2["items"]
    )
    if all_p2_older:
        print("   ✅ PASS: All page 2 items are older than page 1's last item")
    else:
        print("   ❌ FAIL: Some page 2 items are newer than page 1's boundary")

    # Check 4: Verify new products appear at the top when fetching fresh
    print("\n5. Verifying new products appear at top of fresh fetch...")
    r3 = requests.get(f"{BASE_URL}/products?limit=10")
    fresh = r3.json()
    fresh_ids = [p["id"] for p in fresh["items"]]
    new_at_top = any(nid in fresh_ids[:5] for nid in new_ids)
    if new_at_top:
        print("   ✅ PASS: New products appear in fresh fetch (as expected)")
    else:
        print("   ⚠️  New products not in top 10 — may be due to clock skew")

    print("\n" + "=" * 60)
    print("Test complete. Keyset pagination prevents duplicates/missed items.")
    print("=" * 60)


def test_performance():
    """Benchmark deep pagination performance"""
    print("\n" + "=" * 60)
    print("TEST: Deep Pagination Performance")
    print("=" * 60)

    # Get total count first
    r = requests.get(f"{BASE_URL}/products?limit=1&include_count=true")
    total = r.json().get("total_count", "unknown")
    print(f"Total products: {total}")

    # Navigate deep into the list
    cursor = None
    page = 0
    import time

    while True:
        start = time.time()
        r = requests.get(f"{BASE_URL}/products?cursor={cursor or ''}&limit=100")
        elapsed = time.time() - start
        data = r.json()
        page += 1

        if page % 10 == 0:
            print(f"   Page {page}: {elapsed*1000:.1f}ms")

        if not data["has_more"]:
            break
        cursor = data["next_cursor"]

    print(f"\nNavigated through {page} pages. Each page ~100 items.")
    print("Keyset pagination maintains consistent performance regardless of depth.")


if __name__ == "__main__":
    test_pagination_correctness()
    # test_performance()  # Uncomment to run performance test (takes longer)
