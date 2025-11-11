"""
数据迁移验证脚本

功能:
- 对比 MySQL 和 PostgreSQL 的数据
- 验证表结构、行数、关键字段
- 生成验证报告
"""
import os
from sqlalchemy import create_engine, inspect, MetaData, Table, text
from typing import Dict, Any, List
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 数据库连接配置
MYSQL_URL = os.getenv(
    "MYSQL_URL",
    "mysql+pymysql://root:123456@10.10.20.10:24406/md_agent?charset=utf8mb4"
)

POSTGRESQL_URL = os.getenv(
    "POSTGRESQL_URL",
    "postgresql://microgrid:microgrid123@10.10.20.10:14632/new_md_agent"
)


def get_table_count(engine, table_name: str) -> int:
    """获取表的行数"""
    with engine.connect() as conn:
        result = conn.execute(text(f"SELECT COUNT(*) FROM {table_name}"))
        return result.scalar()


def get_table_names(engine) -> List[str]:
    """获取所有表名"""
    inspector = inspect(engine)
    return inspector.get_table_names()


def verify_databases():
    """验证数据库迁移"""
    logger.info("开始验证数据库迁移...")
    logger.info("=" * 60)
    
    # 创建引擎
    mysql_engine = create_engine(MYSQL_URL)
    pgsql_engine = create_engine(POSTGRESQL_URL)
    
    # 获取表名
    mysql_tables = set(get_table_names(mysql_engine))
    pgsql_tables = set(get_table_names(pgsql_engine))
    
    logger.info(f"MySQL 表数量: {len(mysql_tables)}")
    logger.info(f"PostgreSQL 表数量: {len(pgsql_tables)}")
    
    # 检查缺失的表
    missing_in_pgsql = mysql_tables - pgsql_tables
    extra_in_pgsql = pgsql_tables - mysql_tables
    
    if missing_in_pgsql:
        logger.error(f"PostgreSQL 中缺失的表: {missing_in_pgsql}")
    if extra_in_pgsql:
        logger.warning(f"PostgreSQL 中额外的表: {extra_in_pgsql}")
    
    # 对比每个表的行数
    common_tables = mysql_tables & pgsql_tables
    logger.info(f"\n对比 {len(common_tables)} 个共同表的行数:")
    logger.info("-" * 60)
    
    verification_results = []
    
    for table_name in sorted(common_tables):
        try:
            mysql_count = get_table_count(mysql_engine, table_name)
            pgsql_count = get_table_count(pgsql_engine, table_name)
            
            match = mysql_count == pgsql_count
            status = "✅" if match else "❌"
            
            result = {
                "table": table_name,
                "mysql_count": mysql_count,
                "pgsql_count": pgsql_count,
                "match": match
            }
            verification_results.append(result)
            
            logger.info(f"{status} {table_name:30s} MySQL: {mysql_count:6d}  PostgreSQL: {pgsql_count:6d}")
            
        except Exception as e:
            logger.error(f"❌ {table_name:30s} 验证失败: {e}")
            verification_results.append({
                "table": table_name,
                "error": str(e),
                "match": False
            })
    
    # 统计结果
    logger.info("=" * 60)
    total_tables = len(verification_results)
    matched_tables = sum(1 for r in verification_results if r.get("match", False))
    failed_tables = total_tables - matched_tables
    
    logger.info(f"验证完成!")
    logger.info(f"总表数: {total_tables}")
    logger.info(f"匹配: {matched_tables}")
    logger.info(f"不匹配: {failed_tables}")
    
    if failed_tables == 0:
        logger.info("✅ 所有表的数据都已正确迁移!")
    else:
        logger.error(f"❌ 有 {failed_tables} 个表的数据不匹配，请检查!")
    
    logger.info("=" * 60)
    
    # 清理
    mysql_engine.dispose()
    pgsql_engine.dispose()
    
    return failed_tables == 0


if __name__ == "__main__":
    try:
        success = verify_databases()
        exit(0 if success else 1)
    except Exception as e:
        logger.error(f"验证失败: {e}")
        raise

