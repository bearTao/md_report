"""
数据库迁移脚本：添加 'constant' 到 VariableSourceType ENUM

用法:
    python migrate_add_constant.py

功能:
    - 添加 'constant' 值到 generation_task_variables.source ENUM
    - 自动检测当前 ENUM 值
    - 安全执行，包含验证
"""
import sys
from sqlalchemy import create_engine, text
from app.database import DATABASE_URL
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def get_current_enum_values(engine):
    """获取当前 source 字段的 ENUM 值"""
    try:
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT COLUMN_TYPE 
                FROM INFORMATION_SCHEMA.COLUMNS 
                WHERE TABLE_SCHEMA = DATABASE()
                AND TABLE_NAME = 'generation_task_variables' 
                AND COLUMN_NAME = 'source'
            """))
            row = result.fetchone()
            if row:
                # 格式: enum('user_input','sql',...)
                enum_def = row[0]
                logger.info(f"当前 ENUM 定义: {enum_def}")
                return enum_def
            return None
    except Exception as e:
        logger.error(f"获取 ENUM 定义失败: {e}")
        return None


def check_constant_exists(enum_def):
    """检查 'constant' 是否已存在"""
    if enum_def and "'constant'" in enum_def:
        return True
    return False


def migrate():
    """执行迁移"""
    logger.info("=" * 60)
    logger.info("开始数据库迁移：添加 'constant' 到 VariableSourceType")
    logger.info("=" * 60)
    
    # 创建数据库连接
    try:
        engine = create_engine(DATABASE_URL)
        logger.info(f"✓ 连接数据库成功: {DATABASE_URL.split('@')[1] if '@' in DATABASE_URL else 'local'}")
    except Exception as e:
        logger.error(f"✗ 连接数据库失败: {e}")
        return False
    
    # 检查当前 ENUM 值
    logger.info("\n步骤 1: 检查当前 ENUM 定义...")
    enum_def = get_current_enum_values(engine)
    if not enum_def:
        logger.error("✗ 无法获取当前 ENUM 定义")
        return False
    
    # 检查是否已包含 constant
    if check_constant_exists(enum_def):
        logger.info("✓ 'constant' 已存在于 ENUM 中，无需迁移")
        return True
    
    logger.info("✗ 'constant' 不存在，需要迁移")
    
    # 执行迁移
    logger.info("\n步骤 2: 执行 ALTER TABLE...")
    try:
        with engine.begin() as conn:
            conn.execute(text("""
                ALTER TABLE generation_task_variables 
                MODIFY COLUMN source ENUM(
                    'user_input', 
                    'sql', 
                    'api', 
                    'ai_generation', 
                    'system',
                    'constant',
                    'image',
                    'vision_ai'
                ) NOT NULL
            """))
        logger.info("✓ ALTER TABLE 执行成功")
    except Exception as e:
        logger.error(f"✗ ALTER TABLE 失败: {e}")
        return False
    
    # 验证迁移
    logger.info("\n步骤 3: 验证迁移结果...")
    enum_def_after = get_current_enum_values(engine)
    if check_constant_exists(enum_def_after):
        logger.info("✓ 验证成功：'constant' 已添加到 ENUM")
        logger.info(f"新的 ENUM 定义: {enum_def_after}")
        return True
    else:
        logger.error("✗ 验证失败：'constant' 未添加到 ENUM")
        return False


if __name__ == "__main__":
    logger.info("\n数据库迁移工具")
    logger.info("功能：添加 'constant' 值到 VariableSourceType ENUM\n")
    
    # 执行迁移
    success = migrate()
    
    # 输出结果
    logger.info("\n" + "=" * 60)
    if success:
        logger.info("✓ 迁移完成")
        logger.info("\n后续步骤:")
        logger.info("  1. 重启后端服务")
        logger.info("  2. 运行验证脚本: python verify_constant_fix.py")
        logger.info("  3. 测试常量变量功能")
        sys.exit(0)
    else:
        logger.error("✗ 迁移失败")
        logger.error("\n请检查:")
        logger.error("  1. 数据库连接配置")
        logger.error("  2. 数据库权限")
        logger.error("  3. 错误日志")
        sys.exit(1)

