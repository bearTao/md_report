"""
PostgreSQL版本微网格预分析配置脚本

使用方法:
1. 确保PostgreSQL数据库已创建
2. 设置正确的连接参数
3. 运行此脚本导入数据和配置连接
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from sqlalchemy import create_engine, text
from app.database import SessionLocal
from app.models.db_models import DBConnection, DBEngineType
import asyncio

# ==================== 配置区 ====================
# 请根据实际情况修改以下配置

PG_HOST = "10.10.20.10"
PG_PORT = 14632
PG_DATABASE = "microgrid"
PG_USERNAME = "postgres"  # 请修改为正确的用户名
PG_PASSWORD = "your_password"  # 请修改为正确的密码

# 可选：如果SQL文件不在默认位置，请修改
SQL_FILE_PATH = "/data/tao/code/xuqiu/tmp/预分析报告建表语句及测试数据.sql"

# ==================== 配置区结束 ====================


def test_pg_connection():
    """测试PostgreSQL连接"""
    print("=" * 80)
    print("步骤1: 测试PostgreSQL连接")
    print("=" * 80)
    
    pg_url = f"postgresql://{PG_USERNAME}:{PG_PASSWORD}@{PG_HOST}:{PG_PORT}/{PG_DATABASE}"
    
    try:
        engine = create_engine(pg_url)
        with engine.connect() as conn:
            result = conn.execute(text("SELECT version()"))
            version = result.scalar()
            print(f"✅ PostgreSQL连接成功！")
            print(f"   版本: {version[:80]}")
            
            # 检查现有表
            result = conn.execute(text("""
                SELECT COUNT(*) 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
            """))
            table_count = result.scalar()
            print(f"   现有表数量: {table_count}")
            
            return engine
    except Exception as e:
        print(f"❌ PostgreSQL连接失败: {e}")
        print(f"\n请检查:")
        print(f"  1. PostgreSQL服务是否运行")
        print(f"  2. 主机和端口是否正确: {PG_HOST}:{PG_PORT}")
        print(f"  3. 数据库是否存在: {PG_DATABASE}")
        print(f"  4. 用户名和密码是否正确: {PG_USERNAME}")
        return None


def import_sql_data(engine):
    """导入SQL数据"""
    print("\n" + "=" * 80)
    print("步骤2: 导入SQL数据")
    print("=" * 80)
    
    if not os.path.exists(SQL_FILE_PATH):
        print(f"❌ SQL文件不存在: {SQL_FILE_PATH}")
        return False
    
    print(f"📄 读取SQL文件: {SQL_FILE_PATH}")
    
    try:
        with open(SQL_FILE_PATH, 'r', encoding='utf-8') as f:
            sql_content = f.read()
        
        print(f"   文件大小: {len(sql_content)} 字符")
        
        # 执行SQL（使用psycopg2的方式，一次性执行）
        with engine.connect() as conn:
            # 开始事务
            trans = conn.begin()
            try:
                # 执行整个SQL文件
                conn.execute(text(sql_content))
                trans.commit()
                print(f"✅ SQL文件导入成功！")
                
                # 检查导入的数据
                result = conn.execute(text("SELECT COUNT(*) FROM micro_grid_overview_w"))
                count = result.scalar()
                print(f"   micro_grid_overview_w 表: {count} 行")
                
                return True
            except Exception as e:
                trans.rollback()
                print(f"❌ 导入失败: {e}")
                print(f"\n提示: 如果表已存在，可以跳过此步骤")
                return False
                
    except Exception as e:
        print(f"❌ 读取SQL文件失败: {e}")
        return False


def register_pg_connection():
    """在系统中注册PostgreSQL连接"""
    print("\n" + "=" * 80)
    print("步骤3: 注册数据库连接配置")
    print("=" * 80)
    
    db = SessionLocal()
    
    try:
        # 检查是否已存在
        existing = db.query(DBConnection).filter(
            DBConnection.name == "microgrid_db_pg"
        ).first()
        
        if existing:
            print(f"⚠️  连接 'microgrid_db_pg' 已存在，正在更新...")
            existing.engine = DBEngineType.POSTGRESQL
            existing.host = PG_HOST
            existing.port = PG_PORT
            existing.database = PG_DATABASE
            existing.username = PG_USERNAME
            existing.password_ciphertext = PG_PASSWORD
            existing.is_active = "true"
            db.commit()
            print(f"✅ 连接配置已更新")
        else:
            print(f"创建新的连接配置...")
            new_conn = DBConnection(
                name="microgrid_db_pg",
                engine=DBEngineType.POSTGRESQL,
                host=PG_HOST,
                port=PG_PORT,
                database=PG_DATABASE,
                username=PG_USERNAME,
                password_ciphertext=PG_PASSWORD,
                is_active="true",
                description="PostgreSQL版本微网格预分析数据库"
            )
            db.add(new_conn)
            db.commit()
            print(f"✅ 新连接配置已创建")
        
        print(f"\n连接信息:")
        print(f"  名称: microgrid_db_pg")
        print(f"  引擎: PostgreSQL")
        print(f"  地址: {PG_HOST}:{PG_PORT}/{PG_DATABASE}")
        print(f"  用户: {PG_USERNAME}")
        
        return True
        
    except Exception as e:
        print(f"❌ 注册连接失败: {e}")
        db.rollback()
        return False
    finally:
        db.close()


def test_query():
    """测试查询"""
    print("\n" + "=" * 80)
    print("步骤4: 测试查询")
    print("=" * 80)
    
    from app.connectors.database import db_connector
    
    pg_url = f"postgresql://{PG_USERNAME}:{PG_PASSWORD}@{PG_HOST}:{PG_PORT}/{PG_DATABASE}"
    engine = create_engine(pg_url)
    
    try:
        # 注册连接
        db_connector.register_connection("microgrid_db_pg", engine)
        
        async def test_async_query():
            # 测试查询
            result = await db_connector.execute_query(
                connection_name="microgrid_db_pg",
                query="SELECT COUNT(*) as total FROM micro_grid_overview_w",
                timeout=10
            )
            
            if result:
                total = result[0].get('total', 0)
                print(f"✅ 查询成功！")
                print(f"   micro_grid_overview_w 表有 {total} 行数据")
                
                # 查询一些示例wgid
                result = await db_connector.execute_query(
                    connection_name="microgrid_db_pg",
                    query="SELECT wgid, micro_grid_name FROM micro_grid_overview_w LIMIT 5",
                    timeout=10
                )
                
                if result:
                    print(f"\n   示例数据:")
                    for row in result:
                        print(f"     - {row.get('wgid')}: {row.get('micro_grid_name')}")
                
                return True
            else:
                print(f"❌ 查询返回空结果")
                return False
        
        return asyncio.run(test_async_query())
        
    except Exception as e:
        print(f"❌ 查询测试失败: {e}")
        return False


def create_pg_template():
    """创建PostgreSQL版本的模板配置"""
    print("\n" + "=" * 80)
    print("步骤5: 创建PostgreSQL版本模板配置")
    print("=" * 80)
    
    # 模板元数据（将所有SQL配置中的connection改为microgrid_db_pg）
    print(f"提示: 要使用PostgreSQL版本，需要:")
    print(f"  1. 复制现有的微网格预分析模板")
    print(f"  2. 在元数据JSON中，将所有 'connection': 'microgrid_db' 改为 'connection': 'microgrid_db_pg'")
    print(f"  3. 保存为新模板，例如 '微网格预分析-PostgreSQL版'")
    print(f"\n或者，使用API批量更新现有模板的连接配置")


def main():
    """主函数"""
    print("\n")
    print("=" * 80)
    print("PostgreSQL版本微网格预分析配置向导")
    print("=" * 80)
    print(f"\n配置信息:")
    print(f"  PostgreSQL地址: {PG_HOST}:{PG_PORT}")
    print(f"  数据库: {PG_DATABASE}")
    print(f"  用户名: {PG_USERNAME}")
    print(f"  SQL文件: {SQL_FILE_PATH}")
    print("\n⚠️  请确保以上配置正确，按Enter继续，或Ctrl+C退出...")
    
    try:
        input()
    except KeyboardInterrupt:
        print("\n\n已取消")
        return
    
    # 步骤1: 测试连接
    engine = test_pg_connection()
    if not engine:
        print("\n❌ 配置失败: 无法连接到PostgreSQL")
        print("\n请修改脚本顶部的配置参数，然后重新运行")
        return
    
    # 步骤2: 导入数据（可选）
    print("\n是否导入SQL数据？(如果数据已存在，请输入n) [y/N]: ", end="")
    try:
        choice = input().strip().lower()
        if choice == 'y':
            import_sql_data(engine)
    except KeyboardInterrupt:
        print("\n跳过数据导入")
    
    # 步骤3: 注册连接
    if not register_pg_connection():
        print("\n❌ 注册连接失败")
        return
    
    # 步骤4: 测试查询
    if not test_query():
        print("\n⚠️  查询测试失败，但连接已配置")
    
    # 步骤5: 创建模板配置提示
    create_pg_template()
    
    print("\n" + "=" * 80)
    print("✅ PostgreSQL配置完成！")
    print("=" * 80)
    print(f"\n下一步:")
    print(f"  1. 重启API服务以加载新的连接配置")
    print(f"  2. 在管理界面创建PostgreSQL版本的模板")
    print(f"  3. 或使用现有模板（将连接改为 microgrid_db_pg）")


if __name__ == "__main__":
    main()

