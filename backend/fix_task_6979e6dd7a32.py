"""修复 task_6979e6dd7a32 的报告状态"""
from app.database import SessionLocal
from sqlalchemy import text

db = SessionLocal()

try:
    # 更新报告状态
    result = db.execute(
        text("UPDATE reports SET status = 'failed' WHERE task_id = 'task_6979e6dd7a32'"),
    )
    db.commit()
    print(f"Fixed report status for task_6979e6dd7a32, {result.rowcount} row(s) updated")
except Exception as e:
    db.rollback()
    print(f"Error: {e}")
finally:
    db.close()

