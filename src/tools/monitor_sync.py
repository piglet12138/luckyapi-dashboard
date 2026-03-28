"""
实时监控同步进度
自动刷新显示最新进度
"""
import sys
import time
import os
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.core.database import Database
from datetime import datetime


def clear_screen():
    """清屏"""
    os.system('cls' if os.name == 'nt' else 'clear')


def check_progress():
    """检查进度并返回数据"""
    db = Database()
    db.connect()
    
    # 检查日志数据
    cursor = db.execute("SELECT COUNT(*) as cnt FROM ods_logs")
    log_count = cursor.fetchone()['cnt']
    
    # 检查最大ID和最小ID
    cursor = db.execute("SELECT MIN(id) as min_id, MAX(id) as max_id FROM ods_logs")
    row = cursor.fetchone()
    min_id = row['min_id'] if row['min_id'] else 0
    max_id = row['max_id'] if row['max_id'] else 0
    
    # 检查时间范围
    cursor = db.execute("SELECT MIN(created_at) as min_t, MAX(created_at) as max_t FROM ods_logs")
    row = cursor.fetchone()
    min_time = row['min_t']
    max_time = row['max_t']
    
    # 按类型统计
    cursor = db.execute("""
        SELECT type, COUNT(*) as cnt 
        FROM ods_logs 
        GROUP BY type
        ORDER BY type
    """)
    type_stats = {}
    type_map = {1: '充值', 2: '消费', 3: '管理', 4: '错误', 5: '系统'}
    for row in cursor.fetchall():
        type_stats[row['type']] = row['cnt']
    
    # 检查用户数据
    cursor = db.execute("SELECT COUNT(DISTINCT id) as cnt FROM ods_users")
    user_count = cursor.fetchone()['cnt']
    
    # 检查渠道数据
    cursor = db.execute("SELECT COUNT(DISTINCT id) as cnt FROM ods_channels")
    channel_count = cursor.fetchone()['cnt']
    
    db.close()
    
    return {
        'log_count': log_count,
        'min_id': min_id,
        'max_id': max_id,
        'min_time': min_time,
        'max_time': max_time,
        'type_stats': type_stats,
        'user_count': user_count,
        'channel_count': channel_count
    }


def format_time(timestamp):
    """格式化时间戳"""
    if not timestamp:
        return "N/A"
    return datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')


def display_progress(data, last_data=None):
    """显示进度信息"""
    print("="*70)
    print("实时同步进度监控")
    print("="*70)
    print(f"检查时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # 总记录数
    log_count = data['log_count']
    total_expected = 477483
    progress = (log_count / total_expected) * 100 if total_expected > 0 else 0
    
    print(f"日志记录数: {log_count:,} / {total_expected:,} ({progress:.2f}%)")
    
    # 进度条
    bar_width = 50
    filled = int(bar_width * progress / 100)
    bar = '█' * filled + '░' * (bar_width - filled)
    print(f"[{bar}] {progress:.2f}%")
    
    # 速度计算
    if last_data:
        time_diff = time.time() - last_data.get('check_time', time.time())
        count_diff = log_count - last_data.get('log_count', 0)
        if time_diff > 0 and count_diff > 0:
            rate = count_diff / time_diff
            print(f"\n[速度] 本次刷新: +{count_diff:,} 条 ({rate:.1f} 条/秒)")
            
            # 估算剩余时间
            remaining = total_expected - log_count
            if rate > 0:
                eta_seconds = remaining / rate
                eta_minutes = eta_seconds / 60
                print(f"[预计] 剩余时间: {eta_minutes:.1f} 分钟")
    
    print()
    
    # ID范围
    print(f"ID范围: {data['min_id']:,} ~ {data['max_id']:,}")
    
    # 时间范围
    print(f"时间范围: {format_time(data['min_time'])} ~ {format_time(data['max_time'])}")
    
    # 按类型统计
    print("\n按类型统计:")
    type_map = {1: '充值', 2: '消费', 3: '管理', 4: '错误', 5: '系统'}
    for type_id, count in sorted(data['type_stats'].items()):
        type_name = type_map.get(type_id, f"类型{type_id}")
        print(f"  {type_name}: {count:,} 条")
    
    # 用户和渠道
    print(f"\n用户数量: {data['user_count']:,} 个")
    print(f"渠道数量: {data['channel_count']:,} 个")
    
    print("\n" + "="*70)
    print("按Ctrl+C退出监控")


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='实时监控同步进度')
    parser.add_argument('-i', '--interval', type=int, default=5, 
                       help='刷新间隔（秒），默认5秒')
    args = parser.parse_args()
    
    print("="*70)
    print("实时监控模式")
    print(f"刷新间隔: {args.interval}秒")
    print("按Ctrl+C退出")
    print("="*70)
    time.sleep(2)
    
    last_data = None
    
    try:
        while True:
            clear_screen()
            
            data = check_progress()
            data['check_time'] = time.time()
            
            display_progress(data, last_data)
            
            last_data = data
            
            print(f"\n下次刷新: {args.interval}秒后...")
            time.sleep(args.interval)
            
    except KeyboardInterrupt:
        print("\n\n监控已停止")
        sys.exit(0)


if __name__ == "__main__":
    main()
