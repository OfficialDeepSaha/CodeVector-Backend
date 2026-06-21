"""
CRUD operations with keyset pagination

KEY DESIGN DECISION: Keyset (Cursor) Pagination instead of Offset/LIMIT

Why:
1. PERFORMANCE: OFFSET forces Postgres to scan and discard N rows. At page 50,000 
   with offset 1,000,000, this takes ~87ms vs sub-millisecond for keyset.citeweb_search:3#3
2. CORRECTNESS: When 50 new products are added while someone is browsing, offset 
   pagination causes duplicates or missed items. Keyset cursors are immune to this.citeweb_search:3#2
3. INDEX EFFICIENCY: WHERE (created_at, id) < (cursor) uses the composite index 
   for an index seek, not a scan.citeweb_search:3#8

Trade-off: No random page access (can't jump to page 500 directly). 
For browsing "newest first", sequential access is the expected UX anyway.
"""
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func
from typing import List, Tuple, Optional
from datetime import datetime

from app.models import Product
from app.schemas import ProductCreate
from app.cursor import encode_cursor, decode_cursor


def create_product(db: Session, product: ProductCreate) -> Product:
    """Create a new product"""
    db_product = Product(**product.model_dump())
    db.add(db_product)
    db.commit()
    db.refresh(db_product)
    return db_product


def get_products_keyset(
    db: Session,
    category: Optional[str] = None,
    cursor: Optional[str] = None,
    limit: int = 20
) -> Tuple[List[Product], Optional[str], bool]:
    """
    Get products using keyset (cursor) pagination.

    Returns:
        - List of products
        - Next cursor (or None if no more pages)
        - has_more boolean

    Query pattern:
        SELECT * FROM products 
        WHERE (created_at, id) < (cursor_created_at, cursor_id)  -- for next page
        AND category = 'xxx'  -- optional filter
        ORDER BY created_at DESC, id DESC
        LIMIT 21  -- fetch 1 extra to determine has_more

    The composite index idx_products_created_at_id makes this an index seek.
    """
    # We fetch limit + 1 to determine if there are more pages
    fetch_limit = limit + 1

    query = db.query(Product)

    # Apply category filter if provided
    if category:
        query = query.filter(Product.category == category)

    # Apply cursor filter for keyset pagination
    # We want rows WHERE (created_at, id) < (cursor_created_at, cursor_id)
    # because we're sorting DESC (newest first)
    if cursor:
        try:
            cursor_created_at, cursor_id = decode_cursor(cursor)
            # Tuple comparison: (created_at, id) < (cursor_created_at, cursor_id)
            # This is equivalent to:
            # created_at < cursor_created_at OR (created_at = cursor_created_at AND id < cursor_id)
            query = query.filter(
                or_(
                    Product.created_at < cursor_created_at,
                    and_(
                        Product.created_at == cursor_created_at,
                        Product.id < cursor_id
                    )
                )
            )
        except Exception:
            # Invalid cursor - treat as first page
            pass

    # Order by newest first (created_at DESC, id DESC for tie-breaking)
    query = query.order_by(Product.created_at.desc(), Product.id.desc())

    # Limit results
    products = query.limit(fetch_limit).all()

    # Determine if there are more results
    has_more = len(products) > limit
    if has_more:
        products = products[:limit]  # Remove the extra item

    # Generate next cursor from the last item
    next_cursor = None
    if products and has_more:
        last_product = products[-1]
        next_cursor = encode_cursor(last_product.created_at, last_product.id)

    return products, next_cursor, has_more


def get_product(db: Session, product_id: int) -> Optional[Product]:
    """Get a single product by ID"""
    return db.query(Product).filter(Product.id == product_id).first()


def get_categories(db: Session) -> List[str]:
    """Get all unique categories"""
    result = db.query(Product.category).distinct().all()
    return [r[0] for r in result]


def get_total_count(db: Session, category: Optional[str] = None) -> int:
    """Get approximate total count (can be expensive on large tables)"""
    query = db.query(Product)
    if category:
        query = query.filter(Product.category == category)
    return query.count()
