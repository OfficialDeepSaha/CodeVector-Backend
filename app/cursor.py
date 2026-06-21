"""
Cursor encoding/decoding utilities for keyset pagination

The cursor is a base64-encoded JSON object containing (created_at, id).
This is opaque to the client - they just pass it back to get the next page.

Why this approach:
- O(log n) performance via index seek (created_at, id)
- Stable ordering: inserts/deletes before current position don't affect results
- No duplicate/missed items when data changes during browsing
"""
import json
import base64
from datetime import datetime
from typing import Optional, Tuple


def encode_cursor(created_at: datetime, product_id: int) -> str:
    """Encode (created_at, id) tuple into opaque cursor string"""
    data = {
        "t": created_at.isoformat(),  # ISO 8601 timestamp
        "i": product_id
    }
    json_bytes = json.dumps(data).encode("utf-8")
    return base64.urlsafe_b64encode(json_bytes).decode("utf-8").rstrip("=")


def decode_cursor(cursor: str) -> Tuple[datetime, int]:
    """Decode cursor string back to (created_at, id) tuple"""
    # Add padding back if needed
    padding = 4 - len(cursor) % 4
    if padding != 4:
        cursor += "=" * padding

    json_bytes = base64.urlsafe_b64decode(cursor.encode("utf-8"))
    data = json.loads(json_bytes.decode("utf-8"))

    created_at = datetime.fromisoformat(data["t"])
    product_id = data["i"]

    return created_at, product_id
