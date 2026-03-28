"""
更好的同步策略
利用管理权限，使用时间范围分批获取，避免翻页限流
"""
import time
from datetime import datetime, timedelta
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.core.api_client import NewAPIClient
from src.core.database import Database
from src.core.config import BASE_URL, TOKEN, USER_ID, DB_PATH, SYNC_CONFIG


class BetterSyncStrategy:
    """优化的同步策略：按时间范围分批获取"""
    
    def __init__(self, db_path: str = None):
        if db_path is None:
            db_path = DB_PATH
        self.db = Database(db_path)
        self.db.connect()
        
        self.api_client = NewAPIClient(BASE_URL, TOKEN)
        self.api_client.set_user_id(USER_ID)
        
        # 优化配置（从config读取）
        self.batch_days = 7  # 每次获取7天的数据
        self.request_delay = SYNC_CONFIG["request_delay"]
        self.max_page_size = SYNC_CONFIG["max_page_size"]
        self.batch_rest_interval = SYNC_CONFIG["batch_rest_interval"]
        self.batch_rest_duration = SYNC_CONFIG["batch_rest_duration"]
    
    def sync_by_time_range(self):
        """
        按翻页方式全量同步（API时间范围查询不支持，改用翻页）
        从最后一页开始往前翻，确保获取所有历史数据
        """
        print("="*70)
        print("全量翻页同步（API时间范围查询不支持）")
        print("="*70)
        
        # 获取API数据的基本信息
        print("\n获取API数据的基本信息...")
        response = self.api_client.get_logs(page=1, page_size=1)
        if response.get('error'):
            print(f"错误: {response.get('message')}")
            return
        
        data = response.get('data', {})
        total = data.get('total', 0)
        
        print(f"API总记录数: {total:,}")
        
        # 检查数据库已有的记录数
        cursor = self.db.execute("SELECT COUNT(*) as cnt, MIN(id) as min_id, MAX(id) as max_id FROM ods_logs")
        row = cursor.fetchone()
        db_count = row['cnt'] or 0
        db_min_id = row['min_id']
        db_max_id = row['max_id']
        
        print(f"数据库已有记录数: {db_count:,}")
        if db_min_id:
            print(f"数据库ID范围: {db_min_id} ~ {db_max_id}")
        
        # 计算总页数（API实际每页只返回100条，不管请求多少）
        # 注意：API可能返回的页数比计算的多，需要动态检测
        actual_page_size = 100  # API实际限制
        calculated_pages = (total // actual_page_size) + 1
        print(f"计算的页数（基于实际page_size={actual_page_size}）: {calculated_pages:,}")
        
        # 计算同步时间估算
        estimated_time_per_page = self.request_delay + 0.1  # 请求延迟 + 处理时间
        rest_time = (calculated_pages // self.batch_rest_interval) * self.batch_rest_duration
        total_estimated_seconds = (calculated_pages * estimated_time_per_page) + rest_time
        total_estimated_hours = total_estimated_seconds / 3600
        print(f"估算同步时间: {total_estimated_hours:.2f} 小时（{total_estimated_seconds/60:.1f} 分钟）")
        print(f"  每页耗时: {estimated_time_per_page:.1f}秒")
        print(f"  每{self.batch_rest_interval}页休息: {self.batch_rest_duration}秒")
        
        # 动态检测实际的总页数：从计算的页数开始，逐步增加，直到找不到数据
        print(f"\n动态检测实际总页数...")
        actual_total_pages = calculated_pages
        # 先尝试更大的页数，看看是否有更多数据
        for test_page in [calculated_pages + 100, calculated_pages + 200, calculated_pages + 500]:
            test_r = self.api_client.get_logs(page=test_page, page_size=self.max_page_size)
            if not test_r.get('error'):
                test_items = test_r.get('data', {}).get('items', [])
                if test_items:
                    actual_total_pages = max(actual_total_pages, test_page)
                    min_id = min(i['id'] for i in test_items)
                    print(f"  第{test_page}页有数据，最小ID: {min_id}")
                    if min_id < 378903:
                        print(f"  ✓ 找到了ID < 378903的数据！")
                else:
                    break
            time.sleep(0.5)
        
        # 继续往前查找，直到找不到更小的ID
        print(f"\n继续查找更早的数据...")
        found_earlier = True
        current_page = actual_total_pages
        while found_earlier and current_page < calculated_pages + 1000:  # 最多查找1000页
            current_page += 50  # 每次增加50页
            test_r = self.api_client.get_logs(page=current_page, page_size=self.max_page_size)
            if not test_r.get('error'):
                test_items = test_r.get('data', {}).get('items', [])
                if test_items:
                    min_id = min(i['id'] for i in test_items)
                    if min_id < 378903:
                        actual_total_pages = current_page
                        print(f"  第{current_page}页，最小ID: {min_id} < 378903，继续查找...")
                    else:
                        found_earlier = False
                        print(f"  第{current_page}页，最小ID: {min_id} >= 378903，停止查找")
                        break
                else:
                    found_earlier = False
                    break
            else:
                # 如果遇到错误（如限流），停止查找
                break
            time.sleep(0.5)
        
        total_pages = actual_total_pages + 50  # 多查50页，确保不遗漏
        print(f"\n实际总页数: {total_pages}")
        
        # 确定起始页：从第1页开始往后读取，更稳定
        print(f"\n从第1页开始往后同步，确保获取所有历史数据...")
        
        # 检查数据库已有的最大ID，确定从哪一页开始（如果数据库已有数据）
        cursor = self.db.execute("SELECT MAX(id) as max_id FROM ods_logs")
        row = cursor.fetchone()
        db_max_id = row['max_id'] if row and row['max_id'] else None
        
        start_page = 1
        if db_max_id:
            # 估算：如果数据库最大ID是480129，那么应该从包含这个ID的页面之后开始
            # 但为了安全，还是从第1页开始，使用INSERT OR IGNORE自动跳过已存在的记录
            print(f"数据库最大ID: {db_max_id}，将从第1页开始同步（已存在记录会自动跳过）")
        
        total_synced = 0
        start_time = time.time()
        consecutive_empty_pages = 0
        consecutive_errors = 0
        max_consecutive_empty = 20  # 连续20页为空才停止（避免误判）
        max_consecutive_errors = 5  # 连续5次错误才停止
        retry_delay = 10  # 限流重试延迟
        
        # 从第1页开始往后读取
        for page in range(start_page, total_pages + 1):
            retry_count = 0
            max_retries = 3
            
            while retry_count < max_retries:
                response = self.api_client.get_logs(page=page, page_size=self.max_page_size)
                
                if response.get('error'):
                    error_msg = response.get('message', '')
                    status_code = response.get('status_code')
                    
                    if status_code == 429:
                        retry_count += 1
                        wait_time = retry_delay * retry_count  # 递增等待时间
                        print(f"  第{page}页: ⚠️ 限流（第{retry_count}次重试），等待{wait_time}秒...")
                        time.sleep(wait_time)
                        continue
                    else:
                        consecutive_errors += 1
                        if consecutive_errors >= max_consecutive_errors:
                            print(f"  第{page}页: 错误: {error_msg}")
                            print(f"  连续 {consecutive_errors} 次错误，停止同步")
                            break
                        else:
                            print(f"  第{page}页: 错误: {error_msg}，跳过（连续错误{consecutive_errors}/{max_consecutive_errors}）")
                            time.sleep(self.request_delay)
                            break
                else:
                    consecutive_errors = 0  # 重置错误计数器
                    break
            
            if response.get('error') and consecutive_errors >= max_consecutive_errors:
                break
            
            if response.get('error'):
                continue  # 跳过这次请求，继续下一页
            
            data = response.get('data', {})
            items = data.get('items', [])
            
            if not items:
                consecutive_empty_pages += 1
                if consecutive_empty_pages >= max_consecutive_empty:
                    print(f"  连续 {consecutive_empty_pages} 页为空，停止同步")
                    break
                # 即使为空也显示进度
                if consecutive_empty_pages % 5 == 0:
                    progress = (page / total_pages) * 100
                    print(f"  第{page}/{total_pages}页 ({progress:.1f}%): 空页（连续{consecutive_empty_pages}页）")
                continue
            
            consecutive_empty_pages = 0  # 重置空页计数器
            
            # 检查哪些记录已存在
            existing_ids = set()
            if items:
                placeholders = ','.join(['?' for _ in items])
                ids = [item['id'] for item in items]
                check_sql = f"SELECT id FROM ods_logs WHERE id IN ({placeholders})"
                cursor.execute(check_sql, ids)
                existing_ids = {row[0] for row in cursor.fetchall()}
            
            # 准备新记录
            new_items = [item for item in items if item['id'] not in existing_ids]
            
            if new_items:
                records = []
                for item in new_items:
                    record = {
                        'id': item['id'],
                        'user_id': item.get('user_id'),
                        'created_at': item.get('created_at'),
                        'type': item.get('type'),
                        'content': item.get('content', ''),
                        'username': item.get('username', ''),
                        'token_name': item.get('token_name', ''),
                        'model_name': item.get('model_name', ''),
                        'quota': item.get('quota', 0),
                        'prompt_tokens': item.get('prompt_tokens', 0),
                        'completion_tokens': item.get('completion_tokens', 0),
                        'use_time': item.get('use_time', 0),
                        'is_stream': bool(item.get('is_stream', False)),
                        'channel': item.get('channel', 0),
                        'channel_name': item.get('channel_name', ''),
                        'token_id': item.get('token_id', 0),
                        'group_name': item.get('group', ''),
                        'ip': item.get('ip', ''),
                        'request_id': item.get('request_id', ''),
                        'other': item.get('other', ''),
                    }
                    records.append(record)
                
                # 批量插入
                fields = list(records[0].keys())
                placeholders = ', '.join(['?' for _ in fields])
                fields_str = ', '.join(fields)
                sql = f"INSERT OR IGNORE INTO ods_logs ({fields_str}) VALUES ({placeholders})"
                
                values = [tuple(record.get(field) for field in fields) for record in records]
                cursor.executemany(sql, values)
                self.db.conn.commit()
                
                inserted = len(records)
                total_synced += inserted
                skipped = len(items) - inserted
                
                # 显示进度
                progress = (page / total_pages) * 100
                elapsed = time.time() - start_time
                rate = total_synced / elapsed if elapsed > 0 else 0
                
                if items:
                    earliest_item = min(items, key=lambda x: x['created_at'])
                    latest_item = max(items, key=lambda x: x['created_at'])
                    print(f"  第{page}/{total_pages}页 ({progress:.1f}%): 插入 {inserted} 条新记录（跳过 {skipped} 条）")
                    print(f"    ID范围: {min(i['id'] for i in items)} ~ {max(i['id'] for i in items)}")
                    print(f"    时间范围: {datetime.fromtimestamp(earliest_item['created_at'])} ~ {datetime.fromtimestamp(latest_item['created_at'])}")
                    print(f"    累计: {total_synced:,} 条，速度: {rate:.1f} 条/秒")
            else:
                # 全部已存在
                progress = (page / total_pages) * 100
                if page % 50 == 0:  # 每50页显示一次，避免输出过多
                    print(f"  第{page}/{total_pages}页 ({progress:.1f}%): 全部 {len(items)} 条已存在，跳过")
            
            # 每N页休息一次
            if page % self.batch_rest_interval == 0:
                elapsed = time.time() - start_time
                rate = total_synced / elapsed if elapsed > 0 else 0
                remaining_pages = total_pages - page
                progress = (page / total_pages) * 100
                if rate > 0:
                    estimated_remaining = (remaining_pages * estimated_time_per_page) / 3600
                    print(f"\n进度: {page}/{total_pages} 页 ({progress:.1f}%)，累计 {total_synced:,} 条")
                    print(f"耗时: {elapsed:.1f}秒（{elapsed/60:.1f}分钟），速度: {rate:.1f} 条/秒")
                    print(f"剩余: {remaining_pages:,} 页，预计还需: {estimated_remaining:.2f} 小时")
                    print(f"休息{self.batch_rest_duration}秒...\n")
                else:
                    print(f"\n进度: {page}/{total_pages} 页 ({progress:.1f}%)，累计 {total_synced:,} 条")
                    print(f"休息{self.batch_rest_duration}秒...\n")
                time.sleep(self.batch_rest_duration)
            else:
                time.sleep(self.request_delay)
        
        print(f"\n" + "="*70)
        print(f"全量翻页同步完成！")
        print(f"总同步: {total_synced:,} 条")
        print("="*70)
        
        return total_synced
    
    def _sync_time_range(self, start_time: int, end_time: int) -> int:
        """同步指定时间范围的数据"""
        page = 1
        total_synced = 0
        
        while True:
            response = self.api_client.get_logs(
                page=page,
                page_size=self.max_page_size,
                start_time=start_time,
                end_time=end_time
            )
            
            if response.get('error'):
                error_msg = response.get('message', '')
                status_code = response.get('status_code')
                
                if status_code == 429:
                    print(f"  ⚠️ 限流，等待10秒...")
                    time.sleep(10)
                    continue
                else:
                    print(f"  错误: {error_msg}")
                    break
            
            data = response.get('data', {})
            items = data.get('items', [])
            
            if not items:
                break
            
            # 检查哪些记录已存在
            cursor = self.db.conn.cursor()
            existing_ids = set()
            if items:
                placeholders = ','.join(['?' for _ in items])
                ids = [item['id'] for item in items]
                check_sql = f"SELECT id FROM ods_logs WHERE id IN ({placeholders})"
                cursor.execute(check_sql, ids)
                existing_ids = {row[0] for row in cursor.fetchall()}
            
            # 准备新记录
            new_items = [item for item in items if item['id'] not in existing_ids]
            
            if new_items:
                records = []
                for item in new_items:
                    record = {
                        'id': item['id'],
                        'user_id': item.get('user_id'),
                        'created_at': item.get('created_at'),
                        'type': item.get('type'),
                        'content': item.get('content', ''),
                        'username': item.get('username', ''),
                        'token_name': item.get('token_name', ''),
                        'model_name': item.get('model_name', ''),
                        'quota': item.get('quota', 0),
                        'prompt_tokens': item.get('prompt_tokens', 0),
                        'completion_tokens': item.get('completion_tokens', 0),
                        'use_time': item.get('use_time', 0),
                        'is_stream': bool(item.get('is_stream', False)),
                        'channel': item.get('channel', 0),
                        'channel_name': item.get('channel_name', ''),
                        'token_id': item.get('token_id', 0),
                        'group_name': item.get('group', ''),
                        'ip': item.get('ip', ''),
                        'request_id': item.get('request_id', ''),
                        'other': item.get('other', ''),
                    }
                    records.append(record)
                
                # 批量插入
                fields = list(records[0].keys())
                placeholders = ', '.join(['?' for _ in fields])
                fields_str = ', '.join(fields)
                sql = f"INSERT OR IGNORE INTO ods_logs ({fields_str}) VALUES ({placeholders})"
                
                values = [tuple(record.get(field) for field in fields) for record in records]
                cursor.executemany(sql, values)
                self.db.conn.commit()
                
                inserted = len(records)
                total_synced += inserted
                print(f"  第{page}页: 插入 {inserted} 条新记录")
            
            # 检查是否还有更多数据
            if len(items) < self.max_page_size:
                break
            
            page += 1
            time.sleep(self.request_delay)
        
        return total_synced
    
    def _sync_users(self):
        """同步用户数据（快照）"""
        try:
            page = 1
            all_users = []
            page_size = 100  # API实际每页返回100条
            
            # 先获取第1页，确定总页数
            response = self.api_client.get_users(page=1, page_size=page_size)
            if response.get('error'):
                print(f"❌ 获取用户数据失败: {response.get('message')}")
                return
            
            data = response.get('data', {})
            total = data.get('total', 0)
            actual_page_size = data.get('page_size', page_size)
            items = data.get('items', [])
            
            if not items:
                print("⚠️  用户数据为空")
                return
            
            all_users.extend(items)
            print(f"第1页: 获取 {len(items)} 条用户，API总记录数: {total}")
            
            # 计算总页数
            if total > 0:
                total_pages = (total + actual_page_size - 1) // actual_page_size
                print(f"预计总页数: {total_pages}")
                
                # 继续获取剩余页面
                for page in range(2, total_pages + 1):
                    response = self.api_client.get_users(page=page, page_size=page_size)
                    if response.get('error'):
                        print(f"⚠️  第{page}页获取失败: {response.get('message')}")
                        break
                    
                    data = response.get('data', {})
                    items = data.get('items', [])
                    if not items:
                        break
                    
                    all_users.extend(items)
                    print(f"第{page}页: 获取 {len(items)} 条用户，累计 {len(all_users)} 条")
                    time.sleep(0.5)  # 避免请求过快
            else:
                # 如果没有total字段，使用传统方式判断
                while True:
                    page += 1
                    response = self.api_client.get_users(page=page, page_size=page_size)
                    if response.get('error'):
                        break
                    
                    data = response.get('data', {})
                    items = data.get('items', [])
                    if not items:
                        break
                    
                    all_users.extend(items)
                    print(f"第{page}页: 获取 {len(items)} 条用户，累计 {len(all_users)} 条")
                    
                    if len(items) < page_size:
                        break
                    time.sleep(0.5)
            
            if all_users:
                records = []
                for item in all_users:
                    records.append({
                        'id': item.get('id'),
                        'username': item.get('username', ''),
                        'display_name': item.get('display_name', ''),
                        'role': item.get('role'),
                        'status': item.get('status'),
                        'email': item.get('email', ''),
                        'quota': item.get('quota', 0),
                        'used_quota': item.get('used_quota', 0),
                        'request_count': item.get('request_count', 0),
                        'group_name': item.get('group', ''),
                        'aff_code': item.get('aff_code', ''),
                        'aff_count': item.get('aff_count', 0),
                        'inviter_id': item.get('inviter_id'),
                    })
                
                cursor = self.db.conn.cursor()
                fields = list(records[0].keys())
                placeholders = ', '.join(['?' for _ in fields])
                fields_str = ', '.join(fields)
                sql = f"INSERT OR REPLACE INTO ods_users ({fields_str}) VALUES ({placeholders})"
                values = [tuple(r.get(f) for f in fields) for r in records]
                cursor.executemany(sql, values)
                self.db.conn.commit()
                print(f"✅ 同步用户数据完成: {len(records)} 条")
            else:
                print("⚠️  未获取到任何用户数据")
        except Exception as e:
            print(f"❌ 同步用户数据出错: {e}")
            import traceback
            traceback.print_exc()
    
    def _sync_channels(self):
        """同步渠道数据（快照）"""
        try:
            page = 1
            all_channels = []
            page_size = 100  # API实际每页返回100条
            
            # 先获取第1页，确定总页数
            response = self.api_client.get_channels(page=1, page_size=page_size)
            if response.get('error'):
                print(f"❌ 获取渠道数据失败: {response.get('message')}")
                return
            
            data = response.get('data', {})
            total = data.get('total', 0)
            actual_page_size = data.get('page_size', page_size)
            items = data.get('items', [])
            
            if not items:
                print("⚠️  渠道数据为空")
                return
            
            all_channels.extend(items)
            print(f"第1页: 获取 {len(items)} 条渠道，API总记录数: {total}")
            
            # 计算总页数
            if total > 0:
                total_pages = (total + actual_page_size - 1) // actual_page_size
                print(f"预计总页数: {total_pages}")
                
                # 继续获取剩余页面
                for page in range(2, total_pages + 1):
                    response = self.api_client.get_channels(page=page, page_size=page_size)
                    if response.get('error'):
                        print(f"⚠️  第{page}页获取失败: {response.get('message')}")
                        break
                    
                    data = response.get('data', {})
                    items = data.get('items', [])
                    if not items:
                        break
                    
                    all_channels.extend(items)
                    print(f"第{page}页: 获取 {len(items)} 条渠道，累计 {len(all_channels)} 条")
                    time.sleep(0.5)
            else:
                # 如果没有total字段，使用传统方式判断
                while True:
                    page += 1
                    response = self.api_client.get_channels(page=page, page_size=page_size)
                    if response.get('error'):
                        break
                    
                    data = response.get('data', {})
                    items = data.get('items', [])
                    if not items:
                        break
                    
                    all_channels.extend(items)
                    print(f"第{page}页: 获取 {len(items)} 条渠道，累计 {len(all_channels)} 条")
                    
                    if len(items) < page_size:
                        break
                    time.sleep(0.5)
            
            if all_channels:
                import json
                records = []
                for item in all_channels:
                    records.append({
                        'id': item.get('id'),
                        'name': item.get('name', ''),
                        'type': item.get('type'),
                        'status': item.get('status'),
                        'group_name': item.get('group', ''),
                        'weight': item.get('weight', 0),
                        'priority': item.get('priority', 0),
                        'balance': item.get('balance', 0),
                        'balance_updated_time': item.get('balance_updated_time', 0),
                        'models': json.dumps(item.get('models', '')) if isinstance(item.get('models'), (dict, list)) else str(item.get('models', '')),
                    })
                
                cursor = self.db.conn.cursor()
                fields = list(records[0].keys())
                placeholders = ', '.join(['?' for _ in fields])
                fields_str = ', '.join(fields)
                sql = f"INSERT OR REPLACE INTO ods_channels ({fields_str}) VALUES ({placeholders})"
                values = [tuple(r.get(f) for f in fields) for r in records]
                cursor.executemany(sql, values)
                self.db.conn.commit()
                print(f"✅ 同步渠道数据完成: {len(records)} 条")
            else:
                print("⚠️  未获取到任何渠道数据")
        except Exception as e:
            print(f"❌ 同步渠道数据出错: {e}")
            import traceback
            traceback.print_exc()
    
    def close(self):
        self.db.close()


if __name__ == "__main__":
    sync = BetterSyncStrategy()
    try:
        sync.sync_by_time_range()
    finally:
        sync.close()
