#!/usr/bin/env python3
"""强制同步：忽略已存在检查，重新同步指定ID范围的数据"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.core.api_client import NewAPIClient
from src.core.database import Database
from src.core.config import BASE_URL, TOKEN, USER_ID
import time

def force_sync(start_id, end_id):
    """强制同步指定ID范围"""
    print(f"强制同步 ID {start_id} ~ {end_id}")

    db = Database("newapi_warehouse.db")
    db.connect()

    api = NewAPIClient(BASE_URL, TOKEN)
    api.set_user_id(USER_ID)

    # 计算需要多少页
    total = end_id - start_id + 1
    page_size = 100
    pages = (total + page_size - 1) // page_size

    synced = 0
    for page in range(1, pages + 1):
        response = api.get_logs(page=page, page_size=page_size)
        if response.get('error'):
            print(f"错误: {response.get('message')}")
            break

        items = response.get('data', {}).get('items', [])
        if not items:
            break

        # 筛选ID范围内的数据
        filtered = [item for item in items if start_id <= item['id'] <= end_id]

        if filtered:
            # 插入或替换
            for item in filtered:
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
            synced += len(filtered)
            print(f"  第{page}页: {len(filtered)}条")

        time.sleep(0.5)

    db.close()
    print(f"✓ 完成，共同步 {synced} 条")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("用法: python3 force_sync.py <start_id> <end_id>")
        print("示例: python3 force_sync.py 662968 681258")
        sys.exit(1)

    force_sync(int(sys.argv[1]), int(sys.argv[2]))
