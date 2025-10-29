"""测试嵌套模板的报告生成"""
import asyncio
import sys
sys.path.insert(0, '/data/tao/code/xuqiu/backend')

from app.database import SessionLocal
from app.models.db_models import Template, GenerationTask, GenerationTaskVariable, ExecutionLog
from app.api.reports import execute_report_generation
from datetime import datetime


async def test_nested_template_generation():
    """测试嵌套模板报告生成，带有正确的嵌套输入"""
    
    db = SessionLocal()
    
    try:
        # 1. 查找模板
        main_template = db.query(Template).filter(Template.id == 'tpl_8d46934e172c').first()
        if not main_template:
            print("❌ 未找到主模板 tpl_8d46934e172c")
            return
        
        print(f"✓ 主模板: {main_template.name} (ID: {main_template.id})")
        
        # 2. 构造嵌套输入
        # 关键：必须包含主模板和子模板的输入
        nested_user_inputs = {
            "tpl_8d46934e172c": {  # 主模板输入
                "title": "主模板标题测试",
                "content": "主模板内容测试"
            },
            "tpl_e710aea7c613": {  # 子模板1输入
                "title1": "子模板1标题测试",
                "content1": "子模板1内容测试"
            }
        }
        
        print(f"\n构造的嵌套输入:")
        import json
        print(json.dumps(nested_user_inputs, indent=2, ensure_ascii=False))
        
        # 3. 创建任务
        task_id = f"task_test_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        task = GenerationTask(
            id=task_id,
            template_id=main_template.id,
            inputs_json=nested_user_inputs,
            status='pending'
        )
        db.add(task)
        db.commit()
        
        print(f"\n✓ 创建任务: {task_id}")
        
        # 4. 执行报告生成
        print("\n开始执行报告生成...")
        await execute_report_generation(
            task_id=task_id,
            template_id=main_template.id,
            user_inputs=nested_user_inputs,
            db_session=db
        )
        
        # 5. 查看结果
        print("\n" + "="*60)
        print("执行完成，查看结果:")
        print("="*60)
        
        # 查看变量执行记录
        variables = db.query(GenerationTaskVariable).filter(
            GenerationTaskVariable.task_id == task_id
        ).all()
        
        print(f"\n变量执行记录 (共 {len(variables)} 个):")
        for var in variables:
            print(f"  - 变量: {var.variable_name}")
            print(f"    所属模板: {var.template_id}")
            print(f"    模板路径: {var.template_path}")
            print(f"    状态: {var.status}")
        
        # 查看日志
        logs = db.query(ExecutionLog).filter(
            ExecutionLog.task_id == task_id
        ).order_by(ExecutionLog.created_at).all()
        
        print(f"\n执行日志 (共 {len(logs)} 条):")
        for log in logs:
            var_name = log.variable_name or "system"
            print(f"  [{log.level.value}] {var_name}: {log.message[:80]}")
            if log.template_path:
                print(f"    路径: {log.template_path}")
        
        # 查看任务状态
        task = db.query(GenerationTask).filter(GenerationTask.id == task_id).first()
        print(f"\n任务状态: {task.status}")
        
        # 检查是否有子模板的变量
        sub_template_vars = [v for v in variables if v.template_id == 'tpl_e710aea7c613']
        if sub_template_vars:
            print(f"\n✅ 成功！检测到 {len(sub_template_vars)} 个子模板变量:")
            for v in sub_template_vars:
                print(f"   - {v.variable_name} ({v.template_path})")
        else:
            print("\n❌ 失败！没有检测到子模板的变量执行记录")
        
    except Exception as e:
        print(f"\n❌ 执行失败: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()


if __name__ == "__main__":
    asyncio.run(test_nested_template_generation())

