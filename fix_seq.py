import os
import sys
from sqlalchemy import text
sys.path.insert(0, os.getcwd())
from app.database import engine, DATABASE_URL

def fix():
    if "postgresql" in DATABASE_URL:
        print("Resetting sequence...")
        with engine.begin() as conn:
            conn.execute(text("SELECT setval(pg_get_serial_sequence('products', 'id'), coalesce(max(id), 0)) FROM products;"))
        print("Done.")

if __name__ == "__main__":
    fix()
