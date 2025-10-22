#!/usr/bin/env python3
"""
执行数据库枚举类型迁移脚本
"""
import pymysql
import sys

# 数据库配置
DB_CONFIG = {
    'host': '10.10.20.10',
    'port': 24406,
    'user': 'root',
    'password': '123456',
    'database': 'md_agent',
    'charset': 'utf8mb4'
}

def run_migration():
    """执行迁移SQL"""
    connection = None
    try:
        # 连接数据库
        print("📡 连接数据库...")
        connection = pymysql.connect(**DB_CONFIG)
        cursor = connection.cursor()
        
        # 读取SQL文件
        print("📄 读取SQL脚本...")
        with open('/data/tao/code/xuqiu/backend/fix_enum_migration.sql', 'r', encoding='utf-8') as f:
            sql_content = f.read()
        
        # 分割并执行SQL语句
        sql_statements = [stmt.strip() for stmt in sql_content.split(';') if stmt.strip() and not stmt.strip().startswith('--')]
        
        for i, sql in enumerate(sql_statements):
            if not sql:
                continue
            print(f"\n🔧 执行语句 {i+1}/{len(sql_statements)}...")
            print(f"   {sql[:100]}...")
            
            cursor.execute(sql)
            
            # 如果是查询语句，显示结果
            if sql.strip().upper().startswith(('SELECT', 'SHOW')):
                results = cursor.fetchall()
                for row in results:
                    print(f"   ✅ {row}")
        
        # 提交事务
        connection.commit()
        print("\n✅ 迁移成功完成！")
        return True
        
    except Exception as e:
        print(f"\n❌ 迁移失败: {e}")
        if connection:
            connection.rollback()
        return False
        
    finally:
        if connection:
            cursor.close()
            connection.close()
            print("🔌 数据库连接已关闭")

if __name__ == "__main__":
    success = run_migration()
    sys.exit(0 if success else 1)

