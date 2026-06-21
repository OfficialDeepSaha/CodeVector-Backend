"""
SQLAlchemy models for products
"""
from sqlalchemy import Column, Integer, String, Numeric, DateTime, Index
from sqlalchemy.sql import func
from app.database import Base

class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    category = Column(String(100), nullable=False, index=True)
    price = Column(Numeric(10, 2), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        # CRITICAL: Composite index for keyset pagination
        # Orders by newest first (created_at DESC) then id DESC for tie-breaking
        # This makes cursor pagination O(log n) instead of O(n) with offset
        Index('idx_products_created_at_id', 'created_at', 'id', postgresql_using='btree', postgresql_ops={'created_at': 'DESC', 'id': 'DESC'}),
        # Index for category filtering + pagination
        Index('idx_products_category_created_at_id', 'category', 'created_at', 'id', postgresql_using='btree', postgresql_ops={'created_at': 'DESC', 'id': 'DESC'}),
    )
