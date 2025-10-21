"""
完整测试微网格预分析报告生成
"""
import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from app.services.scheduler import ExecutionScheduler
from app.services.context import ExecutionContext
from app.services.renderer import template_renderer
from app.core.models import VariableMetadata
from app.connectors.database import db_connector
from sqlalchemy import create_engine
from dotenv import load_dotenv
import json

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

print("数据库连接已注册")


async def test_full_report():
    """测试完整报告生成"""
    print("\n" + "=" * 80)
    print("开始完整测试微网格预分析报告生成")
    print("=" * 80)
    
    # 用户输入
    user_inputs = {"wgid": "ZQGY0174"}
    
    # 从API获取的元数据
    metadata_json = {
        "wgid": {
            "type": "string",
            "source": "user_input",
            "description": "微网格标识",
            "required": True
        },
        "overview": {
            "type": "object",
            "source": "sql",
            "description": "微网格概况信息",
            "required": True,
            "dependencies": ["wgid"],
            "sql_config": {
                "connection": "microgrid_db",
                "query": "SELECT * FROM microgrid.micro_grid_overview_w WHERE wgid = :wgid ORDER BY endtime DESC LIMIT 1",
                "parameters": ["wgid"],
                "result_mode": "first_row",
                "timeout": 10
            }
        },
        "index_scores": {
            "type": "array",
            "source": "sql",
            "description": "指标评分列表",
            "required": False,
            "default": [],
            "dependencies": ["wgid"],
            "sql_config": {
                "connection": "microgrid_db",
                "query": "SELECT * FROM microgrid.micro_grid_index_score_w WHERE wgid = :wgid ORDER BY `index`",
                "parameters": ["wgid"],
                "result_mode": "all_rows",
                "timeout": 10
            }
        },
        "plan_sites": {
            "type": "array",
            "source": "sql",
            "description": "工程规划站点列表",
            "required": False,
            "default": [],
            "dependencies": ["wgid"],
            "sql_config": {
                "connection": "microgrid_db",
                "query": "SELECT * FROM microgrid.micro_grid_plan_w WHERE wgid = :wgid",
                "parameters": ["wgid"],
                "result_mode": "all_rows",
                "timeout": 10
            }
        },
        "problem_clusters": {
            "type": "array",
            "source": "sql",
            "description": "覆盖融合问题点列表",
            "required": False,
            "default": [],
            "dependencies": ["wgid"],
            "sql_config": {
                "connection": "microgrid_db",
                "query": "SELECT * FROM microgrid.micro_grid_problem_cluster_m WHERE wgid = :wgid",
                "parameters": ["wgid"],
                "result_mode": "all_rows",
                "timeout": 10
            }
        },
        "problem_grid_mdt": {
            "type": "array",
            "source": "sql",
            "description": "栅格MDT问题列表",
            "required": False,
            "default": [],
            "dependencies": ["wgid"],
            "sql_config": {
                "connection": "microgrid_db",
                "query": "SELECT * FROM microgrid.micro_grid_problem_grid_mdt_m WHERE wgid = :wgid AND intweak_count > 0 LIMIT 100",
                "parameters": ["wgid"],
                "result_mode": "all_rows",
                "timeout": 15
            }
        },
        "problem_buildings": {
            "type": "array",
            "source": "sql",
            "description": "问题楼宇列表",
            "required": False,
            "default": [],
            "dependencies": ["wgid"],
            "sql_config": {
                "connection": "microgrid_db",
                "query": "SELECT * FROM microgrid.micro_grid_problem_build_m WHERE wgid = :wgid AND is_issue_build = true",
                "parameters": ["wgid"],
                "result_mode": "all_rows",
                "timeout": 15
            }
        },
        "problem_grid_cloud": {
            "type": "array",
            "source": "sql",
            "description": "栅格云瞰问题列表",
            "required": False,
            "default": [],
            "dependencies": ["wgid"],
            "sql_config": {
                "connection": "microgrid_db",
                "query": "SELECT * FROM microgrid.micro_grid_problem_grid_cloud_m WHERE wgid = :wgid AND intweakcover_count > 0 LIMIT 100",
                "parameters": ["wgid"],
                "result_mode": "all_rows",
                "timeout": 15
            }
        },
        "building_type_stats": {
            "type": "array",
            "source": "sql",
            "description": "楼宇类型分布统计",
            "required": False,
            "default": [],
            "dependencies": ["wgid"],
            "sql_config": {
                "connection": "microgrid_db",
                "query": "SELECT build_type, COUNT(*) as count FROM microgrid.micro_grid_problem_build_m WHERE wgid = :wgid AND is_issue_build = true GROUP BY build_type",
                "parameters": ["wgid"],
                "result_mode": "all_rows",
                "timeout": 5
            }
        },
        "grid_mdt_weak_samples": {
            "type": "number",
            "source": "sql",
            "description": "栅格MDT弱覆盖采样点数",
            "required": False,
            "default": 0,
            "dependencies": ["wgid"],
            "sql_config": {
                "connection": "microgrid_db",
                "query": "SELECT COALESCE(SUM(intweak_count), 0) as total FROM microgrid.micro_grid_problem_grid_mdt_m WHERE wgid = :wgid",
                "parameters": ["wgid"],
                "result_mode": "first_value",
                "timeout": 5
            }
        },
        "grid_mdt_total_samples": {
            "type": "number",
            "source": "sql",
            "description": "栅格MDT总采样点数",
            "required": False,
            "default": 0,
            "dependencies": ["wgid"],
            "sql_config": {
                "connection": "microgrid_db",
                "query": "SELECT COALESCE(SUM(intmdt_count), 0) as total FROM microgrid.micro_grid_problem_grid_mdt_m WHERE wgid = :wgid",
                "parameters": ["wgid"],
                "result_mode": "first_value",
                "timeout": 5
            }
        },
        "buildings_4g_weak_count": {
            "type": "number",
            "source": "sql",
            "description": "4G弱覆盖楼宇数量",
            "required": False,
            "default": 0,
            "dependencies": ["wgid"],
            "sql_config": {
                "connection": "microgrid_db",
                "query": "SELECT COUNT(*) as count FROM microgrid.micro_grid_problem_build_m WHERE wgid = :wgid AND is_bad_cov_4g = true",
                "parameters": ["wgid"],
                "result_mode": "first_value",
                "timeout": 5
            }
        },
        "buildings_5g_weak_count": {
            "type": "number",
            "source": "sql",
            "description": "5G弱覆盖楼宇数量",
            "required": False,
            "default": 0,
            "dependencies": ["wgid"],
            "sql_config": {
                "connection": "microgrid_db",
                "query": "SELECT COUNT(*) as count FROM microgrid.micro_grid_problem_build_m WHERE wgid = :wgid AND is_bad_cov_5g = true",
                "parameters": ["wgid"],
                "result_mode": "first_value",
                "timeout": 5
            }
        },
        "problem_building_clusters": {
            "type": "array",
            "source": "sql",
            "description": "问题楼宇聚类信息",
            "required": False,
            "default": [],
            "dependencies": ["wgid"],
            "sql_config": {
                "connection": "microgrid_db",
                "query": "SELECT * FROM microgrid.micro_grid_problem_build_cluster_m WHERE wgid = :wgid",
                "parameters": ["wgid"],
                "result_mode": "all_rows",
                "timeout": 10
            }
        },
        "buildings_worse_competitor_count": {
            "type": "number",
            "source": "sql",
            "description": "劣于竞对楼宇数量",
            "required": False,
            "default": 0,
            "dependencies": ["wgid"],
            "sql_config": {
                "connection": "microgrid_db",
                "query": "SELECT COUNT(*) as count FROM microgrid.micro_grid_problem_build_m WHERE wgid = :wgid AND is_bad_other_build = true",
                "parameters": ["wgid"],
                "result_mode": "first_value",
                "timeout": 5
            }
        },
        "report_metadata": {
            "type": "object",
            "source": "system",
            "description": "报告元数据",
            "required": True,
            "system_config": {
                "fields": {
                    "version": {"value": "1.0.0"},
                    "report_id": {"generator": "uuid"},
                    "generated_date": {"generator": "datetime", "format": "%Y年%m月%d日"}
                }
            }
        },
        "report_generated_time": {
            "type": "string",
            "source": "system",
            "description": "报告生成时间",
            "required": True,
            "system_config": {
                "fields": {
                    "timestamp": {"generator": "datetime", "format": "%Y-%m-%d %H:%M:%S"}
                }
            }
        }
    }
    
    # 转换为VariableMetadata对象
    metadata = {k: VariableMetadata(**v) for k, v in metadata_json.items()}
    
    # 创建执行上下文
    context = ExecutionContext(
        task_id="test_full_task",
        template_id="tpl_21c2afbe565c",
        user_inputs=user_inputs,
        metadata=metadata
    )
    
    # 执行调度器
    scheduler = ExecutionScheduler()
    
    print("\n📋 开始执行所有变量...")
    try:
        results = await scheduler.execute_all(context)
        
        print("\n✅ 变量执行结果:")
        success_count = 0
        error_count = 0
        
        for var_name, result in results.items():
            if result.status.value == "success":
                success_count += 1
                print(f"  ✅ {var_name}: {result.status.value} ({result.duration_ms}ms)")
            else:
                error_count += 1
                print(f"  ❌ {var_name}: {result.status.value}")
                if result.error:
                    print(f"     错误: {result.error}")
        
        print(f"\n📊 统计: 成功 {success_count}, 失败 {error_count}")
        
        if error_count == 0:
            print("\n✅ 所有变量执行成功！报告可以正常生成。")
        else:
            print(f"\n⚠️  有 {error_count} 个变量执行失败，可能影响报告生成。")
            
        # 保存结果到文件
        with open('/data/tao/code/xuqiu/backend/test_result.json', 'w', encoding='utf-8') as f:
            result_data = {}
            for var_name, result in results.items():
                result_data[var_name] = {
                    "status": result.status.value,
                    "duration_ms": result.duration_ms,
                    "error": result.error
                }
            json.dump(result_data, f, ensure_ascii=False, indent=2)
        
        print("\n📄 详细结果已保存到: test_result.json")
        
    except Exception as e:
        print(f"\n❌ 执行失败: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_full_report())

