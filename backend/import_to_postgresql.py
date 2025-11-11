"""
PostgreSQL 数据导入脚本

功能:
- 从导出的 JSON 文件导入数据到 PostgreSQL
- 自动处理类型转换（如布尔值）
- 验证导入完整性
"""
import os
import json
from datetime import datetime
from sqlalchemy import create_engine, inspect, MetaData, Table, text
from sqlalchemy.orm import sessionmaker
from typing import Dict, Any, List
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# PostgreSQL 连接配置
POSTGRESQL_URL = os.getenv(
    "POSTGRESQL_URL",
    "postgresql://microgrid:microgrid123@10.10.20.10:14632/new_md_agent"
)

# 导入目录（应该是导出脚本创建的目录）
IMPORT_DIR = "mysql_export"

# 布尔字段映射（需要从字符串转换为布尔值）
BOOLEAN_FIELDS = {
    "db_connections": ["is_active"]
}


def convert_boolean_fields(table_name: str, row: Dict[str, Any]) -> Dict[str, Any]:
    """转换布尔字段"""
    if table_name in BOOLEAN_FIELDS:
        for field in BOOLEAN_FIELDS[table_name]:
            if field in row:
                value = row[field]
                if isinstance(value, str):
                    row[field] = value.lower() in ("true", "1", "yes")
                elif value is None:
                    row[field] = False
    return row


def import_table(engine, table_name: str, import_dir: str) -> int:
    """
    导入单个表的数据
    
    Args:
        engine: SQLAlchemy 引擎
        table_name: 表名
        import_dir: 导入目录
        
    Returns:
        导入的行数
    """
    logger.info(f"开始导入表: {table_name}")
    
    # 读取数据文件
    input_file = os.path.join(import_dir, f"{table_name}.json")
    if not os.path.exists(input_file):
        logger.warning(f"文件不存在，跳过: {input_file}")
        return 0
    
    with open(input_file, 'r', encoding='utf-8') as f:
        rows = json.load(f)
    
    if not rows:
        logger.info(f"表 {table_name} 没有数据")
        return 0
    
    # 反射表结构
    metadata = MetaData()
    table = Table(table_name, metadata, autoload_with=engine)
    
    # 转换数据
    converted_rows = []
    for row in rows:
        converted_row = convert_boolean_fields(table_name, row)
        converted_rows.append(converted_row)
    
    # 插入数据
    with engine.connect() as conn:
        # 开启事务
        with conn.begin():
            # 批量插入
            conn.execute(table.insert(), converted_rows)
            
            # 如果表有自增字段，重置序列
            # PostgreSQL 的序列需要手动更新
            try:
                # 获取主键列
                pk_columns = [col.name for col in table.primary_key.columns]
                if pk_columns:
                    pk_col = pk_columns[0]
                    # 查询最大值
                    max_id = conn.execute(text(f"SELECT MAX({pk_col}) FROM {table_name}")).scalar()
                    if max_id:
                        # 尝试重置序列（如果存在）
                        try:
                            conn.execute(text(f"SELECT setval(pg_get_serial_sequence('{table_name}', '{pk_col}'), {max_id})"))
                            logger.info(f"重置序列: {table_name}.{pk_col} -> {max_id}")
                        except:
                            pass  # 如果没有序列，忽略错误
            except Exception as e:
                logger.warning(f"重置序列失败（可能不需要）: {e}")
    
    logger.info(f"表 {table_name} 导入完成: {len(converted_rows)} 行")
    return len(converted_rows)


def import_all_tables():
    """导入所有表"""
    # 检查导入目录
    if not os.path.exists(IMPORT_DIR):
        logger.error(f"导入目录不存在: {IMPORT_DIR}")
        return
    
    # 读取导出统计
    stats_file = os.path.join(IMPORT_DIR, "_export_stats.json")
    if not os.path.exists(stats_file):
        logger.error(f"导出统计文件不存在: {stats_file}")
        return
    
    with open(stats_file, 'r', encoding='utf-8') as f:
        export_stats = json.load(f)
    
    logger.info(f"导出时间: {export_stats['export_time']}")
    logger.info(f"源数据库: {export_stats['source_database']}")
    
    # 创建引擎
    logger.info(f"连接到 PostgreSQL: {POSTGRESQL_URL.split('@')[1]}")  # 不显示密码
    engine = create_engine(POSTGRESQL_URL)
    
    # 导入统计
    import_stats = {
        "import_time": datetime.now().isoformat(),
        "target_database": "postgresql",
        "tables": {}
    }
    
    # 导入每个表
    table_names = list(export_stats["tables"].keys())
    logger.info(f"准备导入 {len(table_names)} 个表")
    
    for table_name in table_names:
        try:
            row_count = import_table(engine, table_name, IMPORT_DIR)
            export_count = export_stats["tables"][table_name].get("row_count", 0)
            
            import_stats["tables"][table_name] = {
                "row_count": row_count,
                "expected_count": export_count,
                "match": row_count == export_count,
                "status": "success"
            }
        except Exception as e:
            logger.error(f"导入表 {table_name} 失败: {e}")
            import_stats["tables"][table_name] = {
                "row_count": 0,
                "status": "failed",
                "error": str(e)
            }
    
    # 保存导入统计
    import_stats_file = os.path.join(IMPORT_DIR, "_import_stats.json")
    with open(import_stats_file, 'w', encoding='utf-8') as f:
        json.dump(import_stats, f, ensure_ascii=False, indent=2)
    
    logger.info("=" * 60)
    logger.info("导入完成!")
    logger.info(f"总表数: {len(table_names)}")
    logger.info(f"成功: {sum(1 for t in import_stats['tables'].values() if t['status'] == 'success')}")
    logger.info(f"失败: {sum(1 for t in import_stats['tables'].values() if t['status'] == 'failed')}")
    logger.info(f"总行数: {sum(t.get('row_count', 0) for t in import_stats['tables'].values())}")
    
    # 检查数据一致性
    mismatches = [
        name for name, stats in import_stats['tables'].items()
        if not stats.get('match', True) and stats['status'] == 'success'
    ]
    if mismatches:
        logger.warning(f"警告: 以下表的行数不匹配: {', '.join(mismatches)}")
    else:
        logger.info("✅ 所有表的行数都匹配!")
    
    logger.info("=" * 60)
    
    engine.dispose()


if __name__ == "__main__":
    try:
        import_all_tables()
    except Exception as e:
        logger.error(f"导入失败: {e}")
        raise

