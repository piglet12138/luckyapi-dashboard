"""
验证同步完成情况
检查数据完整性、ID连续性、时间覆盖等
"""
import sys
import io
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.core.database import Database
from src.core.api_client import NewAPIClient
from src.core.config import BASE_URL, TOKEN, USER_ID
from datetime import datetime
import json

# 修复Windows控制台编码问题
if sys.platform == 'win32':
    try:
        if not isinstance(sys.stdout, io.TextIOWrapper) or sys.stdout.encoding != 'utf-8':
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        if not isinstance(sys.stderr, io.TextIOWrapper) or sys.stderr.encoding != 'utf-8':
            sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
    except Exception as e:
        print(f"Warning: Failed to set UTF-8 encoding for console: {e}", file=sys.stderr)


def check_id_gaps(db):
    """检查ID是否有缺失"""
    print("\n" + "="*70)
    print("检查ID连续性")
    print("="*70)
    
    # 获取ID范围
    cursor = db.execute("SELECT MIN(id) as min_id, MAX(id) as max_id, COUNT(*) as cnt FROM ods_logs")
    row = cursor.fetchone()
    min_id = row['min_id']
    max_id = row['max_id']
    count = row['cnt']
    
    print(f"ID范围: {min_id:,} ~ {max_id:,}")
    print(f"记录数: {count:,}")
    print(f"理论应有记录数: {max_id - min_id + 1:,}")
    
    # 检查缺失的ID（采样检查，因为全量检查太慢）
    print("\n采样检查ID缺失情况（检查前1000、中间1000、最后1000个ID）...")
    
    # 检查前1000个ID
    cursor = db.execute("""
        SELECT id FROM ods_logs 
        WHERE id BETWEEN ? AND ?
        ORDER BY id
    """, (min_id, min(min_id + 1000, max_id)))
    first_ids = {row['id'] for row in cursor.fetchall()}
    first_expected = set(range(min_id, min(min_id + 1000, max_id) + 1))
    first_missing = first_expected - first_ids
    print(f"  前1000个ID: 缺失 {len(first_missing)} 个")
    if first_missing and len(first_missing) <= 20:
        print(f"    缺失ID: {sorted(list(first_missing))}")
    
    # 检查中间1000个ID
    mid_start = (min_id + max_id) // 2 - 500
    mid_end = mid_start + 1000
    cursor = db.execute("""
        SELECT id FROM ods_logs 
        WHERE id BETWEEN ? AND ?
        ORDER BY id
    """, (mid_start, mid_end))
    mid_ids = {row['id'] for row in cursor.fetchall()}
    mid_expected = set(range(mid_start, mid_end + 1))
    mid_missing = mid_expected - mid_ids
    print(f"  中间1000个ID: 缺失 {len(mid_missing)} 个")
    if mid_missing and len(mid_missing) <= 20:
        print(f"    缺失ID: {sorted(list(mid_missing))}")
    
    # 检查最后1000个ID
    last_start = max(min_id, max_id - 1000)
    cursor = db.execute("""
        SELECT id FROM ods_logs 
        WHERE id BETWEEN ? AND ?
        ORDER BY id
    """, (last_start, max_id))
    last_ids = {row['id'] for row in cursor.fetchall()}
    last_expected = set(range(last_start, max_id + 1))
    last_missing = last_expected - last_ids
    print(f"  最后1000个ID: 缺失 {len(last_missing)} 个")
    if last_missing and len(last_missing) <= 20:
        print(f"    缺失ID: {sorted(list(last_missing))}")
    
    return len(first_missing) + len(mid_missing) + len(last_missing) == 0


def check_api_latest(db, api_client):
    """检查API返回的最新数据是否已同步"""
    print("\n" + "="*70)
    print("检查API最新数据")
    print("="*70)
    
    # 获取API第1页（最新数据）
    response = api_client.get_logs(page=1, page_size=100)
    if response.get('error'):
        print(f"❌ 无法获取API数据: {response.get('message')}")
        return False
    
    api_data = response.get('data', {})
    api_items = api_data.get('items', [])
    
    if not api_items:
        print("⚠️  API返回空数据")
        return False
    
    # 获取API中的最新ID和最新时间
    api_max_id = max(item['id'] for item in api_items)
    api_max_time = max(item['created_at'] for item in api_items)
    
    # 获取数据库中的最新ID和最新时间
    cursor = db.execute("SELECT MAX(id) as max_id, MAX(created_at) as max_time FROM ods_logs")
    row = cursor.fetchone()
    db_max_id = row['max_id']
    db_max_time = row['max_time']
    
    print(f"API最新ID: {api_max_id:,}")
    print(f"数据库最新ID: {db_max_id:,}")
    print(f"API最新时间: {datetime.fromtimestamp(api_max_time).strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"数据库最新时间: {datetime.fromtimestamp(db_max_time).strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 检查API中的最新记录是否在数据库中
    api_latest_ids = [item['id'] for item in api_items]
    placeholders = ','.join(['?' for _ in api_latest_ids])
    cursor = db.execute(f"SELECT id FROM ods_logs WHERE id IN ({placeholders})", api_latest_ids)
    found_ids = {row['id'] for row in cursor.fetchall()}
    missing_in_db = set(api_latest_ids) - found_ids
    
    if missing_in_db:
        print(f"\n⚠️  API最新数据中有 {len(missing_in_db)} 条未同步到数据库")
        print(f"    缺失ID: {sorted(list(missing_in_db))[:20]}")
        return False
    else:
        print(f"\n✅ API最新数据已全部同步到数据库")
        return True


def check_data_quality(db):
    """检查数据质量"""
    print("\n" + "="*70)
    print("检查数据质量")
    print("="*70)
    
    # 检查空值
    cursor = db.execute("""
        SELECT 
            COUNT(*) as total,
            SUM(CASE WHEN user_id IS NULL THEN 1 ELSE 0 END) as null_user_id,
            SUM(CASE WHEN created_at IS NULL THEN 1 ELSE 0 END) as null_created_at,
            SUM(CASE WHEN type IS NULL THEN 1 ELSE 0 END) as null_type,
            SUM(CASE WHEN content IS NULL OR content = '' THEN 1 ELSE 0 END) as empty_content
        FROM ods_logs
    """)
    stats_row = cursor.fetchone()
    total = stats_row['total']
    print(f"总记录数: {total:,}")
    print(f"  user_id为空: {stats_row['null_user_id']:,} ({stats_row['null_user_id']/total*100:.2f}%)")
    print(f"  created_at为空: {stats_row['null_created_at']:,}")
    print(f"  type为空: {stats_row['null_type']:,}")
    print(f"  content为空: {stats_row['empty_content']:,} ({stats_row['empty_content']/total*100:.2f}%)")
    
    # 检查时间分布
    cursor = db.execute("""
        SELECT 
            DATE(datetime(created_at, 'unixepoch')) as date,
            COUNT(*) as cnt
        FROM ods_logs
        GROUP BY DATE(datetime(created_at, 'unixepoch'))
        ORDER BY date DESC
        LIMIT 10
    """)
    print("\n最近10天数据分布:")
    for row in cursor.fetchall():
        print(f"  {row['date']}: {row['cnt']:,} 条")
    
    # 检查类型分布
    cursor = db.execute("""
        SELECT type, COUNT(*) as cnt
        FROM ods_logs
        GROUP BY type
        ORDER BY type
    """)
    type_map = {1: '充值', 2: '消费', 3: '管理', 4: '错误', 5: '系统'}
    print("\n类型分布:")
    for row in cursor.fetchall():
        type_name = type_map.get(row['type'], f"类型{row['type']}")
        print(f"  {type_name}: {row['cnt']:,} 条 ({row['cnt']/total*100:.2f}%)")


def main():
    print("="*70)
    print("同步完成情况验证")
    print("="*70)
    print(f"检查时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    db = Database()
    db.connect()
    
    try:
        # 1. 基本统计
        cursor = db.execute("SELECT COUNT(*) as cnt, MIN(id) as min_id, MAX(id) as max_id, MIN(created_at) as min_t, MAX(created_at) as max_t FROM ods_logs")
        row = cursor.fetchone()
        print(f"\n基本统计:")
        print(f"  记录数: {row['cnt']:,}")
        print(f"  ID范围: {row['min_id']:,} ~ {row['max_id']:,}")
        if row['min_t']:
            print(f"  时间范围: {datetime.fromtimestamp(row['min_t']).strftime('%Y-%m-%d %H:%M:%S')} ~ {datetime.fromtimestamp(row['max_t']).strftime('%Y-%m-%d %H:%M:%S')}")
        
        # 2. 检查ID连续性
        id_ok = check_id_gaps(db)
        
        # 3. 检查API最新数据
        api_client = NewAPIClient(BASE_URL, TOKEN)
        api_client.set_user_id(USER_ID)
        api_ok = check_api_latest(db, api_client)
        
        # 4. 检查数据质量
        check_data_quality(db)
        
        # 5. 总结
        print("\n" + "="*70)
        print("验证总结")
        print("="*70)
        if id_ok and api_ok:
            print("✅ 同步完成情况良好")
            print("  - ID连续性: 正常")
            print("  - API最新数据: 已同步")
        else:
            if not id_ok:
                print("⚠️  ID连续性检查发现问题（可能是正常的，因为API可能跳过了某些ID）")
            if not api_ok:
                print("⚠️  API最新数据未完全同步，可能需要再次运行同步")
        
    finally:
        db.close()


if __name__ == "__main__":
    main()
