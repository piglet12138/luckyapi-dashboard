#!/usr/bin/env python3
"""
数据修复脚本 - 检查并补齐各层缺失数据
解耦设计：分别检查ODS->DWD、DWD->ADS的缺失，针对性修复
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import sqlite3
from datetime import datetime, timedelta

class DataRepairer:
    """数据修复器"""

    def __init__(self, db_path="newapi_warehouse.db"):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row

    def check_ods_to_dwd_gaps(self):
        """检查ODS->DWD的缺失"""
        print("\n=== 检查 ODS -> DWD 缺失 ===")

        cursor = self.conn.execute("""
            SELECT COUNT(*) as missing_count
            FROM ods_logs o
            WHERE NOT EXISTS (
                SELECT 1 FROM dwd_logs d WHERE d.log_id = o.id
            )
        """)
        missing = cursor.fetchone()['missing_count']

        if missing > 0:
            print(f"发现 {missing} 条ODS记录未转换到DWD")

            # 按日期统计
            cursor = self.conn.execute("""
                SELECT
                    DATE(datetime(o.created_at, 'unixepoch')) as date,
                    COUNT(*) as count
                FROM ods_logs o
                WHERE NOT EXISTS (
                    SELECT 1 FROM dwd_logs d WHERE d.log_id = o.id
                )
                GROUP BY date
                ORDER BY date
            """)

            print("缺失明细:")
            for row in cursor.fetchall():
                print(f"  {row['date']}: {row['count']}条")

            return True
        else:
            print("✓ ODS->DWD 无缺失")
            return False

    def repair_ods_to_dwd(self):
        """修复ODS->DWD缺失"""
        print("\n=== 修复 ODS -> DWD ===")

        self.conn.execute("""
            INSERT OR IGNORE INTO dwd_logs (
                log_id, user_id, log_date, log_datetime, log_type,
                model_name, prompt_tokens, completion_tokens, topup_amount, quota
            )
            SELECT
                id, user_id,
                DATE(datetime(created_at, 'unixepoch')),
                datetime(created_at, 'unixepoch'),
                type, model_name, prompt_tokens, completion_tokens,
                CASE WHEN type = 1 THEN quota ELSE 0 END,
                quota
            FROM ods_logs
            WHERE NOT EXISTS (
                SELECT 1 FROM dwd_logs WHERE log_id = ods_logs.id
            )
        """)
        count = self.conn.total_changes
        self.conn.commit()
        print(f"✓ 已补齐 {count} 条记录")
        return count

    def check_dwd_to_ads_gaps(self):
        """检查DWD->ADS的缺失"""
        print("\n=== 检查 DWD -> ADS 缺失 ===")

        cursor = self.conn.execute("""
            SELECT DISTINCT log_date
            FROM dwd_logs
            WHERE log_date NOT IN (SELECT stat_date FROM ads_funnel_daily)
            ORDER BY log_date
        """)

        missing_dates = [row[0] for row in cursor.fetchall()]

        if missing_dates:
            print(f"发现 {len(missing_dates)} 个日期缺失ADS数据:")
            for date in missing_dates:
                print(f"  {date}")
            return True
        else:
            print("✓ DWD->ADS 无缺失")
            return False

    def repair_dwd_to_ads(self):
        """修复DWD->ADS缺失"""
        print("\n=== 修复 DWD -> ADS ===")

        from src.etl.dwd_to_dws import DWDToDWS
        from src.etl.dws_to_ads import DWSToADS

        print("重新计算DWS...")
        DWDToDWS(self.db_path).aggregate_user_lifecycle()

        print("重新计算ADS...")
        ads = DWSToADS(self.db_path)
        ads.calculate_funnel_daily()
        ads.calculate_retention_cohort()

        print("✓ ADS数据已重新计算")

    def repair_all(self):
        """检查并修复所有缺失"""
        print("开始数据修复检查...")

        # 检查并修复ODS->DWD
        if self.check_ods_to_dwd_gaps():
            self.repair_ods_to_dwd()

        # 检查并修复DWD->ADS
        if self.check_dwd_to_ads_gaps():
            self.repair_dwd_to_ads()

        # 重新导出看板
        print("\n=== 导出看板数据 ===")
        from export_dashboard_data import DashboardDataExporter
        exporter = DashboardDataExporter()
        exporter.connect()
        exporter.export_all()
        exporter.close()
        print("✓ 看板数据已更新")

        print("\n✓ 数据修复完成")

    def close(self):
        self.conn.close()


if __name__ == "__main__":
    repairer = DataRepairer()
    try:
        repairer.repair_all()
    finally:
        repairer.close()

