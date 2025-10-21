#!/usr/bin/env python3
"""
最终测试：完整的报告生成流程
"""

import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from app.services.context import ExecutionContext
from app.services.scheduler import ExecutionScheduler
from app.core.models import VariableMetadata
from app.database import SessionLocal
from app.models.db_models import Template


async def test_full_report_generation():
    """测试完整的报告生成流程"""
    
    # 注册数据库连接
    from app.connectors.database import db_connector  # 使用全局单例
    import os
    
    # 从环境变量获取数据库URL，或使用默认值
    db_url = os.getenv('DATABASE_URL', 'mysql+pymysql://root:zaq1xsw2@localhost:13306/md_agent')
    microgrid_url = db_url.replace('/md_agent', '/microgrid')
    
    # 注册microgrid_db连接（MySQL）
    try:
        db_connector.register_connection(
            name="microgrid_db",
            connection_url_or_engine=microgrid_url,
            pool_size=5,
            max_overflow=10
        )
        print(f"✅ 已注册 microgrid_db 连接")
    except Exception as e:
        print(f"⚠️ 注册 microgrid_db 失败（可能已注册）: {e}")
    
    db = SessionLocal()
    
    try:
        # 获取模板（使用MySQL AI版本）
        template_id = 'tpl_ai_mysql'
        template = db.query(Template).filter(Template.id == template_id).first()
        
        if not template:
            print(f"❌ 未找到模板: {template_id}")
            return False
        
        print(f"✅ 找到模板: {template.name}")
        print("=" * 80)
        
        # 解析metadata
        metadata_dict = {}
        for var_name, var_data in template.metadata_json.items():
            metadata_dict[var_name] = VariableMetadata.model_validate(var_data)
        
        print(f"📊 变量总数: {len(metadata_dict)}")
        
        # 统计变量类型
        from app.core.models import VariableSource
        sql_vars = {k: v for k, v in metadata_dict.items() if v.source == VariableSource.SQL}
        ai_vars = {k: v for k, v in metadata_dict.items() if v.source == VariableSource.AI_GENERATION}
        user_vars = {k: v for k, v in metadata_dict.items() if v.source == VariableSource.USER_INPUT}
        
        print(f"  - 用户输入变量: {len(user_vars)}")
        print(f"  - SQL变量: {len(sql_vars)}")
        print(f"  - AI变量: {len(ai_vars)}")
        
        # 创建执行上下文
        user_inputs = {'wgid': 'ZQGY0174'}
        context = ExecutionContext(
            task_id="final_test",
            template_id=template_id,
            user_inputs=user_inputs,
            metadata=metadata_dict
        )
        
        print(f"\n🎯 开始执行变量（用户输入: wgid={user_inputs['wgid']}）")
        print("=" * 80)
        
        # 创建调度器
        scheduler = ExecutionScheduler(metadata_dict)
        
        # 执行所有变量（不使用进度回调以简化测试）
        try:
            results = await scheduler.execute_all(context, progress_callback=None)
            
            print("\n" + "=" * 80)
            print("📊 执行结果统计:")
            print("=" * 80)
            
            # 统计结果
            from app.core.models import VariableStatus
            success_count = sum(1 for r in results.values() if r.status == VariableStatus.SUCCESS)
            failed_count = sum(1 for r in results.values() if r.status == VariableStatus.FAILED)
            
            print(f"✅ 成功: {success_count}")
            print(f"❌ 失败: {failed_count}")
            
            # 显示失败的变量
            if failed_count > 0:
                print("\n失败的变量:")
                for var_name, result in results.items():
                    if result.status == VariableStatus.FAILED:
                        print(f"  - {var_name}: {result.error}")
            
            # 显示AI变量执行结果
            print("\nAI变量执行结果:")
            for var_name in ai_vars.keys():
                if var_name in results:
                    result = results[var_name]
                    status = "✅" if result.status == VariableStatus.SUCCESS else "❌"
                    duration = result.duration_ms
                    print(f"  {status} {var_name} ({duration}ms)")
            
            if failed_count == 0:
                print("\n" + "=" * 80)
                print("🎉 所有变量执行成功！")
                print("=" * 80)
                return True
            else:
                print("\n" + "=" * 80)
                print("⚠️ 部分变量执行失败，但这可能是预期的（如可选变量）")
                print("=" * 80)
                # 检查是否只是可选变量失败
                required_failed = sum(
                    1 for var_name, result in results.items()
                    if result.status == VariableStatus.FAILED and 
                       metadata_dict[var_name].required
                )
                
                if required_failed == 0:
                    print("✅ 所有必需变量执行成功")
                    return True
                else:
                    print(f"❌ {required_failed} 个必需变量执行失败")
                    return False
                
        except Exception as e:
            print(f"\n❌ 执行失败: {e}")
            import traceback
            traceback.print_exc()
            return False
            
    finally:
        db.close()


async def main():
    print("\n" + "=" * 80)
    print("最终测试：完整报告生成流程")
    print("=" * 80 + "\n")
    
    success = await test_full_report_generation()
    
    if success:
        print("\n✅ 测试通过！系统已经可以正常工作了")
        return 0
    else:
        print("\n❌ 测试失败")
        return 1


if __name__ == '__main__':
    sys.exit(asyncio.run(main()))

