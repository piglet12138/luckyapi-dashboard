"""
增量同步脚本
只获取自上次同步以来的新数据
用于每日定时更新
"""
import sys
import os
import time
from datetime import datetime, timedelta

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.core.api_client import NewAPIClient
from src.core.database import Database
from src.core.config import BASE_URL, TOKEN, USER_ID, DB_PATH, SYNC_CONFIG


class IncrementalSync:
    """增量同步：只获取新数据"""

    def __init__(self, db_path: str = None):
        if db_path is None:
            db_path = DB_PATH
        self.db = Database(db_path)
        self.db.connect()

        self.api_client = NewAPIClient(BASE_URL, TOKEN)
        self.api_client.set_user_id(USER_ID)

        # 配置
        self.request_delay = SYNC_CONFIG.get("request_delay", 0.5)
        self.max_page_size = SYNC_CONFIG.get("max_page_size", 100)
        self.max_retries = 3
        self.retry_delay = 10

    def sync_new_logs(self) -> int:
        """
        增量同步日志数据
        只获取数据库中不存在的新日志
        """
        print("="*70)
        print("增量同步日志数据")
        print("="*70)

        # 1. 检查数据库最新记录
        cursor = self.db.execute("""
            SELECT MAX(id) as max_id, MAX(created_at) as max_time
            FROM ods_logs
        """)
        row = cursor.fetchone()
        db_max_id = row['max_id'] if row and row['max_id'] else 0
        db_max_time = row['max_time'] if row and row['max_time'] else 0

        if db_max_id:
            db_max_datetime = datetime.fromtimestamp(db_max_time)
            print(f"数据库最新记录: ID={db_max_id}, 时间={db_max_datetime}")
        else:
            print("数据库为空，将执行首次同步")

        # 2. 获取API最新数据（第1页）
        print("\n检查API是否有新数据...")
        response = self.api_client.get_logs(page=1, page_size=10)
        if response.get('error'):
            print(f"错误: {response.get('message')}")
            return 0

        data = response.get('data', {})
        items = data.get('items', [])

        if not items:
            print("API无数据")
            return 0

        # API最新记录
        api_max_id = max(item['id'] for item in items)
        api_max_time = max(item['created_at'] for item in items)
        api_max_datetime = datetime.fromtimestamp(api_max_time)

        print(f"API最新记录: ID={api_max_id}, 时间={api_max_datetime}")

        # 3. 判断是否需要同步
        if db_max_id >= api_max_id:
            print("\n数据已是最新，无需同步")
            return 0

        print(f"\n发现新数据: {api_max_id - db_max_id} 条新记录（估算）")

        # 4. 增量获取新数据
        # 策略：从第1页开始获取，直到ID <= db_max_id
        total_synced = 0
        page = 1

        print("\n开始增量同步...")
        start_time = time.time()

        while True:
            # 获取当前页数据
            retry_count = 0
            while retry_count < self.max_retries:
                response = self.api_client.get_logs(page=page, page_size=self.max_page_size)

                if response.get('error'):
                    status_code = response.get('status_code')
                    if status_code == 429:
                        retry_count += 1
                        wait_time = self.retry_delay * retry_count
                        print(f"  第{page}页: 限流，等待{wait_time}秒...")
                        time.sleep(wait_time)
                        continue
                    else:
                        print(f"  第{page}页: 错误: {response.get('message')}")
                        return total_synced
                else:
                    break

            if response.get('error'):
                break

            data = response.get('data', {})
            items = data.get('items', [])

            if not items:
                print(f"  第{page}页: 无数据，停止同步")
                break

            # 检查哪些记录已存在
            item_ids = [item['id'] for item in items]
            placeholders = ','.join(['?' for _ in item_ids])
            check_sql = f"SELECT id FROM ods_logs WHERE id IN ({placeholders})"
            cursor = self.db.execute(check_sql, item_ids)
            existing_ids = {row[0] for row in cursor.fetchall()}

            # 筛选新记录
            new_items = [item for item in items if item['id'] not in existing_ids]

            # 检查是否已到达数据库最大ID
            min_id_in_page = min(item['id'] for item in items)
            if min_id_in_page <= db_max_id:
                # 只保留ID > db_max_id的记录
                new_items = [item for item in new_items if item['id'] > db_max_id]
                if new_items:
                    print(f"  第{page}页: 新增{len(new_items)}条，已到达数据库边界")
                else:
                    print(f"  第{page}页: 已到达数据库边界，停止同步")
                    break

            # 插入新记录
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
            cursor = self.db.conn.cursor()
            cursor.executemany(sql, values)
            self.db.conn.commit()

            inserted = len(records)
            total_synced += inserted
            skipped = len(items) - inserted

            # 显示进度
            min_id = min(item['id'] for item in items)
            max_id = max(item['id'] for item in items)
            min_time = datetime.fromtimestamp(min(item['created_at'] for item in items))
            max_time = datetime.fromtimestamp(max(item['created_at'] for item in items))

            print(f"  第{page}页: 新增{inserted}条，跳过{skipped}条")
            print(f"    ID范围: {min_id} ~ {max_id}")
            print(f"    时间: {min_time} ~ {max_time}")

            # 如果已到达边界，停止
            if min_id <= db_max_id:
                break

            page += 1
            time.sleep(self.request_delay)

        elapsed = time.time() - start_time
        print(f"\n日志增量同步完成: 新增 {total_synced} 条，耗时 {elapsed:.1f}秒")

        return total_synced

    def sync_users(self) -> int:
        """同步用户数据（全量快照）"""
        print("\n" + "="*70)
        print("同步用户数据")
        print("="*70)

        try:
            page = 1
            all_users = []
            page_size = 100

            # 获取第1页
            response = self.api_client.get_users(page=1, page_size=page_size)
            if response.get('error'):
                print(f"错误: {response.get('message')}")
                return 0

            data = response.get('data', {})
            total = data.get('total', 0)
            items = data.get('items', [])

            if not items:
                print("无用户数据")
                return 0

            all_users.extend(items)
            print(f"第1页: 获取 {len(items)} 条，总数: {total}")

            # 获取剩余页面
            if total > 0:
                total_pages = (total + page_size - 1) // page_size
                for page in range(2, total_pages + 1):
                    response = self.api_client.get_users(page=page, page_size=page_size)
                    if response.get('error'):
                        print(f"第{page}页错误: {response.get('message')}")
                        break

                    data = response.get('data', {})
                    items = data.get('items', [])
                    if not items:
                        break

                    all_users.extend(items)
                    if page % 10 == 0:
                        print(f"第{page}页: 累计 {len(all_users)} 条")
                    time.sleep(0.3)

            # 批量插入/更新
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

                print(f"用户数据同步完成: {len(records)} 条")
                return len(records)
            else:
                print("未获取到用户数据")
                return 0

        except Exception as e:
            print(f"用户数据同步出错: {e}")
            import traceback
            traceback.print_exc()
            return 0

    def sync_channels(self) -> int:
        """同步渠道数据（全量快照）"""
        print("\n" + "="*70)
        print("同步渠道数据")
        print("="*70)

        try:
            page = 1
            all_channels = []
            page_size = 100

            # 获取第1页
            response = self.api_client.get_channels(page=1, page_size=page_size)
            if response.get('error'):
                print(f"错误: {response.get('message')}")
                return 0

            data = response.get('data', {})
            total = data.get('total', 0)
            items = data.get('items', [])

            if not items:
                print("无渠道数据")
                return 0

            all_channels.extend(items)
            print(f"第1页: 获取 {len(items)} 条，总数: {total}")

            # 获取剩余页面
            if total > 0:
                total_pages = (total + page_size - 1) // page_size
                for page in range(2, total_pages + 1):
                    response = self.api_client.get_channels(page=page, page_size=page_size)
                    if response.get('error'):
                        print(f"第{page}页错误: {response.get('message')}")
                        break

                    data = response.get('data', {})
                    items = data.get('items', [])
                    if not items:
                        break

                    all_channels.extend(items)
                    if page % 5 == 0:
                        print(f"第{page}页: 累计 {len(all_channels)} 条")
                    time.sleep(0.3)

            # 批量插入/更新
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

                print(f"渠道数据同步完成: {len(records)} 条")
                return len(records)
            else:
                print("未获取到渠道数据")
                return 0

        except Exception as e:
            print(f"渠道数据同步出错: {e}")
            import traceback
            traceback.print_exc()
            return 0

    def sync_all(self):
        """执行完整的增量同步"""
        start_time = time.time()

        print("="*70)
        print("开始增量同步")
        print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*70)

        # 1. 增量同步日志
        logs_count = self.sync_new_logs()

        # 2. 全量同步用户（快照）
        users_count = self.sync_users()

        # 3. 全量同步渠道（快照）
        channels_count = self.sync_channels()

        # 完成
        elapsed = time.time() - start_time
        print("\n" + "="*70)
        print("增量同步完成")
        print("="*70)
        print(f"新增日志: {logs_count} 条")
        print(f"同步用户: {users_count} 条")
        print(f"同步渠道: {channels_count} 条")
        print(f"总耗时: {elapsed:.1f}秒")
        print("="*70)

        return {
            'logs': logs_count,
            'users': users_count,
            'channels': channels_count,
            'duration': elapsed
        }

    def close(self):
        """关闭数据库连接"""
        self.db.close()


if __name__ == "__main__":
    sync = IncrementalSync()
    try:
        sync.sync_all()
    finally:
        sync.close()
