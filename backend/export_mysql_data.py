"""
MySQL 数据导出脚本

功能:
- 从 MySQL 数据库导出所有表的数据
- 保存为 JSON 格式，便于导入到 PostgreSQL
- 记录每个表的行数和导出时间
"""
import os
import json
from datetime import datetime
from sqlalchemy import create_engine, inspect, MetaData, Table
from sqlalchemy.orm import sessionmaker
from typing import Dict, Any, List
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# MySQL 连接配置
MYSQL_URL = os.getenv(
    "MYSQL_URL",
    "mysql+pymysql://root:123456@10.10.20.10:24406/md_agent?charset=utf8mb4"
)

# 导出目录
EXPORT_DIR = "mysql_export"


def convert_to_serializable(obj: Any) -> Any:
    """转换对象为 JSON 可序列化格式"""
    if isinstance(obj, datetime):
        return obj.isoformat()
    elif isinstance(obj, bytes):
        return obj.decode('utf-8', errors='ignore')
    elif obj is None:
        return None
    else:
        return obj


def export_table(engine, table_name: str, output_dir: str) -> int:
    """
    导出单个表的数据
    
    Args:
        engine: SQLAlchemy 引擎
        table_name: 表名
        output_dir: 输出目录
        
    Returns:
        导出的行数
    """
    logger.info(f"开始导出表: {table_name}")
    
    # 反射表结构
    metadata = MetaData()
    table = Table(table_name, metadata, autoload_with=engine)
    
    # 查询所有数据
    with engine.connect() as conn:
        result = conn.execute(table.select())
        rows = []
        
        for row in result:
            row_dict = {}
            for key, value in row._mapping.items():
                row_dict[key] = convert_to_serializable(value)
            rows.append(row_dict)
    
    # 保存到文件
    output_file = os.path.join(output_dir, f"{table_name}.json")
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(rows, f, ensure_ascii=False, indent=2)
    
    logger.info(f"表 {table_name} 导出完成: {len(rows)} 行")
    return len(rows)


def export_all_tables():
    """导出所有表"""
    # 创建输出目录
    os.makedirs(EXPORT_DIR, exist_ok=True)
    
    # 创建引擎
    logger.info(f"连接到 MySQL: {MYSQL_URL.split('@')[1]}")  # 不显示密码
    engine = create_engine(MYSQL_URL)
    
    # 获取所有表名
    inspector = inspect(engine)
    table_names = inspector.get_table_names()
    
    logger.info(f"找到 {len(table_names)} 个表")
    
    # 导出统计
    export_stats = {
        "export_time": datetime.now().isoformat(),
        "source_database": "mysql",
        "tables": {}
    }
    
    # 导出每个表
    for table_name in table_names:
        try:
            row_count = export_table(engine, table_name, EXPORT_DIR)
            export_stats["tables"][table_name] = {
                "row_count": row_count,
                "status": "success"
            }
        except Exception as e:
            logger.error(f"导出表 {table_name} 失败: {e}")
            export_stats["tables"][table_name] = {
                "row_count": 0,
                "status": "failed",
                "error": str(e)
            }
    
    # 保存导出统计
    stats_file = os.path.join(EXPORT_DIR, "_export_stats.json")
    with open(stats_file, 'w', encoding='utf-8') as f:
        json.dump(export_stats, f, ensure_ascii=False, indent=2)
    
    logger.info("=" * 60)
    logger.info("导出完成!")
    logger.info(f"总表数: {len(table_names)}")
    logger.info(f"成功: {sum(1 for t in export_stats['tables'].values() if t['status'] == 'success')}")
    logger.info(f"失败: {sum(1 for t in export_stats['tables'].values() if t['status'] == 'failed')}")
    logger.info(f"总行数: {sum(t.get('row_count', 0) for t in export_stats['tables'].values())}")
    logger.info(f"输出目录: {EXPORT_DIR}")
    logger.info("=" * 60)
    
    engine.dispose()


if __name__ == "__main__":
    try:
        export_all_tables()
    except Exception as e:
        logger.error(f"导出失败: {e}")
        raise

