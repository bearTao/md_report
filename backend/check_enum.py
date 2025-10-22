#!/usr/bin/env python3
"""检查数据库枚举类型"""
import pymysql

DB_CONFIG = {
    'host': '10.10.20.10',
    'port': 24406,
    'user': 'root',
    'password': '123456',
    'database': 'md_agent',
    'charset': 'utf8mb4'
}

def check_enum():
    """检查枚举类型"""
    connection = pymysql.connect(**DB_CONFIG)
    cursor = connection.cursor()
    
    try:
        # 查看source字段的定义
        cursor.execute("SHOW COLUMNS FROM generation_task_variables LIKE 'source'")
        result = cursor.fetchone()
        
        print("=" * 60)
        print("generation_task_variables.source 字段定义:")
        print("=" * 60)
        print(f"Field: {result[0]}")
        print(f"Type: {result[1]}")
        print(f"Null: {result[2]}")
        print(f"Key: {result[3]}")
        print(f"Default: {result[4]}")
        print(f"Extra: {result[5]}")
        
        # 检查是否包含 'IMAGE' 和 'VISION_AI' (大写)
        type_def = result[1].upper()
        has_image = 'IMAGE' in type_def
        has_vision_ai = 'VISION_AI' in type_def
        
        print("\n" + "=" * 60)
        print("检查结果:")
        print("=" * 60)
        print(f"包含 'image': {'✅' if has_image else '❌'}")
        print(f"包含 'vision_ai': {'✅' if has_vision_ai else '❌'}")
        
        if not (has_image and has_vision_ai):
            print("\n⚠️  需要执行ALTER TABLE语句！")
        else:
            print("\n✅ 枚举类型已正确更新！")
            
    finally:
        cursor.close()
        connection.close()

if __name__ == "__main__":
    check_enum()

