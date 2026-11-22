import sys
sys.path.insert(0, 'backend')
from app.database import engine
from sqlalchemy import inspect, text

inspector = inspect(engine)
tables = inspector.get_table_names()
print(f"Total tables: {len(tables)}")
print("-" * 55)
with engine.connect() as conn:
    total_rows = 0
    for t in sorted(tables):
        try:
            count = conn.execute(text(f'SELECT COUNT(*) FROM "{t}"')).scalar()
            print(f"{t:35}: {count:6d} rows")
            total_rows += count
        except Exception as e:
            print(f"{t:35}: ERROR ({e})")
    print("-" * 55)
    print(f"TOTAL ROWS ACROSS ALL TABLES      : {total_rows:6d}")
