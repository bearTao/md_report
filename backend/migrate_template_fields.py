"""数据库迁移脚本：添加模板层级字段"""
import pymysql
import sys

def migrate():
    # 数据库配置
    connection = pymysql.connect(
        host='10.10.20.10',
        port=24406,
        user='root',
        password='123456',
        database='md_agent',
        charset='utf8mb4'
    )
    
    try:
        with connection.cursor() as cursor:
            # 检查 generation_task_variables 表是否已有这些字段
            cursor.execute("""
                SELECT COUNT(*) 
                FROM information_schema.COLUMNS 
                WHERE TABLE_SCHEMA = 'md_agent' 
                AND TABLE_NAME = 'generation_task_variables' 
                AND COLUMN_NAME = 'template_id'
            """)
            if cursor.fetchone()[0] == 0:
                print("添加 generation_task_variables.template_id 和 template_path...")
                cursor.execute("""
                    ALTER TABLE generation_task_variables 
                    ADD COLUMN template_id VARCHAR(50),
                    ADD COLUMN template_path VARCHAR(500)
                """)
                print("✓ generation_task_variables 表字段添加成功")
            else:
                print("generation_task_variables 表字段已存在，跳过")
            
            # 检查 execution_logs 表是否已有这些字段
            cursor.execute("""
                SELECT COUNT(*) 
                FROM information_schema.COLUMNS 
                WHERE TABLE_SCHEMA = 'md_agent' 
                AND TABLE_NAME = 'execution_logs' 
                AND COLUMN_NAME = 'template_id'
            """)
            if cursor.fetchone()[0] == 0:
                print("添加 execution_logs.template_id 和 template_path...")
                cursor.execute("""
                    ALTER TABLE execution_logs
                    ADD COLUMN template_id VARCHAR(50),
                    ADD COLUMN template_path VARCHAR(500)
                """)
                print("✓ execution_logs 表字段添加成功")
            else:
                print("execution_logs 表字段已存在，跳过")
            
            connection.commit()
            print("\n✓ 数据库迁移完成！")
            
    except Exception as e:
        connection.rollback()
        print(f"✗ 迁移失败: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        connection.close()

if __name__ == "__main__":
    migrate()

