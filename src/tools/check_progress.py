"""
检查同步进度脚本
实时查看全量同步的进度
支持自动刷新模式
"""
import sys
import time
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.core.database import Database
from datetime import datetime


def check_progress(refresh=False, interval=5):
    """检查同步进度"""
    db = Database()
    db.connect()
    
    print("="*70)
    print("同步进度检查")
    print("="*70)
    print(f"检查时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # 检查日志数据
    cursor = db.execute("SELECT COUNT(*) as cnt FROM ods_logs")
    log_count = cursor.fetchone()['cnt']
    print(f"日志记录数: {log_count:,} 条")
    
    # 检查最大ID和最小ID
    cursor = db.execute("SELECT MIN(id) as min_id, MAX(id) as max_id FROM ods_logs")
    row = cursor.fetchone()
    if row['min_id']:
        print(f"ID范围: {row['min_id']:,} ~ {row['max_id']:,}")
    
    # 检查时间范围
    cursor = db.execute("SELECT MIN(created_at) as min_t, MAX(created_at) as max_t FROM ods_logs")
    row = cursor.fetchone()
    if row['min_t']:
        min_dt = datetime.fromtimestamp(row['min_t'])
        max_dt = datetime.fromtimestamp(row['max_t'])
        print(f"时间范围: {min_dt.strftime('%Y-%m-%d %H:%M:%S')} ~ {max_dt.strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 按类型统计
    cursor = db.execute("""
        SELECT type, COUNT(*) as cnt 
        FROM ods_logs 
        GROUP BY type
        ORDER BY type
    """)
    print("\n按类型统计:")
    type_map = {1: '充值', 2: '消费', 3: '管理', 4: '错误', 5: '系统'}
    for row in cursor.fetchall():
        type_name = type_map.get(row['type'], f"类型{row['type']}")
        print(f"  {type_name}: {row['cnt']:,} 条")
    
    # 检查用户数据
    cursor = db.execute("SELECT COUNT(DISTINCT id) as cnt FROM ods_users")
    user_count = cursor.fetchone()['cnt']
    print(f"\n用户数量: {user_count:,} 个")
    
    # 检查渠道数据
    cursor = db.execute("SELECT COUNT(DISTINCT id) as cnt FROM ods_channels")
    channel_count = cursor.fetchone()['cnt']
    print(f"渠道数量: {channel_count:,} 个")
    
    # 检查同步记录
    cursor = db.execute("SELECT * FROM sync_records WHERE table_name = 'ods_logs'")
    sync_info = cursor.fetchone()
    if sync_info:
        print(f"\n同步记录:")
        print(f"  最后同步时间: {sync_info['last_sync_time']}")
        print(f"  最大created_at: {sync_info['last_max_created_at']}")
        print(f"  总记录数: {sync_info['total_records']:,}")
    
    # 估算进度（如果知道总数据量）
    # API返回的总数据量约为477,483条
    total_expected = 477483
    if log_count > 0:
        progress = (log_count / total_expected) * 100
        print(f"\n估算进度: {progress:.2f}% ({log_count:,} / {total_expected:,})")
        
        # 估算剩余时间（基于当前速度，假设67条/秒）
        if log_count < total_expected:
            remaining = total_expected - log_count
            estimated_seconds = remaining / 67
            estimated_minutes = estimated_seconds / 60
            print(f"预计剩余时间: {estimated_minutes:.1f} 分钟")
    
    print("\n" + "="*70)
    
    db.close()
    
    return log_count, user_count, channel_count


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='检查同步进度')
    parser.add_argument('-r', '--refresh', action='store_true', help='自动刷新模式')
    parser.add_argument('-i', '--interval', type=int, default=5, help='刷新间隔（秒），默认5秒')
    args = parser.parse_args()
    
    if args.refresh:
        print("="*70)
        print("实时监控模式（按Ctrl+C退出）")
        print("="*70)
        try:
            last_count = 0
            while True:
                # 清屏（Windows）
                import os
                os.system('cls' if os.name == 'nt' else 'clear')
                
                log_count, user_count, channel_count = check_progress()
                
                # 计算速度
                if last_count > 0:
                    diff = log_count - last_count
                    print(f"\n[速度] 本次刷新新增: {diff:,} 条")
                    if diff > 0:
                        rate_per_sec = diff / args.interval
                        print(f"[速度] 约 {rate_per_sec:.1f} 条/秒")
                
                last_count = log_count
                
                print(f"\n下次刷新: {args.interval}秒后... (按Ctrl+C退出)")
                time.sleep(args.interval)
        except KeyboardInterrupt:
            print("\n\n监控已停止")
    else:
        check_progress()
