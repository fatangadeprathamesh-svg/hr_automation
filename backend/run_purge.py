import sys
sys.path.insert(0, 'backend')
from app.database import SessionLocal
from app.services.purge_service import purge_all_demo_data

db = SessionLocal()
try:
    print("Executing purge_all_demo_data()...")
    res = purge_all_demo_data(db)
    print(f"Purge complete: {res['total_deleted']} records deleted.")
    for table, count in sorted(res['deleted_counts'].items()):
        if count > 0:
            print(f"  - {table:25}: {count:5d} rows deleted")
finally:
    db.close()
