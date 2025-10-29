"""
清理异常任务数据脚本

用法:
    # 干运行模式（只检测，不删除）
    python cleanup_abnormal_tasks.py --dry-run
    
    # 实际执行清理
    python cleanup_abnormal_tasks.py
    
    # 清理指定天数之前的记录
    python cleanup_abnormal_tasks.py --days 7

功能:
    - 清理状态为 RUNNING 但任务已失败/完成的变量
    - 清理超过指定时间仍处于 RUNNING 状态的记录
    - 清理孤儿记录（任务已删除但变量/日志仍存在）
"""
import argparse
import sys
from datetime import datetime, timedelta
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from app.database import DATABASE_URL
from app.models.db_models import (
    GenerationTask, GenerationTaskVariable, ExecutionLog,
    VariableStatusType, ReportStatus
)
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def get_abnormal_running_variables(session, hours=24):
    """
    获取异常的 RUNNING 状态变量
    
    异常情况：
    1. 变量状态为 RUNNING 但任务已失败/取消/成功
    2. 创建时间超过指定小时数仍为 RUNNING
    """
    # 查询1：任务已结束但变量仍在 RUNNING
    query1 = session.query(GenerationTaskVariable).join(
        GenerationTask,
        GenerationTaskVariable.task_id == GenerationTask.id
    ).filter(
        GenerationTaskVariable.status == VariableStatusType.RUNNING,
        GenerationTask.status.in_([
            ReportStatus.SUCCESS,
            ReportStatus.FAILED,
            ReportStatus.CANCELLED
        ])
    )
    
    abnormal_vars_1 = query1.all()
    
    # 查询2：超时仍在 RUNNING
    cutoff_time = datetime.now() - timedelta(hours=hours)
    query2 = session.query(GenerationTaskVariable).filter(
        GenerationTaskVariable.status == VariableStatusType.RUNNING,
        GenerationTaskVariable.started_at < cutoff_time
    )
    
    abnormal_vars_2 = query2.all()
    
    # 合并并去重
    all_abnormal = {var.id: var for var in abnormal_vars_1 + abnormal_vars_2}
    
    return list(all_abnormal.values())


def get_orphan_records(session):
    """
    获取孤儿记录（任务已删除但关联记录仍存在）
    """
    orphan_vars = []
    orphan_logs = []
    
    # 查找没有对应任务的变量
    vars_without_task = session.query(GenerationTaskVariable).filter(
        ~GenerationTaskVariable.task_id.in_(
            session.query(GenerationTask.id)
        )
    ).all()
    orphan_vars.extend(vars_without_task)
    
    # 查找没有对应任务的日志
    logs_without_task = session.query(ExecutionLog).filter(
        ExecutionLog.task_id.isnot(None),
        ~ExecutionLog.task_id.in_(
            session.query(GenerationTask.id)
        )
    ).all()
    orphan_logs.extend(logs_without_task)
    
    return orphan_vars, orphan_logs


def cleanup_abnormal_data(dry_run=True, hours=24):
    """
    清理异常数据
    
    Args:
        dry_run: True=只检测不删除，False=实际删除
        hours: 判定超时的小时数
    """
    logger.info("=" * 60)
    logger.info(f"开始清理异常数据 - 模式: {'干运行' if dry_run else '实际执行'}")
    logger.info(f"超时阈值: {hours} 小时")
    logger.info("=" * 60)
    
    engine = create_engine(DATABASE_URL)
    Session = sessionmaker(bind=engine)
    session = Session()
    
    try:
        # 1. 检测异常 RUNNING 变量
        logger.info("\n步骤 1: 检测异常 RUNNING 状态的变量...")
        abnormal_vars = get_abnormal_running_variables(session, hours)
        
        if abnormal_vars:
            logger.warning(f"发现 {len(abnormal_vars)} 个异常变量:")
            for var in abnormal_vars[:10]:  # 只显示前10个
                logger.warning(
                    f"  - task_id={var.task_id}, "
                    f"variable={var.variable_name}, "
                    f"status={var.status.value}, "
                    f"started_at={var.started_at}"
                )
            if len(abnormal_vars) > 10:
                logger.warning(f"  ... 还有 {len(abnormal_vars) - 10} 个")
            
            if not dry_run:
                # 更新状态为 FAILED
                for var in abnormal_vars:
                    var.status = VariableStatusType.FAILED
                    var.error_message = "自动清理：任务异常终止或超时"
                    var.finished_at = datetime.now()
                    if var.started_at:
                        duration = (datetime.now() - var.started_at).total_seconds() * 1000
                        var.duration_ms = int(duration)
                session.commit()
                logger.info(f"✓ 已更新 {len(abnormal_vars)} 个变量状态为 FAILED")
        else:
            logger.info("✓ 未发现异常 RUNNING 变量")
        
        # 2. 检测孤儿记录
        logger.info("\n步骤 2: 检测孤儿记录...")
        orphan_vars, orphan_logs = get_orphan_records(session)
        
        if orphan_vars:
            logger.warning(f"发现 {len(orphan_vars)} 个孤儿变量记录:")
            for var in orphan_vars[:5]:
                logger.warning(f"  - task_id={var.task_id}, variable={var.variable_name}")
            if len(orphan_vars) > 5:
                logger.warning(f"  ... 还有 {len(orphan_vars) - 5} 个")
            
            if not dry_run:
                for var in orphan_vars:
                    session.delete(var)
                session.commit()
                logger.info(f"✓ 已删除 {len(orphan_vars)} 个孤儿变量记录")
        else:
            logger.info("✓ 未发现孤儿变量记录")
        
        if orphan_logs:
            logger.warning(f"发现 {len(orphan_logs)} 个孤儿日志记录")
            
            if not dry_run:
                for log in orphan_logs:
                    session.delete(log)
                session.commit()
                logger.info(f"✓ 已删除 {len(orphan_logs)} 个孤儿日志记录")
        else:
            logger.info("✓ 未发现孤儿日志记录")
        
        # 3. 统计总结
        logger.info("\n" + "=" * 60)
        logger.info("清理总结:")
        logger.info(f"  异常变量: {len(abnormal_vars)}")
        logger.info(f"  孤儿变量记录: {len(orphan_vars)}")
        logger.info(f"  孤儿日志记录: {len(orphan_logs)}")
        
        if dry_run:
            logger.info("\n这是干运行模式，未实际修改数据")
            logger.info("运行 'python cleanup_abnormal_tasks.py' 执行实际清理")
        else:
            logger.info("\n✓ 清理完成")
        
        logger.info("=" * 60)
        
        return {
            'abnormal_vars': len(abnormal_vars),
            'orphan_vars': len(orphan_vars),
            'orphan_logs': len(orphan_logs)
        }
        
    except Exception as e:
        logger.error(f"清理过程出错: {e}")
        session.rollback()
        raise
    finally:
        session.close()


def main():
    parser = argparse.ArgumentParser(description='清理异常任务数据')
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

