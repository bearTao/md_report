"""
常量类型完整集成测试

测试从数据库到执行的完整链路
"""
import asyncio
from app.core.models import VariableMetadata, VariableSource, ApiConfig
from app.models.db_models import GenerationTaskVariable, VariableSourceType, VariableStatusType
from app.database import SessionLocal
from app.services.scheduler import ExecutionScheduler
from app.services.context import ExecutionContext
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_constant_execution():
    """测试常量执行"""
    logger.info("=" * 60)
    logger.info("测试 1: 常量变量执行")
    logger.info("=" * 60)
    
    metadata = {
        "test_constant": VariableMetadata(
            type="string",
            source=VariableSource.CONSTANT,
            description="测试常量",
            value="test_value_123"
        )
    }
    
    context = ExecutionContext("test_integration", "test_template", {}, metadata)
    scheduler = ExecutionScheduler()
    
    try:
        results = await scheduler.execute_all(context)
        assert "test_constant" in results
        assert results["test_constant"].value == "test_value_123"
        logger.info("✅ 常量执行成功")
        return True
    except Exception as e:
        logger.error(f"❌ 常量执行失败: {e}")
        return False


def test_database_insert():
    """测试数据库插入"""
    logger.info("\n" + "=" * 60)
    logger.info("测试 2: 数据库插入常量记录")
    logger.info("=" * 60)
    
    db = SessionLocal()
    test_task_id = "test_constant_db_insert"
    
    try:
        # 清理旧数据
        db.query(GenerationTaskVariable).filter(
            GenerationTaskVariable.task_id == test_task_id
        ).delete()
        db.commit()
        
        # 插入测试记录
        record = GenerationTaskVariable(
            task_id=test_task_id,
            variable_name="test_constant_var",
            source=VariableSourceType.CONSTANT,  # 使用枚举
            status=VariableStatusType.SUCCESS
        )
        db.add(record)
        db.commit()
        
        logger.info("✅ 数据库插入成功")
        
        # 验证读取
        saved = db.query(GenerationTaskVariable).filter(
            GenerationTaskVariable.task_id == test_task_id
        ).first()
        
        assert saved is not None
        assert saved.source == VariableSourceType.CONSTANT
        logger.info(f"✅ 数据库读取验证成功: source={saved.source.value}")
        
        # 清理
        db.delete(saved)
        db.commit()
        
        return True
        
    except Exception as e:
        logger.error(f"❌ 数据库操作失败: {e}")
        db.rollback()
        return False
    finally:
        db.close()


def test_enum_consistency():
    """测试枚举一致性"""
    logger.info("\n" + "=" * 60)
    logger.info("测试 3: 枚举定义一致性")
    logger.info("=" * 60)
    
    try:
        # 检查核心枚举
        core_constant = VariableSource.CONSTANT
        logger.info(f"核心枚举: VariableSource.CONSTANT = '{core_constant.value}'")
        
        # 检查数据库枚举
        db_constant = VariableSourceType.CONSTANT
        logger.info(f"数据库枚举: VariableSourceType.CONSTANT = '{db_constant.value}'")
        
        # 验证值一致
        assert core_constant.value == db_constant.value == "constant"
        logger.info("✅ 枚举值一致")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ 枚举检查失败: {e}")
        return False


async def main():
    """运行所有测试"""
    logger.info("\n" + "🧪" * 30)
    logger.info("CONSTANT 类型完整集成测试")
    logger.info("🧪" * 30)
    
    tests = [
        ("枚举一致性", test_enum_consistency),
        ("常量执行", test_constant_execution),
        ("数据库操作", test_database_insert),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            if asyncio.iscoroutinefunction(test_func):
                result = await test_func()
            else:
                result = test_func()
            results.append((name, result))
        except Exception as e:
            logger.error(f"\n测试 '{name}' 异常: {e}")
            results.append((name, False))
    
    # 输出结果
    logger.info("\n" + "=" * 60)
    logger.info("测试结果总结")
    logger.info("=" * 60)
    
    all_passed = True
    for name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        logger.info(f"  {name}: {status}")
        if not result:
            all_passed = False
    
    logger.info("\n" + "=" * 60)
    if all_passed:
        logger.info("🎉 所有测试通过！CONSTANT 类型功能完整可用")
        logger.info("\n现在可以:")
        logger.info("  1. 重启后端服务")
        logger.info("  2. 刷新前端页面")
        logger.info("  3. 创建包含常量的模板")
        logger.info("  4. 验证前端显示和执行")
    else:
        logger.error("❌ 部分测试失败，请检查错误信息")


if __name__ == "__main__":
    asyncio.run(main())

