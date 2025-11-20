"""
数据库迁移执行脚本

使用方法：
    python migrations/run_migration.py --migration 002 --env dev
    python migrations/run_migration.py --migration 002 --env prod --dry-run
"""
import os
import sys
import argparse
from pathlib import Path
from datetime import datetime
import psycopg2
from psycopg2 import sql
from loguru import logger

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))


class MigrationRunner:
    """数据库迁移执行器"""
    
    def __init__(self, env: str = "dev"):
        """
        初始化迁移执行器
        
        Args:
            env: 环境名称（dev/test/prod）
        """
        self.env = env
        self.conn = None
        self.migrations_dir = Path(__file__).parent / "pg"
        
    def connect(self):
        """连接数据库"""
        # 从环境变量获取数据库配置
        db_config = {
            "host": os.getenv("POSTGRES_HOST", "10.10.20.10"),
            "port": os.getenv("POSTGRES_PORT", "14632"),
            "database": os.getenv("POSTGRES_DB", "new_md_agent"),
            "user": os.getenv("POSTGRES_USER", "microgrid"),
            "password": os.getenv("POSTGRES_PASSWORD", "microgrid123")
        }
        
        logger.info(f"连接数据库: {db_config['host']}:{db_config['port']}/{db_config['database']}")
        
        try:
            self.conn = psycopg2.connect(**db_config)
            logger.success("数据库连接成功")
        except Exception as e:
            logger.error(f"数据库连接失败: {e}")
            raise
    
    def disconnect(self):
        """断开数据库连接"""
        if self.conn:
            self.conn.close()
            logger.info("数据库连接已关闭")
    
    def get_migration_file(self, migration_number: str) -> Path:
        """
        获取迁移文件路径
        
        Args:
            migration_number: 迁移编号（如 "002"）
        
        Returns:
            Path: 迁移文件路径
        """
        # 查找匹配的迁移文件
        pattern = f"{migration_number}_*.sql"
        files = list(self.migrations_dir.glob(pattern))
        
        if not files:
            raise FileNotFoundError(f"未找到迁移文件: {pattern}")
        
        if len(files) > 1:
            logger.warning(f"找到多个匹配的迁移文件: {files}")
        
        return files[0]
    
    def read_migration_sql(self, migration_file: Path) -> str:
        """
        读取迁移 SQL
        
        Args:
            migration_file: 迁移文件路径
        
        Returns:
            str: SQL 内容
        """
        logger.info(f"读取迁移文件: {migration_file.name}")
        return migration_file.read_text(encoding='utf-8')
    
    def execute_migration(self, sql: str, dry_run: bool = False):
        """
        执行迁移
        
        Args:
            sql: SQL 语句
            dry_run: 是否为演练模式（不实际执行）
        """
        if dry_run:
            logger.warning("⚠️ 演练模式：不会实际执行迁移")
            logger.info("将要执行的 SQL:")
            logger.info("-" * 80)
            # 只显示前1000字符
            preview = sql[:1000] + "..." if len(sql) > 1000 else sql
            print(preview)
            logger.info("-" * 80)
            return
        
        logger.info("开始执行迁移...")
        start_time = datetime.now()
        
        try:
            with self.conn.cursor() as cur:
                # 执行 SQL
                cur.execute(sql)
                self.conn.commit()
                
                duration = (datetime.now() - start_time).total_seconds()
                logger.success(f"✅ 迁移执行成功！耗时: {duration:.2f} 秒")
        
        except Exception as e:
            self.conn.rollback()
            logger.error(f"❌ 迁移执行失败: {e}")
            raise
    
    def verify_migration(self, migration_number: str):
        """
        验证迁移是否成功
        
        Args:
            migration_number: 迁移编号
        """
        logger.info("验证迁移结果...")
        
        if migration_number == "002":
            self._verify_migration_002()
    
    def _verify_migration_002(self):
        """验证 002 迁移"""
        with self.conn.cursor() as cur:
            # 检查字段是否存在
            cur.execute("""
                SELECT 
                    column_name, 
                    data_type, 
                    is_nullable, 
                    column_default
                FROM information_schema.columns
                WHERE table_name = 'report_states'
                AND column_name IN ('edit_mode', 'variable_snapshot', 'generated_at', 'locked_at', 'lock_reason')
                ORDER BY ordinal_position
            """)
            
            columns = cur.fetchall()
            
            if len(columns) == 5:
                logger.success(f"✅ 所有字段已成功添加 ({len(columns)}/5)")
                for col in columns:
                    logger.info(f"  - {col[0]}: {col[1]} (nullable={col[2]})")
            else:
                logger.error(f"❌ 字段数量不正确: {len(columns)}/5")
                return False
            
            # 检查索引是否创建
            cur.execute("""
                SELECT 
                    indexname
                FROM pg_indexes
                WHERE tablename = 'report_states'
                AND indexname IN ('idx_report_states_edit_mode', 'idx_report_states_generated_at', 'idx_report_states_locked_at')
                ORDER BY indexname
            """)
            
            indexes = cur.fetchall()
            
            if len(indexes) == 3:
                logger.success(f"✅ 所有索引已成功创建 ({len(indexes)}/3)")
                for idx in indexes:
                    logger.info(f"  - {idx[0]}")
            else:
                logger.error(f"❌ 索引数量不正确: {len(indexes)}/3")
                return False
            
            # 检查约束是否创建
            cur.execute("""
                SELECT 
                    conname
                FROM pg_constraint
                WHERE conrelid = 'report_states'::regclass
                AND conname = 'check_edit_mode'
            """)
            
            constraints = cur.fetchall()
            
            if len(constraints) == 1:
                logger.success(f"✅ 约束已成功创建: {constraints[0][0]}")
            else:
                logger.error(f"❌ 约束未创建")
                return False
            
            return True
    
    def run(self, migration_number: str, dry_run: bool = False, verify: bool = True):
        """
        运行迁移
        
        Args:
            migration_number: 迁移编号
            dry_run: 是否为演练模式
            verify: 是否验证迁移结果
        """
        try:
            # 连接数据库
            self.connect()
            
            # 获取迁移文件
            migration_file = self.get_migration_file(migration_number)
            logger.info(f"迁移文件: {migration_file.name}")
            
            # 读取 SQL
            sql = self.read_migration_sql(migration_file)
            
            # 执行迁移
            self.execute_migration(sql, dry_run=dry_run)
            
            # 验证迁移
            if not dry_run and verify:
                self.verify_migration(migration_number)
            
            logger.success("🎉 迁移完成！")
        
        except Exception as e:
            logger.error(f"迁移失败: {e}")
            sys.exit(1)
        
        finally:
            self.disconnect()


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="数据库迁移执行脚本")
    parser.add_argument(
        "--migration", 
        "-m",
        required=True,
        help="迁移编号（如 002）"
    )
    parser.add_argument(
        "--env",
        "-e",
        default="dev",
        choices=["dev", "test", "prod"],
        help="环境名称（默认: dev）"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="演练模式（不实际执行）"
    )
    parser.add_argument(
        "--no-verify",
        action="store_true",
        help="不验证迁移结果"
    )
    
    args = parser.parse_args()
    
    # 配置日志
    logger.remove()
    logger.add(
        sys.stderr,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
        level="INFO"
    )
    
    # 执行迁移
    logger.info("=" * 80)
    logger.info(f"开始执行数据库迁移")
    logger.info(f"迁移编号: {args.migration}")
    logger.info(f"环境: {args.env}")
    logger.info(f"演练模式: {args.dry_run}")
    logger.info("=" * 80)
    
    runner = MigrationRunner(env=args.env)
    runner.run(
        migration_number=args.migration,
        dry_run=args.dry_run,
        verify=not args.no_verify
    )


if __name__ == "__main__":
    main()
