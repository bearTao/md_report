#!/usr/bin/env python3
"""
任务监控脚本 - 实时查看报告生成进度
"""
import requests
import time
import sys
from datetime import datetime

API_BASE = "http://localhost:8000"

def format_time(iso_time):
    """格式化时间"""
    if not iso_time:
        return "-"
    try:
        dt = datetime.fromisoformat(iso_time.replace('Z', '+00:00'))
        return dt.strftime('%H:%M:%S')
    except:
        return iso_time

def get_status_icon(status):
    """获取状态图标"""
    icons = {
        'pending': '⏸️ ',
        'running': '🔄',
        'success': '✅',
        'failed': '❌',
        'skipped': '⏭️ '
    }
    return icons.get(status, '  ')

def monitor_task(task_id, interval=2):
    """监控任务执行"""
    print(f"\n{'='*80}")
    print(f"监控任务: {task_id}")
    print(f"{'='*80}\n")
    
    last_status = None
    iteration = 0
    
    while True:
        try:
            iteration += 1
            response = requests.get(f"{API_BASE}/api/reports/tasks/{task_id}/status")
            
            if response.status_code != 200:
                print(f"❌ 获取任务状态失败: {response.status_code}")
                print(f"   {response.text}")
                break
            
            data = response.json()
            
            # 清屏（可选）
            # print("\033[2J\033[H")
            
            # 任务概要
            print(f"\n[{datetime.now().strftime('%H:%M:%S')}] 查询 #{iteration}")
            print(f"{'─'*80}")
            print(f"任务ID: {data['task_id']}")
            print(f"状态: {get_status_icon(data['status'])} {data['status'].upper()}")
            print(f"开始时间: {format_time(data.get('started_at'))}")
            
            if data.get('finished_at'):
                print(f"结束时间: {format_time(data['finished_at'])}")
            
            if data.get('report_id'):
                print(f"报告ID: {data['report_id']}")
                print(f"查看报告: http://localhost:5174/reports/{data['report_id']}")
            
            # 变量执行详情
            variables = data.get('variables', [])
            if variables:
                print(f"\n变量执行情况 ({len(variables)}个):")
                print(f"{'─'*80}")
                
                for var in variables:
                    icon = get_status_icon(var['status'])
                    duration = f"{var['duration_ms']}ms" if var.get('duration_ms') else "-"
                    
                    print(f"{icon} {var['variable_name']:<25} [{var['source']:<15}] {var['status']:<10} {duration}")
                    
                    if var.get('error_message'):
                        print(f"   ❌ 错误: {var['error_message']}")
                    
                    if var.get('result_preview'):
                        preview = str(var['result_preview']).get('preview', '')[:100]
                        if preview:
                            print(f"   📄 结果: {preview}...")
            
            # 检查是否完成
            if data['status'] in ['success', 'failed', 'cancelled']:
                print(f"\n{'='*80}")
                if data['status'] == 'success':
                    print(f"🎉 任务完成！")
                    if data.get('report_id'):
                        print(f"\n查看报告:")
                        print(f"  浏览器: http://localhost:5174/reports/{data['report_id']}")
                        print(f"  API: {API_BASE}/api/reports/{data['report_id']}")
                        print(f"  下载: {API_BASE}/api/reports/{data['report_id']}/download")
                elif data['status'] == 'failed':
                    print(f"❌ 任务失败")
                else:
                    print(f"⚠️  任务已取消")
                print(f"{'='*80}")
                break
            
            # 等待下次轮询
            time.sleep(interval)
            
        except KeyboardInterrupt:
            print(f"\n\n⚠️  监控已停止")
            break
        except Exception as e:
            print(f"\n❌ 错误: {e}")
            time.sleep(interval)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python monitor_task.py <task_id> [interval]")
        print("示例: python monitor_task.py task_abc123 2")
        sys.exit(1)
    
    task_id = sys.argv[1]
    interval = int(sys.argv[2]) if len(sys.argv) > 2 else 2
    
    try:
        monitor_task(task_id, interval)
    except Exception as e:
        print(f"❌ 监控失败: {e}")
        sys.exit(1)

