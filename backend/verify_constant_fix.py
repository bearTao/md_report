"""
验证 CONSTANT 类型修复完整性

用法:
    python verify_constant_fix.py

检查项:
    1. Python 枚举定义
    2. 数据库 ENUM 定义
    3. 实际插入测试
"""
import sys
from sqlalchemy import create_engine, text
from app.database import DATABASE_URL
from app.core.models import VariableSource
from app.models.db_models import VariableSourceType
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def check_python_enum():
    """检查 Python 枚举定义"""
    logger.info("\n检查 1: Python 枚举定义")
    logger.info("-" * 40)
    
    # 检查核心模型
    try:
        has_constant_core = hasattr(VariableSource, 'CONSTANT')
        logger.info(f"  app.core.models.VariableSource.CONSTANT: {'✓ 存在' if has_constant_core else '✗ 不存在'}")
        if has_constant_core:
            logger.info(f"    值: {VariableSource.CONSTANT.value}")
    except Exception as e:
        logger.error(f"  ✗ 检查失败: {e}")
        return False
    
    # 检查数据库模型
    try:
        has_constant_db = hasattr(VariableSourceType, 'CONSTANT')
        logger.info(f"  app.models.db_models.VariableSourceType.CONSTANT: {'✓ 存在' if has_constant_db else '✗ 不存在'}")
        if has_constant_db:
            logger.info(f"    值: {VariableSourceType.CONSTANT.value}")
    except Exception as e:
        logger.error(f"  ✗ 检查失败: {e}")
        return False
    
    if has_constant_core and has_constant_db:
        logger.info("  结果: ✓ 通过")
        return True
    else:
        logger.error("  结果: ✗ 失败")
        return False


def check_database_enum():
    """检查数据库 ENUM 定义"""
    logger.info("\n检查 2: 数据库 ENUM 定义")
    logger.info("-" * 40)
    
    try:
        engine = create_engine(DATABASE_URL)
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
                enum_def = row[0]
                logger.info(f"  当前定义: {enum_def}")
                
                if "'constant'" in enum_def:
                    logger.info("  结果: ✓ 'constant' 已包含在数据库 ENUM 中")
                    return True
                else:
                    logger.error("  结果: ✗ 'constant' 未包含在数据库 ENUM 中")
                    logger.error("  请运行迁移脚本: python migrate_add_constant.py")
                    return False
            else:
                logger.error("  ✗ 无法获取 ENUM 定义")
                return False
    except Exception as e:
        logger.error(f"  ✗ 检查失败: {e}")
        return False


def check_database_insert():
    """测试实际插入常量记录"""
    logger.info("\n检查 3: 数据库插入测试")
    logger.info("-" * 40)
    
    try:
        engine = create_engine(DATABASE_URL)
        test_task_id = "test_constant_verification"
        
        with engine.begin() as conn:
            # 清除可能的旧测试数据
            conn.execute(text("""
                DELETE FROM generation_task_variables 
                WHERE task_id = :task_id
            """), {"task_id": test_task_id})
            
            # 尝试插入测试记录
            logger.info("  尝试插入 source='constant' 的测试记录...")
            conn.execute(text("""
                INSERT INTO generation_task_variables 
                (task_id, variable_name, source, status) 
                VALUES (:task_id, :var_name, :source, :status)
            """), {
                "task_id": test_task_id,
                "var_name": "test_constant_var",
                "source": "constant",
                "status": "pending"
            })
            
            logger.info("  ✓ 插入成功")
            
            # 验证插入
            result = conn.execute(text("""
                SELECT source FROM generation_task_variables 
                WHERE task_id = :task_id
            """), {"task_id": test_task_id})
            row = result.fetchone()
            
            if row and row[0] == "constant":
                logger.info(f"  ✓ 验证成功: 读取到 source='{row[0]}'")
                
                # 清理测试数据
                conn.execute(text("""
                    DELETE FROM generation_task_variables 
                    WHERE task_id = :task_id
                """), {"task_id": test_task_id})
                logger.info("  ✓ 测试数据已清理")
                
                logger.info("  结果: ✓ 通过")
                return True
            else:
                logger.error("  ✗ 验证失败: 无法读取插入的记录")
                return False
                
    except Exception as e:
        logger.error(f"  ✗ 测试失败: {e}")
        logger.error("  这通常表示数据库 ENUM 未更新")
        logger.error("  请运行迁移脚本: python migrate_add_constant.py")
        return False


def verify():
    """执行所有验证"""
    logger.info("=" * 60)
    logger.info("CONSTANT 类型修复验证")
    logger.info("=" * 60)
    
    checks = [
        ("Python 枚举定义", check_python_enum),
        ("数据库 ENUM 定义", check_database_enum),
        ("数据库插入测试", check_database_insert),
    ]
    
    results = []
    for name, check_func in checks:
        try:
            result = check_func()
            results.append((name, result))
        except Exception as e:
            logger.error(f"\n检查 '{name}' 时发生异常: {e}")
            results.append((name, False))
    
    # 输出总结
    logger.info("\n" + "=" * 60)
    logger.info("验证结果总结")
    logger.info("=" * 60)
    
    all_passed = True
    for name, result in results:
        status = "✓ 通过" if result else "✗ 失败"
        logger.info(f"  {name}: {status}")
        if not result:
            all_passed = False
    
    logger.info("\n" + "=" * 60)
    if all_passed:
        logger.info("✓ 所有检查通过！CONSTANT 类型已正确配置")
        logger.info("\n你现在可以:")
        logger.info("  1. 创建包含 source: constant 的变量")
        logger.info("  2. 使用常量自动注入功能")
        logger.info("  3. 在前端查看常量变量的执行状态")
        return True
    else:
        logger.error("✗ 部分检查失败")
        logger.error("\n修复步骤:")
        logger.error("  1. 如果 Python 枚举失败: 检查代码文件是否正确更新")
        logger.error("  2. 如果数据库检查失败: 运行 python migrate_add_constant.py")
        logger.error("  3. 如果插入测试失败: 确保迁移已成功执行")
        return False


if __name__ == "__main__":
    success = verify()
    sys.exit(0 if success else 1)

