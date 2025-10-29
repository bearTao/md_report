"""
使用原生 SQL 清理异常任务数据（避免 ORM 枚举问题）

用法:
    # 干运行模式（只检测，不删除）
    python cleanup_abnormal_tasks_sql.py --dry-run
    
    # 实际执行清理
    python cleanup_abnormal_tasks_sql.py
"""
import argparse
import sys
from datetime import datetime, timedelta
from sqlalchemy import create_engine, text
from app.database import DATABASE_URL
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def cleanup_abnormal_data(dry_run=True, hours=24):
    """
    使用原生 SQL 清理异常数据
    
    Args:
        dry_run: True=只检测不删除，False=实际删除
        hours: 判定超时的小时数
    """
    logger.info("=" * 60)
    logger.info(f"开始清理异常数据 - 模式: {'干运行' if dry_run else '实际执行'}")
    logger.info(f"超时阈值: {hours} 小时")
    logger.info("=" * 60)
    
    engine = create_engine(DATABASE_URL)
    
    stats = {
        'abnormal_vars': 0,
        'orphan_vars': 0,
        'orphan_logs': 0
    }
    
    with engine.begin() as conn:
        try:
            # 1. 检测异常 RUNNING 变量（任务已结束但变量仍在 RUNNING）
            logger.info("\n步骤 1: 检测异常 RUNNING 状态的变量...")
            
            check_sql = text("""
                SELECT 
                    v.id, v.task_id, v.variable_name, v.source, v.status, v.started_at,
                    t.status as task_status
                FROM generation_task_variables v
                JOIN generation_tasks t ON v.task_id = t.id
                WHERE v.status = 'RUNNING'
                AND t.status IN ('SUCCESS', 'FAILED', 'CANCELLED')
            """)
            
            abnormal_vars_1 = conn.execute(check_sql).fetchall()
            
            # 检测超时的 RUNNING 变量
            cutoff_time = datetime.now() - timedelta(hours=hours)
            check_sql_2 = text("""
                SELECT 
                    v.id, v.task_id, v.variable_name, v.source, v.status, v.started_at
                FROM generation_task_variables v
                WHERE v.status = 'RUNNING'
                AND v.started_at < :cutoff_time
            """)
            
            abnormal_vars_2 = conn.execute(
                check_sql_2,
                {"cutoff_time": cutoff_time}
            ).fetchall()
            
            # 合并结果（去重）
            abnormal_var_ids = set()
            abnormal_vars = []
            for var in list(abnormal_vars_1) + list(abnormal_vars_2):
                if var[0] not in abnormal_var_ids:
                    abnormal_var_ids.add(var[0])
                    abnormal_vars.append(var)
            
            stats['abnormal_vars'] = len(abnormal_vars)
            
            if abnormal_vars:
                logger.warning(f"发现 {len(abnormal_vars)} 个异常变量:")
                for var in abnormal_vars[:10]:
                    logger.warning(
                        f"  - id={var[0]}, task_id={var[1]}, "
                        f"variable={var[2]}, status={var[4]}, "
                        f"started_at={var[5]}"
                    )
                if len(abnormal_vars) > 10:
                    logger.warning(f"  ... 还有 {len(abnormal_vars) - 10} 个")
                
                if not dry_run:
                    # 更新状态为 FAILED
                    update_sql = text("""
                        UPDATE generation_task_variables
                        SET status = 'FAILED',
                            error_message = '自动清理：任务异常终止或超时',
                            finished_at = NOW(),
                            duration_ms = TIMESTAMPDIFF(MICROSECOND, started_at, NOW()) / 1000
                        WHERE id IN :ids
                    """)
                    conn.execute(
                        update_sql,
                        {"ids": tuple(abnormal_var_ids)}
                    )
                    logger.info(f"✓ 已更新 {len(abnormal_vars)} 个变量状态为 FAILED")
            else:
                logger.info("✓ 未发现异常 RUNNING 变量")
            
            # 2. 检测孤儿变量记录
            logger.info("\n步骤 2: 检测孤儿记录...")
            
            orphan_vars_sql = text("""
                SELECT v.id, v.task_id, v.variable_name
                FROM generation_task_variables v
                LEFT JOIN generation_tasks t ON v.task_id = t.id
                WHERE t.id IS NULL
            """)
            
            orphan_vars = conn.execute(orphan_vars_sql).fetchall()
            stats['orphan_vars'] = len(orphan_vars)
            
            if orphan_vars:
                logger.warning(f"发现 {len(orphan_vars)} 个孤儿变量记录:")
                for var in orphan_vars[:5]:
                    logger.warning(f"  - id={var[0]}, task_id={var[1]}, variable={var[2]}")
                if len(orphan_vars) > 5:
                    logger.warning(f"  ... 还有 {len(orphan_vars) - 5} 个")
                
                if not dry_run:
                    delete_vars_sql = text("""
                        DELETE v FROM generation_task_variables v
                        LEFT JOIN generation_tasks t ON v.task_id = t.id
                        WHERE t.id IS NULL
                    """)
                    result = conn.execute(delete_vars_sql)
                    logger.info(f"✓ 已删除 {result.rowcount} 个孤儿变量记录")
            else:
                logger.info("✓ 未发现孤儿变量记录")
            
            # 3. 检测孤儿日志记录
            orphan_logs_sql = text("""
                SELECT l.id, l.task_id
                FROM execution_logs l
                LEFT JOIN generation_tasks t ON l.task_id = t.id
                WHERE l.task_id IS NOT NULL AND t.id IS NULL
            """)
            
            orphan_logs = conn.execute(orphan_logs_sql).fetchall()
            stats['orphan_logs'] = len(orphan_logs)
            
            if orphan_logs:
                logger.warning(f"发现 {len(orphan_logs)} 个孤儿日志记录")
                
                if not dry_run:
                    delete_logs_sql = text("""
                        DELETE l FROM execution_logs l
                        LEFT JOIN generation_tasks t ON l.task_id = t.id
                        WHERE l.task_id IS NOT NULL AND t.id IS NULL
                    """)
                    result = conn.execute(delete_logs_sql)
                    logger.info(f"✓ 已删除 {result.rowcount} 个孤儿日志记录")
            else:
                logger.info("✓ 未发现孤儿日志记录")
            
            # 4. 统计总结
            logger.info("\n" + "=" * 60)
            logger.info("清理总结:")
            logger.info(f"  异常变量: {stats['abnormal_vars']}")
            logger.info(f"  孤儿变量记录: {stats['orphan_vars']}")
            logger.info(f"  孤儿日志记录: {stats['orphan_logs']}")
            
            if dry_run:
                logger.info("\n这是干运行模式，未实际修改数据")
                logger.info("运行 'python cleanup_abnormal_tasks_sql.py' 执行实际清理")
            else:
                logger.info("\n✓ 清理完成")
            
            logger.info("=" * 60)
            
            return stats
            
        except Exception as e:
            logger.error(f"清理过程出错: {e}")
            raise


def main():
    parser = argparse.ArgumentParser(description='清理异常任务数据（SQL版本）')
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='干运行模式（只检测，不删除）'
    )
    parser.add_argument(
        '--hours',
        type=int,
        default=24,
        help='判定超时的小时数（默认24小时）'
    )
    
    args = parser.parse_args()
    
    try:
        result = cleanup_abnormal_data(
            dry_run=args.dry_run,
            hours=args.hours
        )
        
        # 如果发现异常数据且是干运行模式，返回非零退出码
        if args.dry_run and sum(result.values()) > 0:
            sys.exit(1)
        
        sys.exit(0)
        
    except Exception as e:
        logger.error(f"执行失败: {e}")
        sys.exit(2)


if __name__ == "__main__":
    main()

