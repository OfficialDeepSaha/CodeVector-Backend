"""
FastAPI application for CodeVector product catalog

Architecture:
- Keyset pagination for O(log n) performance and data consistency
- Connection pooling for concurrent requests
- Proper index design for filtered queries
"""
from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from typing import Optional, List
import os

from app.database import engine, get_db, Base
from app import models, crud, schemas

# Create tables on startup (in production, use Alembic migrations)
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="CodeVector Product Catalog",
    description="Fast backend for browsing 200,000+ products with cursor-based pagination",
    version="1.0.0"
)

# CORS for frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve static frontend files
app.mount("/static", StaticFiles(directory="app/static"), name="static")


@app.get("/")
def root():
    return FileResponse("app/static/index.html")


@app.get("/products", response_model=schemas.ProductListResponse)
def list_products(
    category: Optional[str] = Query(None, description="Filter by category"),
    cursor: Optional[str] = Query(None, description="Opaque cursor for next page"),
    limit: int = Query(20, ge=1, le=100, description="Items per page (max 100)"),
    include_count: bool = Query(False, description="Include total count (slower on large tables)"),
    db: Session = Depends(get_db)
):
    """
    List products with cursor-based pagination (newest first).

    **Why cursor pagination?**
    - **Fast**: O(log n) index seek vs O(n) offset scan. Page 50,000 is as fast as page 1.
    - **Correct**: No duplicates or missed items when products are added/updated during browsing.

    **Usage:**
    1. First request: `GET /products` (no cursor)
    2. Next page: `GET /products?cursor={next_cursor from response}`
    3. Stop when `has_more` is false

    The cursor is opaque - just pass it back to get the next page.
    """
    products, next_cursor, has_more = crud.get_products_keyset(
        db=db,
        category=category,
        cursor=cursor,
        limit=limit
    )

    total_count = None
    if include_count:
        total_count = crud.get_total_count(db, category=category)

    return schemas.ProductListResponse(
        items=products,
        next_cursor=next_cursor,
        has_more=has_more,
        total_count=total_count
    )


@app.get("/products/{product_id}", response_model=schemas.ProductResponse)
def get_product(product_id: int, db: Session = Depends(get_db)):
    """Get a single product by ID"""
    product = crud.get_product(db, product_id=product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product


@app.get("/categories", response_model=List[str])
def list_categories(db: Session = Depends(get_db)):
    """Get all unique product categories"""
    return crud.get_categories(db)


@app.post("/products", response_model=schemas.ProductResponse, status_code=201)
def create_product(product: schemas.ProductCreate, db: Session = Depends(get_db)):
    """Create a new product (for testing data changes during pagination)"""
    return crud.create_product(db=db, product=product)
