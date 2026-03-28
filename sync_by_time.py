#!/usr/bin/env python3
"""按时间范围同步数据"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.core.api_client import NewAPIClient
from src.core.database import Database
from src.core.config import BASE_URL, TOKEN, USER_ID
from datetime import datetime
import time

def sync_by_time(start_time_str, end_time_str):
    """按时间范围同步"""
    start_dt = datetime.strptime(start_time_str, "%Y-%m-%d %H:%M:%S")
    end_dt = datetime.strptime(end_time_str, "%Y-%m-%d %H:%M:%S")
    start_ts = int(start_dt.timestamp())
    end_ts = int(end_dt.timestamp())

    print(f"同步时间范围: {start_time_str} ~ {end_time_str}")

    db = Database("newapi_warehouse.db")
    db.connect()

    api = NewAPIClient(BASE_URL, TOKEN)
    api.set_user_id(USER_ID)

    total = 0
    page = 1

    while True:
        response = api.get_logs(page=page, page_size=100,
                               start_time=start_ts, end_time=end_ts)
        if response.get('error'):
            print(f"错误: {response.get('message')}")
            break

        items = response.get('data', {}).get('items', [])
        if not items:
            break

        # 插入数据
        for item in items:
            db.execute("""
                INSERT OR REPLACE INTO ods_logs (
                    id, user_id, created_at, type, content, username,
                    token_name, model_name, quota, prompt_tokens,
                    completion_tokens, use_time, is_stream
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, [
                item['id'], item.get('user_id'), item.get('created_at'),
                item.get('type'), item.get('content', ''), item.get('username', ''),
                item.get('token_name', ''), item.get('model_name', ''),
                item.get('quota', 0), item.get('prompt_tokens', 0),
                item.get('completion_tokens', 0), item.get('use_time', 0),
                bool(item.get('is_stream', False))
            ])

        db.conn.commit()
        total += len(items)
        print(f"第{page}页: {len(items)}条，累计{total}条")

        page += 1
        time.sleep(0.5)

    db.close()
    print(f"✓ 完成，共同步 {total} 条")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("用法: python3 sync_by_time.py '2026-03-26 18:00:00' '2026-03-27 00:00:00'")
        sys.exit(1)

    sync_by_time(sys.argv[1], sys.argv[2])
