#!/usr/bin/env python3
"""补数据脚本：重新计算指定日期的DWD/ADS数据"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.core.database import Database
from export_dashboard_data import DashboardDataExporter

def backfill(date_str):
    """重新计算指定日期的数据"""
    print(f"开始补数据: {date_str}")

    db = Database("newapi_warehouse.db")
    db.connect()

    # 1. 重新计算DWD（从ODS）
    print(f"重新计算 {date_str} 的DWD数据...")
    db.execute("DELETE FROM dwd_logs WHERE log_date = ?", [date_str])
    cursor = db.execute("""
        INSERT INTO dwd_logs (
            log_id, user_id, log_date, log_datetime, log_type, model_name,
            prompt_tokens, completion_tokens, topup_amount, quota
        )
        SELECT
            id, user_id,
            DATE(datetime(created_at, 'unixepoch')),
            datetime(created_at, 'unixepoch'),
            type, model_name,
            prompt_tokens, completion_tokens,
            CASE WHEN type = 1 THEN quota ELSE 0 END,
            quota
        FROM ods_logs
        WHERE DATE(datetime(created_at, 'unixepoch')) = ?
    """, [date_str])
    db.conn.commit()
    print(f"  DWD: {cursor.rowcount} 条")

    # 2. 重新计算ADS（从DWD）
    print(f"重新计算 {date_str} 的ADS数据...")
    db.execute("DELETE FROM ads_funnel_daily WHERE stat_date = ?", [date_str])
    db.execute("""
        INSERT INTO ads_funnel_daily (
            stat_date, active_users, new_users, activated_new_users, d3_retention_rate
        )
        SELECT
            ? as stat_date,
            COUNT(DISTINCT user_id) as active_users,
            (SELECT COUNT(DISTINCT user_id) FROM (
                SELECT user_id, MIN(log_date) as first_date FROM dwd_logs GROUP BY user_id
            ) WHERE first_date = ?) as new_users,
            0 as activated_new_users,
            0 as d3_retention_rate
        FROM dwd_logs
        WHERE log_date = ?
    """, [date_str, date_str, date_str])
    db.conn.commit()
    print(f"  ADS: 完成")

    db.close()

    # 3. 重新导出看板数据
    print("重新导出看板数据...")
    exporter = DashboardDataExporter()
    exporter.connect()
    exporter.export_all()
    exporter.close()

    print(f"✓ {date_str} 数据补齐完成")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python3 backfill_data.py 2026-03-27")
        sys.exit(1)

    backfill(sys.argv[1])
