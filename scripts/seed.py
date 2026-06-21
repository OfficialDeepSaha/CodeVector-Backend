"""
Seed script to generate 200,000 products

APPROACH: Bulk insert with SQLAlchemy core for speed
- Single INSERT with 200k values would be too large
- We batch into chunks of 5,000 for optimal performance
- Uses Faker for realistic product data
- Uses COPY for maximum speed if available, falls back to bulk insert

Performance target: ~30-60 seconds for 200k rows
"""
import os
import sys
import random
from datetime import datetime, timedelta
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
from faker import Faker
import argparse

# Add parent to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from app.database import Base, DATABASE_URL
from app.models import Product

load_dotenv()

fake = Faker()

# Predefined categories for realistic distribution
CATEGORIES = [
    "Electronics", "Clothing", "Home & Garden", "Sports", "Books",
    "Toys", "Automotive", "Health", "Food", "Office",
    "Music", "Art", "Pet Supplies", "Tools", "Garden"
]

# Pre-generated adjectives and nouns for product names
ADJECTIVES = ["Premium", "Smart", "Ultra", "Pro", "Essential", "Deluxe", 
              "Compact", "Wireless", "Digital", "Classic", "Modern", "Vintage",
              "Portable", "Professional", "Advanced", "Basic", "Elite", "Standard"]
NOUNS = ["Device", "Kit", "System", "Pack", "Set", "Unit", "Collection",
         "Bundle", "Edition", "Model", "Version", "Series", "Assortment"]


def generate_product_name():
    """Generate a realistic product name"""
    patterns = [
        lambda: f"{random.choice(ADJECTIVES)} {fake.word().title()} {random.choice(NOUNS)}",
        lambda: f"{fake.word().title()} {random.choice(NOUNS)} {random.randint(100, 999)}",
        lambda: f"{random.choice(ADJECTIVES)} {fake.word().title()}",
        lambda: f"{fake.word().title()} {fake.word().title()} {random.choice(NOUNS)}",
    ]
    return random.choice(patterns)()


def generate_products(count: int):
    """Generate product data without hitting the DB"""
    products = []
    now = datetime.utcnow()

    for i in range(count):
        # Spread created_at over the last 2 years for realistic distribution
        days_ago = random.randint(0, 730)
        hours_ago = random.randint(0, 23)
        minutes_ago = random.randint(0, 59)
        created_at = now - timedelta(days=days_ago, hours=hours_ago, minutes=minutes_ago)

        # Some products recently updated
        updated_at = created_at
        if random.random() < 0.3:  # 30% chance of being updated
            updated_at = created_at + timedelta(days=random.randint(0, days_ago))

        product = {
            "id": i + 1,
            "name": generate_product_name(),
            "category": random.choice(CATEGORIES),
            "price": round(random.uniform(5.0, 500.0), 2),
            "created_at": created_at,
            "updated_at": updated_at
        }
        products.append(product)

    return products


def seed_with_copy(engine, products):
    """Use PostgreSQL COPY for maximum speed"""
    import io
    import csv

    # Create CSV in memory
    output = io.StringIO()
    writer = csv.writer(output)

    for p in products:
        writer.writerow([
            p["id"],
            p["name"],
            p["category"],
            p["price"],
            p["created_at"].isoformat(),
            p["updated_at"].isoformat()
        ])

    output.seek(0)

    raw_conn = engine.raw_connection()
    try:
        with raw_conn.cursor() as cursor:
            cursor.copy_expert(
                """COPY products (id, name, category, price, created_at, updated_at) 
                   FROM STDIN WITH CSV""",
                output
            )
        raw_conn.commit()
    finally:
        raw_conn.close()


def seed_with_bulk_insert(engine, products, batch_size=5000):
    """Fallback: Use SQLAlchemy bulk insert in batches"""
    Session = sessionmaker(bind=engine)

    total = len(products)
    for i in range(0, total, batch_size):
        batch = products[i:i + batch_size]
        session = Session()
        try:
            session.bulk_insert_mappings(Product, batch)
            session.commit()
            print(f"  Inserted {min(i + batch_size, total)}/{total} products...")
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()


def main():
    parser = argparse.ArgumentParser(description="Seed products database")
    parser.add_argument("--count", type=int, default=200000, help="Number of products to generate")
    parser.add_argument("--batch-size", type=int, default=5000, help="Batch size for inserts")
    parser.add_argument("--use-copy", action="store_true", default=True, help="Use PostgreSQL COPY (fastest)")
    args = parser.parse_args()

    print(f"🚀 Generating {args.count:,} products...")

    # Generate data in memory first
    products = generate_products(args.count)
    print(f"✅ Generated {len(products):,} product records in memory")

    # Create engine
    engine = create_engine(DATABASE_URL)

    # Drop and create tables
    print("📊 Setting up database tables...")
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    # Seed data
    print(f"💾 Inserting into database...")
    start_time = datetime.now()

    if args.use_copy and "postgresql" in DATABASE_URL:
        try:
            seed_with_copy(engine, products)
            print(f"✅ Used PostgreSQL COPY for fast insertion")
        except Exception as e:
            print(f"⚠️ COPY failed ({e}), falling back to bulk insert...")
            seed_with_bulk_insert(engine, products, args.batch_size)
    else:
        seed_with_bulk_insert(engine, products, args.batch_size)

    elapsed = (datetime.now() - start_time).total_seconds()
    print(f"✅ Done! Inserted {args.count:,} products in {elapsed:.2f}s")
    print(f"   Rate: {args.count / elapsed:,.0f} rows/second")

    # Verify count
    Session = sessionmaker(bind=engine)
    session = Session()
    count = session.query(Product).count()
    print(f"📈 Total products in database: {count:,}")

    # Show category distribution
    from sqlalchemy import func
    categories = session.query(Product.category, func.count(Product.id)).group_by(Product.category).all()
    print(f"📊 Category distribution:")
    for cat, cnt in sorted(categories, key=lambda x: -x[1]):
        print(f"   {cat}: {cnt:,}")

    # Reset PostgreSQL sequence so new inserts don't fail with UniqueViolation
    if "postgresql" in DATABASE_URL:
        print("🔄 Resetting sequence for PostgreSQL...")
        try:
            session.execute(text("SELECT setval(pg_get_serial_sequence('products', 'id'), coalesce(max(id), 0)) FROM products;"))
            session.commit()
        except Exception as e:
            print(f"⚠️ Sequence reset failed: {e}")
            session.rollback()

    session.close()

if __name__ == "__main__":
    main()
