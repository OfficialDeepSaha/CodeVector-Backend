# Submission Note

## What I chose and why
- **Backend Framework**: I chose **FastAPI (Python)** because it is incredibly fast, natively supports asynchronous operations, and is very easy to read. 
- **Database**: I chose **PostgreSQL** with **SQLAlchemy**. PostgreSQL was selected because it handles large datasets efficiently and supports `COPY FROM STDIN`, which I used in the seed script to bulk insert 200,000 products in just a few seconds.
- **Pagination Strategy**: I specifically chose **Keyset (Cursor) Pagination** over offset pagination. The PDF required that if 50 products are added while someone is browsing, they must not see duplicates or miss items. Offset pagination fails this requirement, but Cursor pagination (using a composite `(created_at, id)` index) guarantees it works perfectly and maintains O(log n) performance on deep pages.
- **Bonus UI**: I built a premium **React/Vite** frontend from scratch using vanilla CSS with a glassmorphic dark-mode aesthetic to provide a beautiful browsing experience that seamlessly integrates with the backend's cursor pagination.

## What I'd improve with more time
1. **Alembic Migrations**: Currently using `create_all()`; in a production environment, I would set up Alembic for proper database schema versioning.
2. **Caching**: Implement Redis caching for the `/categories` endpoint and hot pagination cursors.
3. **Search functionality**: Add Full-Text Search using PostgreSQL's `tsvector` so users can search products by name.
4. **Rate Limiting**: Add `slowapi` to protect the endpoints from abuse.
5. **Testing**: Expand the automated test suite beyond the concurrency simulation script to include standard unit tests via `pytest`.

## How I used AI
- **What it helped with**: I used AI extensively for scaffolding the initial FastAPI boilerplate, generating the realistic product data (names/prices) for the 200,000 items, and rapid prototyping of the React frontend CSS and layout.
- **What it got wrong (and what I caught/fixed)**: 
  1. The AI initially suggested using a single-column `id` cursor for the pagination. I caught this error, as it fails to sort properly when multiple products share the exact same `created_at` timestamp. I manually corrected it to use a **composite `(created_at, id)` cursor** for fully deterministic ordering.
  2. The AI initially suggested a standard `for` loop for seeding 200,000 records. I recognized this would take far too long and rewrote the seed script to use PostgreSQL's native `COPY FROM STDIN` via `io.StringIO()` for a massive performance boost.
  3. When generating the seed script, it hardcoded explicit IDs which broke the PostgreSQL sequence. I wrote a fix to execute `SELECT setval()` to resync the database sequence so new POST requests wouldn't fail.
