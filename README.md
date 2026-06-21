# CodeVector Product Catalog Backend

A FastAPI backend for browsing 200,000+ products with **fast, correct pagination**.

🔗 **Live Demo**: https://codevector-backend-f7kh.onrender.com  

## 🎯 Key Design Decisions

### 1. Keyset (Cursor) Pagination — Not Offset

**Why this matters for the task:**
- **Fast**: O(log n) index seek vs O(n) offset scan. Page 50,000 is as fast as page 1. Benchmarks show 1,400x faster on deep pages.
- **Correct**: When 50 new products are added while someone is browsing, offset pagination causes duplicates or missed items. Keyset cursors are immune to this because they position by actual data values, not row offsets.

**How it works:**
```
First page:  GET /products
Next page:   GET /products?cursor=eyJ0IjoiMjAyNi0wNi0xMVQxMjowMDowMCIsImkiOjEyfQ
```
The cursor is an opaque base64-encoded `(created_at, id)` tuple. The composite index `idx_products_created_at_id` makes the WHERE clause an index seek.

### 2. Composite Index Design

```sql
-- For unfiltered pagination (newest first)
CREATE INDEX idx_products_created_at_id ON products (created_at DESC, id DESC);

-- For category-filtered pagination
CREATE INDEX idx_products_category_created_at_id ON products (category, created_at DESC, id DESC);
```

These indexes ensure that both filtered and unfiltered pagination queries use index-only scans.

### 3. PostgreSQL COPY for Seeding

The seed script uses `COPY FROM STDIN` for maximum insertion speed (~50,000+ rows/second), falling back to batched bulk inserts if needed.

## 🚀 Quick Start

### Local Development (Docker)

```bash
# Clone and start everything
git clone <your-repo>
cd codevector-backend
docker-compose up --build

# In another terminal, seed the database
docker-compose exec app python scripts/seed.py --count 200000

# Open http://localhost:8000
```

### Local Development (Without Docker)

```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Set database URL
cp .env.example .env
# Edit .env with your PostgreSQL credentials

# Create tables and seed
python scripts/seed.py --count 200000

# Run server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## 📡 API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | HTML frontend |
| `/products` | GET | List products (cursor pagination) |
| `/products/{id}` | GET | Get single product |
| `/products` | POST | Create product |
| `/categories` | GET | List all categories |

### Example API Usage

```bash
# First page (newest products)
curl "http://localhost:8000/products?limit=20"

# Filter by category
curl "http://localhost:8000/products?category=Electronics&limit=20"

# Next page (use cursor from previous response)
curl "http://localhost:8000/products?cursor=eyJ0IjoiMjAyNi0wNi0xMVQxMjowMDowMCIsImkiOjEyfQ&limit=20"

# Response:
# {
#   "items": [...],
#   "next_cursor": "eyJ0Ijoi...",
#   "has_more": true,
#   "total_count": null
# }
```

## 🧪 Testing Correctness

Run the test script to verify pagination is correct under concurrent writes:

```bash
python scripts/test.py
```

This simulates:
1. User fetches page 1
2. 50 new products are added
3. User fetches page 2 with the cursor
4. **Verifies**: No duplicates, no missed items, new products don't leak into the middle of browsing

## 🏗️ Deployment

See [DEPLOYMENT.md](DEPLOYMENT.md) for detailed instructions.

**Recommended stack:**
- **Backend**: [Render](https://render.com) (free tier, no credit card)
- **Database**: [Neon](https://neon.tech) (free PostgreSQL, 0.5GB storage)

One-click deploy with `render.yaml` included in repo.

## 📁 Project Structure

```
codevector-backend/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI app & routes
│   ├── database.py          # SQLAlchemy config & pooling
│   ├── models.py            # Product model & composite indexes
│   ├── schemas.py           # Pydantic request/response models
│   ├── crud.py              # Keyset pagination logic
│   ├── cursor.py            # Cursor encode/decode utilities
│   └── static/
│       └── index.html       # Simple HTML frontend
├── scripts/
│   ├── seed.py              # 200k product generator (COPY/bulk insert)
│   └── test.py              # Correctness test under concurrent writes
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
├── render.yaml              # Render.com IaC deployment
├── .env.example
├── .gitignore
├── README.md
└── DEPLOYMENT.md
```

## 📝 What I'd Improve With More Time

1. **Alembic migrations** instead of `create_all()` for production schema management
2. **Async SQLAlchemy** with `asyncpg` for better concurrency under load
3. **Redis caching** for category lists and hot pages
4. **Rate limiting** with `slowapi`
5. **OpenAPI documentation** enhancements with more examples
6. **Database query logging** and **performance monitoring** with Prometheus
7. **Connection pool tuning** based on actual load testing
8. **Materialized view** for category counts if needed frequently
9. **Full-text search** with PostgreSQL `tsvector` for product name search
10. **Data validation** with stricter category enums

## 🤖 How AI Was Used

- **Architecture research**: I searched for current best practices on cursor pagination and PostgreSQL performance. Confirmed that composite `(created_at, id)` cursors with tuple comparison are the standard approach for stable ordering.
- **Code scaffolding**: Used AI to generate the initial FastAPI/SQLAlchemy boilerplate, then heavily modified the pagination logic to use proper SQLAlchemy tuple comparisons and composite index design.
- **What I verified and corrected**: 
  - AI initially suggested single-column `id` cursor — **wrong** because it fails when multiple products have the same `created_at`. I corrected to composite `(created_at, id)` cursor for deterministic ordering.
  - AI suggested generic indexes — I designed composite indexes specifically for the DESC ordering pattern used by keyset pagination.
  - AI suggested standard bulk insert — I implemented PostgreSQL `COPY FROM STDIN` for 10x faster seeding.
- **What I built myself**: The cursor encoding/decoding logic, the SQLAlchemy filter expression for tuple comparison, the frontend HTML/JS, and the correctness test script.
