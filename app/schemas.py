"""
Pydantic schemas for request/response validation
"""
from pydantic import BaseModel, Field
from decimal import Decimal
from datetime import datetime
from typing import Optional, List

class ProductBase(BaseModel):
    name: str
    category: str
    price: Decimal = Field(..., ge=0, decimal_places=2)

class ProductCreate(ProductBase):
    pass

class ProductResponse(ProductBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class ProductListResponse(BaseModel):
    """Response for paginated product list with cursor-based pagination"""
    items: List[ProductResponse]
    next_cursor: Optional[str] = None
    has_more: bool
    total_count: Optional[int] = None  # Approximate, can be expensive on large tables

class ProductFilter(BaseModel):
    """Query parameters for filtering products"""
    category: Optional[str] = None
    cursor: Optional[str] = None  # Base64-encoded (created_at, id) tuple
    limit: int = Field(default=20, ge=1, le=100)  # Max 100 per page
