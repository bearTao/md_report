#!/usr/bin/env python3
"""直接执行ALTER TABLE语句"""
import pymysql

DB_CONFIG = {
    'host': '10.10.20.10',
    'port': 24406,
    'user': 'root',
    'password': '123456',
    'database': 'md_agent',
    'charset': 'utf8mb4'
}

def alter_table():
    """直接执行ALTER TABLE"""
    connection = pymysql.connect(**DB_CONFIG)
    cursor = connection.cursor()
    
    try:
        sql = """
        ALTER TABLE generation_task_variables 
        MODIFY COLUMN source 
        ENUM('USER_INPUT', 'SQL', 'API', 'AI_GENERATION', 'SYSTEM', 'IMAGE', 'VISION_AI') 
        NOT NULL
        """
        
        print("执行SQL:")
        print(sql)
        print("\n执行中...")
        
        cursor.execute(sql)
        connection.commit()
        
        print("✅ ALTER TABLE 成功执行！")
        
        # 验证
        cursor.execute("SHOW COLUMNS FROM generation_task_variables LIKE 'source'")
        result = cursor.fetchone()
        print(f"\n新的类型定义: {result[1]}")
        
    except Exception as e:
        print(f"❌ 错误: {e}")
        connection.rollback()
    finally:
        cursor.close()
        connection.close()

if __name__ == "__main__":
    alter_table()

