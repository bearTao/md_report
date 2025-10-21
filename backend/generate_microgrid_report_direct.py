"""
直接生成并保存微网格预分析报告
"""
import asyncio
import sys
import os
import uuid
from datetime import datetime

sys.path.insert(0, os.path.dirname(__file__))

from app.services.scheduler import ExecutionScheduler
from app.services.context import ExecutionContext
from app.services.renderer import template_renderer
from app.core.models import VariableMetadata
from app.connectors.database import db_connector
from sqlalchemy import create_engine
from dotenv import load_dotenv

load_dotenv()

# 配置数据库连接
DB_HOST = os.getenv("DB_HOST", "10.10.20.10")
DB_PORT = os.getenv("DB_PORT", "24406")
DB_USER = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD", "123456")
DB_NAME = "microgrid"

DATABASE_URL = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}?charset=utf8mb4"

# 注册数据库连接
engine = create_engine(DATABASE_URL)
db_connector.register_connection("microgrid_db", engine)

print("✅ 数据库连接已注册\n")

# 从API获取模板内容
import requests
import json

print("📥 获取模板内容...")
response = requests.get("http://localhost:8000/api/templates/tpl_21c2afbe565c")
template_data = response.json()

template_content = template_data["template_content"]
metadata_json = template_data["metadata_json"]

print(f"✅ 模板获取成功: {template_data['name']}")
print(f"   变量数量: {len(metadata_json)}")
print(f"   模板长度: {len(template_content)} 字符\n")


async def generate_report():
    """生成报告"""
    print("=" * 80)
    print("开始生成微网格预分析报告")
    print("=" * 80 + "\n")
    
    # 用户输入
    user_inputs = {"wgid": "ZQGY0174"}
    
    # 转换元数据
    metadata = {k: VariableMetadata(**v) for k, v in metadata_json.items()}
    
    # 创建执行上下文
    task_id = f"direct_task_{uuid.uuid4().hex[:12]}"
    context = ExecutionContext(
        task_id=task_id,
        template_id="tpl_21c2afbe565c",
        user_inputs=user_inputs,
        metadata=metadata
    )
    
    # 执行所有变量
    scheduler = ExecutionScheduler()
    
    print("⚙️  执行变量...")
    results = await scheduler.execute_all(context)
    
    success_count = sum(1 for r in results.values() if r.status.value == "success")
    error_count = len(results) - success_count
    
    print(f"✅ 变量执行完成: 成功 {success_count}/{len(results)}\n")
    
    if error_count > 0:
        print(f"⚠️  有 {error_count} 个变量执行失败:")
        for var_name, result in results.items():
            if result.status.value != "success":
                print(f"   ❌ {var_name}: {result.error}")
        print()
    
    # 渲染模板
    print("📄 渲染模板...")
    markdown_content = template_renderer.render(template_content, context.get_all_variables())
    
    print(f"✅ 模板渲染完成: {len(markdown_content)} 字符\n")
    
    # 保存到数据库（使用SQLAlchemy）
    print("💾 保存到数据库...")
    report_id = f"rpt_{uuid.uuid4().hex[:12]}"
    
    from app.database import SessionLocal
    from app.models.db_models import Report, ReportStatus
    
    db = SessionLocal()
    try:
        report = Report(
            id=report_id,
            template_id="tpl_21c2afbe565c",
            task_id=task_id,
            title=f"微网格预分析-{user_inputs['wgid']}",
            status=ReportStatus.SUCCESS,
            markdown_content=markdown_content,
            duration_ms=sum(v.duration_ms for v in results.values()),
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        db.add(report)
        db.commit()
        db.refresh(report)
        print(f"✅ 报告已保存到MySQL数据库")
    except Exception as e:
        db.rollback()
        print(f"❌ 保存失败: {e}")
        raise
    finally:
        db.close()
    
    print(f"✅ 报告已保存到数据库\n")
    
    # 保存到文件
    output_file = f"/data/tao/code/xuqiu/backend/microgrid_report_{user_inputs['wgid']}.md"
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(markdown_content)
    
    print(f"✅ 报告已保存到文件: {output_file}\n")
    
    print("=" * 80)
    print("报告生成成功！")
    print("=" * 80)
    print(f"报告ID: {report_id}")
    print(f"报告长度: {len(markdown_content)} 字符")
    print(f"报告行数: {len(markdown_content.splitlines())} 行")
    print(f"文件位置: {output_file}")
    
    # 预览报告
    print("\n" + "=" * 80)
    print("报告预览 (前50行):")
    print("=" * 80)
    lines = markdown_content.split('\n')
    for line in lines[:50]:
        print(line)
    if len(lines) > 50:
        print(f"\n... 还有 {len(lines) - 50} 行")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(generate_report())

