"""
DWD层到DWS层的数据转换
实现数据汇总和聚合
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from datetime import datetime, timedelta
from src.core.database import Database


class DWDToDWS:
    """DWD层到DWS层的ETL转换"""

    def __init__(self, db_path: str = "newapi_warehouse.db"):
        self.db = Database(db_path)
        self.db.connect()

    def aggregate_user_daily(self, start_date: str = None, end_date: str = None):
        """
        汇总用户每日数据：DWD -> DWS

        Args:
            start_date: 开始日期（YYYY-MM-DD），默认为DWD层最早日期
            end_date: 结束日期（YYYY-MM-DD），默认为DWD层最晚日期
        """
        print("="*70)
        print("开始汇总用户每日数据：DWD -> DWS")
        print("="*70)

        # 获取日期范围
        if not start_date or not end_date:
            cursor = self.db.execute("""
                SELECT MIN(log_date) as min_date, MAX(log_date) as max_date
                FROM dwd_logs WHERE log_type = 2
            """)
            row = cursor.fetchone()
            start_date = start_date or row['min_date']
            end_date = end_date or row['max_date']

        print(f"日期范围: {start_date} ~ {end_date}")

        # 汇总SQL（简化版，去掉复杂子查询）
        sql = """
        INSERT OR REPLACE INTO dws_user_daily (
            stat_date, user_id,
            call_count, total_quota,
            total_prompt_tokens, total_completion_tokens, total_tokens,
            total_use_time,
            model_count, channel_count
        )
        SELECT
            log_date as stat_date,
            user_id,
            COUNT(*) as call_count,
            SUM(quota) as total_quota,
            SUM(prompt_tokens) as total_prompt_tokens,
            SUM(completion_tokens) as total_completion_tokens,
            SUM(total_tokens) as total_tokens,
            SUM(use_time) as total_use_time,
            COUNT(DISTINCT model_name) as model_count,
            COUNT(DISTINCT channel_id) as channel_count
        FROM dwd_logs
        WHERE log_type = 2
          AND log_date >= ?
          AND log_date <= ?
        GROUP BY log_date, user_id
        """

        cursor = self.db.execute(sql, (start_date, end_date))
        affected = cursor.rowcount
        print(f"汇总完成: {affected} 条记录")

        # 统计信息
        cursor = self.db.execute("""
            SELECT COUNT(*) as cnt FROM dws_user_daily
            WHERE stat_date >= ? AND stat_date <= ?
        """, (start_date, end_date))
        total = cursor.fetchone()['cnt']
        print(f"DWS层记录数: {total:,} 条")

    def aggregate_model_daily(self, start_date: str = None, end_date: str = None):
        """
        汇总模型每日数据：DWD -> DWS

        Args:
            start_date: 开始日期
            end_date: 结束日期
        """
        print("="*70)
        print("开始汇总模型每日数据：DWD -> DWS")
        print("="*70)

        # 获取日期范围
        if not start_date or not end_date:
            cursor = self.db.execute("""
                SELECT MIN(log_date) as min_date, MAX(log_date) as max_date
                FROM dwd_logs WHERE log_type = 2
            """)
            row = cursor.fetchone()
            start_date = start_date or row['min_date']
            end_date = end_date or row['max_date']

        print(f"日期范围: {start_date} ~ {end_date}")

        # 汇总SQL
        sql = """
        INSERT OR REPLACE INTO dws_model_daily (
            stat_date, model_name,
            call_count, user_count,
            total_quota, total_tokens,
            avg_tokens_per_call, avg_use_time
        )
        SELECT
            log_date as stat_date,
            model_name,
            COUNT(*) as call_count,
            COUNT(DISTINCT user_id) as user_count,
            SUM(quota) as total_quota,
            SUM(total_tokens) as total_tokens,
            ROUND(AVG(total_tokens), 2) as avg_tokens_per_call,
            ROUND(AVG(use_time), 2) as avg_use_time
        FROM dwd_logs
        WHERE log_type = 2
          AND log_date >= ?
          AND log_date <= ?
          AND model_name IS NOT NULL
        GROUP BY log_date, model_name
        """

        cursor = self.db.execute(sql, (start_date, end_date))
        affected = cursor.rowcount
        print(f"汇总完成: {affected} 条记录")

    def aggregate_channel_daily(self, start_date: str = None, end_date: str = None):
        """
        汇总渠道每日数据：DWD -> DWS

        Args:
            start_date: 开始日期
            end_date: 结束日期
        """
        print("="*70)
        print("开始汇总渠道每日数据：DWD -> DWS")
        print("="*70)

        # 获取日期范围
        if not start_date or not end_date:
            cursor = self.db.execute("""
                SELECT MIN(log_date) as min_date, MAX(log_date) as max_date
                FROM dwd_logs WHERE log_type = 2
            """)
            row = cursor.fetchone()
            start_date = start_date or row['min_date']
            end_date = end_date or row['max_date']

        print(f"日期范围: {start_date} ~ {end_date}")

        # 汇总SQL
        sql = """
        INSERT OR REPLACE INTO dws_channel_daily (
            stat_date, channel_id, channel_name,
            call_count, user_count,
            total_quota, avg_response_time
        )
        SELECT
            log_date as stat_date,
            channel_id,
            MAX(channel_name) as channel_name,
            COUNT(*) as call_count,
            COUNT(DISTINCT user_id) as user_count,
            SUM(quota) as total_quota,
            ROUND(AVG(use_time), 2) as avg_response_time
        FROM dwd_logs
        WHERE log_type = 2
          AND log_date >= ?
          AND log_date <= ?
          AND channel_id IS NOT NULL
        GROUP BY log_date, channel_id
        """

        cursor = self.db.execute(sql, (start_date, end_date))
        affected = cursor.rowcount
        print(f"汇总完成: {affected} 条记录")

    def aggregate_user_lifecycle(self):
        """
        汇总用户生命周期数据：DWD -> DWS
        """
        print("="*70)
        print("开始汇总用户生命周期数据：DWD -> DWS")
        print("="*70)

        # 获取当前日期
        today = datetime.now().date()

        # 先创建临时汇总表
        print("步骤1: 创建用户统计临时表...")
        self.db.execute("""
            CREATE TEMP TABLE IF NOT EXISTS temp_user_stats AS
            SELECT
                user_id,
                MIN(CASE WHEN log_type = 2 THEN log_date END) as first_use_date,
                MAX(CASE WHEN log_type = 2 THEN log_date END) as last_use_date,
                SUM(CASE WHEN log_type = 2 THEN 1 ELSE 0 END) as total_call_count,
                SUM(CASE WHEN log_type = 2 THEN quota ELSE 0 END) as total_quota,
                SUM(CASE WHEN log_type = 1 THEN topup_amount ELSE 0 END) as total_topup_amount,
                SUM(CASE WHEN log_type = 1 THEN 1 ELSE 0 END) as topup_count
            FROM dwd_logs
            GROUP BY user_id
        """)

        print("步骤2: 获取首次使用的模型和渠道...")
        self.db.execute("""
            CREATE TEMP TABLE IF NOT EXISTS temp_user_first AS
            SELECT
                user_id,
                model_name as first_model,
                channel_id as first_channel_id
            FROM (
                SELECT
                    user_id,
                    model_name,
                    channel_id,
                    ROW_NUMBER() OVER (PARTITION BY user_id ORDER BY log_datetime) as rn
                FROM dwd_logs
                WHERE log_type = 2
            )
            WHERE rn = 1
        """)

        print("步骤3: 插入用户生命周期数据...")
        sql = """
        INSERT OR REPLACE INTO dws_user_lifecycle (
            user_id,
            first_use_date, first_model, first_channel_id,
            last_use_date,
            total_call_count, total_quota,
            total_topup_amount, topup_count,
            days_since_first, days_since_last,
            is_active_7d, is_active_30d,
            user_segment
        )
        SELECT
            s.user_id,
            s.first_use_date,
            f.first_model,
            f.first_channel_id,
            s.last_use_date,
            s.total_call_count,
            s.total_quota,
            s.total_topup_amount,
            s.topup_count,
            CAST(julianday(?) - julianday(s.first_use_date) AS INT) as days_since_first,
            CAST(julianday(?) - julianday(s.last_use_date) AS INT) as days_since_last,
            CASE WHEN s.last_use_date >= date(?, '-7 days') THEN 1 ELSE 0 END as is_active_7d,
            CASE WHEN s.last_use_date >= date(?, '-30 days') THEN 1 ELSE 0 END as is_active_30d,
            CASE
                WHEN s.total_topup_amount IS NULL OR s.total_topup_amount = 0 THEN '0_未付费'
                WHEN s.total_topup_amount < 10 THEN '1_轻度'
                WHEN s.total_topup_amount < 100 THEN '2_中度'
                ELSE '3_重度'
            END as user_segment
        FROM temp_user_stats s
        LEFT JOIN temp_user_first f ON s.user_id = f.user_id
        """

        cursor = self.db.execute(sql, (today, today, today, today))
        affected = cursor.rowcount
        print(f"汇总完成: {affected} 条记录")

        # 清理临时表
        self.db.execute("DROP TABLE IF EXISTS temp_user_stats")
        self.db.execute("DROP TABLE IF EXISTS temp_user_first")

        # 统计信息
        cursor = self.db.execute("""
            SELECT
                user_segment,
                COUNT(*) as user_count,
                SUM(total_call_count) as total_calls,
                SUM(total_topup_amount) as total_revenue
            FROM dws_user_lifecycle
            GROUP BY user_segment
            ORDER BY user_segment
        """)

        print("\n用户分层统计:")
        for row in cursor.fetchall():
            print(f"  {row['user_segment']}: {row['user_count']:,} 人, "
                  f"调用 {row['total_calls']:,} 次, "
                  f"充值 ${row['total_revenue'] or 0:.2f}")

    def run_full_aggregation(self):
        """运行完整的DWD->DWS汇总流程"""
        print("\n" + "="*70)
        print("开始DWD->DWS完整汇总流程")
        print("="*70 + "\n")

        # 1. 汇总用户每日数据
        self.aggregate_user_daily()
        print()

        # 2. 汇总模型每日数据
        self.aggregate_model_daily()
        print()

        # 3. 汇总渠道每日数据
        self.aggregate_channel_daily()
        print()

        # 4. 汇总用户生命周期
        self.aggregate_user_lifecycle()

        print("\n" + "="*70)
        print("[OK] DWD->DWS汇总完成！")
        print("="*70)

        # 统计信息
        self._print_statistics()

    def _print_statistics(self):
        """打印统计信息"""
        print("\n" + "="*70)
        print("DWS层数据统计")
        print("="*70)

        # 用户每日汇总
        cursor = self.db.execute("SELECT COUNT(*) as cnt FROM dws_user_daily")
        count = cursor.fetchone()['cnt']
        print(f"用户每日汇总: {count:,} 条")

        # 模型每日汇总
        cursor = self.db.execute("SELECT COUNT(*) as cnt FROM dws_model_daily")
        count = cursor.fetchone()['cnt']
        print(f"模型每日汇总: {count:,} 条")

        # 渠道每日汇总
        cursor = self.db.execute("SELECT COUNT(*) as cnt FROM dws_channel_daily")
        count = cursor.fetchone()['cnt']
        print(f"渠道每日汇总: {count:,} 条")

        # 用户生命周期
        cursor = self.db.execute("SELECT COUNT(*) as cnt FROM dws_user_lifecycle")
        count = cursor.fetchone()['cnt']
        print(f"用户生命周期: {count:,} 个用户")

        # 日期范围
        cursor = self.db.execute("""
            SELECT MIN(stat_date) as min_date, MAX(stat_date) as max_date
            FROM dws_user_daily
        """)
        row = cursor.fetchone()
        if row['min_date']:
            print(f"\n时间范围: {row['min_date']} ~ {row['max_date']}")

        print("="*70)

    def close(self):
        """关闭数据库连接"""
        self.db.close()


if __name__ == "__main__":
    # 运行ETL转换
    etl = DWDToDWS()

    try:
        etl.run_full_aggregation()
    finally:
        etl.close()

    print("\n[OK] 所有汇总完成！")
