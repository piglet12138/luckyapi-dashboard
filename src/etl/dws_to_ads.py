"""
DWS层到ADS层的数据转换
实现业务指标计算和分析
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from datetime import datetime, timedelta
from src.core.database import Database


class DWSToADS:
    """DWS层到ADS层的ETL转换"""

    def __init__(self, db_path: str = "newapi_warehouse.db"):
        self.db = Database(db_path)
        self.db.connect()

    def calculate_daily_summary(self, start_date: str = None, end_date: str = None):
        """
        计算每日汇总指标：DWS -> ADS

        Args:
            start_date: 开始日期（YYYY-MM-DD）
            end_date: 结束日期（YYYY-MM-DD）
        """
        print("="*70)
        print("开始计算每日汇总指标：DWS -> ADS")
        print("="*70)

        # 获取日期范围
        if not start_date or not end_date:
            cursor = self.db.execute("""
                SELECT MIN(stat_date) as min_date, MAX(stat_date) as max_date
                FROM dws_user_daily
            """)
            row = cursor.fetchone()
            start_date = start_date or row['min_date']
            end_date = end_date or row['max_date']

        print(f"日期范围: {start_date} ~ {end_date}")

        # 计算每日汇总指标
        sql = """
        INSERT OR REPLACE INTO ads_daily_summary (
            stat_date,
            total_users, active_users, new_users, paying_users,
            total_calls, total_quota, total_tokens,
            total_revenue, new_revenue,
            arpu, arppu,
            conversion_rate, activation_rate
        )
        SELECT
            d.stat_date,

            -- 用户指标
            (SELECT COUNT(*) FROM dws_user_lifecycle) as total_users,
            COUNT(DISTINCT d.user_id) as active_users,
            (SELECT COUNT(*) FROM dws_user_lifecycle WHERE first_use_date = d.stat_date) as new_users,
            (SELECT COUNT(DISTINCT user_id) FROM dwd_logs WHERE log_type = 1 AND log_date = d.stat_date) as paying_users,

            -- 使用指标
            SUM(d.call_count) as total_calls,
            SUM(d.total_quota) as total_quota,
            SUM(d.total_tokens) as total_tokens,

            -- 财务指标
            (SELECT COALESCE(SUM(topup_amount), 0) FROM dwd_logs WHERE log_type = 1 AND log_date <= d.stat_date) as total_revenue,
            (SELECT COALESCE(SUM(topup_amount), 0) FROM dwd_logs WHERE log_type = 1 AND log_date = d.stat_date) as new_revenue,

            -- ARPU和ARPPU
            ROUND((SELECT COALESCE(SUM(topup_amount), 0) FROM dwd_logs WHERE log_type = 1 AND log_date = d.stat_date) /
                  NULLIF(COUNT(DISTINCT d.user_id), 0), 2) as arpu,
            ROUND((SELECT COALESCE(SUM(topup_amount), 0) FROM dwd_logs WHERE log_type = 1 AND log_date = d.stat_date) /
                  NULLIF((SELECT COUNT(DISTINCT user_id) FROM dwd_logs WHERE log_type = 1 AND log_date = d.stat_date), 0), 2) as arppu,

            -- 转化率
            ROUND(CAST((SELECT COUNT(DISTINCT user_id) FROM dwd_logs WHERE log_type = 1 AND log_date = d.stat_date) AS FLOAT) /
                  NULLIF(COUNT(DISTINCT d.user_id), 0) * 100, 2) as conversion_rate,

            -- 激活率（当日新用户中有调用的比例）
            ROUND(CAST(COUNT(DISTINCT d.user_id) AS FLOAT) /
                  NULLIF((SELECT COUNT(*) FROM dws_user_lifecycle WHERE first_use_date = d.stat_date), 0) * 100, 2) as activation_rate

        FROM dws_user_daily d
        WHERE d.stat_date >= ?
          AND d.stat_date <= ?
        GROUP BY d.stat_date
        """

        cursor = self.db.execute(sql, (start_date, end_date))
        affected = cursor.rowcount
        print(f"计算完成: {affected} 条记录")

    def calculate_funnel_daily(self, start_date: str = None, end_date: str = None):
        """
        计算增长漏斗：DWS -> ADS

        Args:
            start_date: 开始日期
            end_date: 结束日期
        """
        print("="*70)
        print("开始计算增长漏斗：DWS -> ADS")
        print("="*70)

        # 获取日期范围
        if not start_date or not end_date:
            cursor = self.db.execute("""
                SELECT MIN(stat_date) as min_date, MAX(stat_date) as max_date
                FROM dws_user_daily
            """)
            row = cursor.fetchone()
            start_date = start_date or row['min_date']
            end_date = end_date or row['max_date']

        print(f"日期范围: {start_date} ~ {end_date}")

        # 计算漏斗指标
        sql = """
        INSERT OR REPLACE INTO ads_funnel_daily (
            stat_date,
            registered_users, active_users, retained_7d_users,
            paying_users, repurchase_users,
            new_users, activated_new_users,
            activation_rate, retention_rate, d3_retention_rate, conversion_rate, repurchase_rate
        )
        SELECT
            stat_date,

            -- 漏斗各层
            (SELECT COUNT(*) FROM dws_user_lifecycle WHERE first_use_date <= stat_date) as registered_users,
            (SELECT COUNT(DISTINCT user_id) FROM dws_user_daily WHERE stat_date = main.stat_date) as active_users,

            -- 修复：7日留存用户数（7天前活跃且今天仍活跃的用户）
            (SELECT COUNT(DISTINCT d1.user_id)
             FROM dws_user_daily d1
             WHERE d1.stat_date = date(main.stat_date, '-7 days')
               AND EXISTS (
                   SELECT 1 FROM dws_user_daily d2
                   WHERE d2.user_id = d1.user_id
                     AND d2.stat_date = main.stat_date
               )) as retained_7d_users,

            -- 修复：累计付费用户数（用于复购率计算）
            (SELECT COUNT(DISTINCT user_id) FROM dwd_logs
             WHERE log_type = 1 AND log_date <= main.stat_date) as paying_users,
            (SELECT COUNT(DISTINCT user_id) FROM dws_user_lifecycle
             WHERE topup_count >= 2 AND first_use_date <= main.stat_date) as repurchase_users,

            -- 新用户激活（用首次日志时间作为注册时间）
            (SELECT COUNT(DISTINCT user_id)
             FROM (SELECT user_id, MIN(log_date) as register_date FROM dwd_logs GROUP BY user_id)
             WHERE register_date = main.stat_date) as new_users,
            (SELECT COUNT(DISTINCT d.user_id)
             FROM dws_user_daily d
             WHERE d.stat_date = main.stat_date
               AND d.user_id IN (
                   SELECT user_id FROM (SELECT user_id, MIN(log_date) as register_date FROM dwd_logs GROUP BY user_id)
                   WHERE register_date = main.stat_date
               )) as activated_new_users,

            -- 新用户激活率
            ROUND(CAST((SELECT COUNT(DISTINCT d.user_id)
                        FROM dws_user_daily d
                        WHERE d.stat_date = main.stat_date
                          AND d.user_id IN (
                              SELECT user_id FROM (SELECT user_id, MIN(log_date) as register_date FROM dwd_logs GROUP BY user_id)
                              WHERE register_date = main.stat_date
                          )) AS FLOAT) /
                  NULLIF((SELECT COUNT(DISTINCT user_id)
                          FROM (SELECT user_id, MIN(log_date) as register_date FROM dwd_logs GROUP BY user_id)
                          WHERE register_date = main.stat_date), 0) * 100, 2) as activation_rate,

            -- 修复：7日留存率（7天前活跃用户中今天仍活跃的比例）
            ROUND(CAST((SELECT COUNT(DISTINCT d1.user_id)
                        FROM dws_user_daily d1
                        WHERE d1.stat_date = date(main.stat_date, '-7 days')
                          AND EXISTS (
                              SELECT 1 FROM dws_user_daily d2
                              WHERE d2.user_id = d1.user_id
                                AND d2.stat_date = main.stat_date
                          )) AS FLOAT) /
                  NULLIF((SELECT COUNT(DISTINCT user_id) FROM dws_user_daily WHERE stat_date = date(main.stat_date, '-7 days')), 0) * 100, 2) as retention_rate,

            -- D3留存率（3天前注册的新用户中今天仍活跃的比例）
            ROUND(CAST((SELECT COUNT(DISTINCT d.user_id)
                        FROM dws_user_daily d
                        WHERE d.stat_date = main.stat_date
                          AND d.user_id IN (
                              SELECT user_id FROM (SELECT user_id, MIN(log_date) as register_date FROM dwd_logs GROUP BY user_id)
                              WHERE register_date = date(main.stat_date, '-3 days')
                          )) AS FLOAT) /
                  NULLIF((SELECT COUNT(DISTINCT user_id)
                          FROM (SELECT user_id, MIN(log_date) as register_date FROM dwd_logs GROUP BY user_id)
                          WHERE register_date = date(main.stat_date, '-3 days')), 0) * 100, 2) as d3_retention_rate,

            -- 修复：当日付费转化率（当日付费用户 / 当日活跃用户）
            ROUND(CAST((SELECT COUNT(DISTINCT user_id) FROM dwd_logs WHERE log_type = 1 AND log_date = main.stat_date) AS FLOAT) /
                  NULLIF((SELECT COUNT(DISTINCT user_id) FROM dws_user_daily WHERE stat_date = main.stat_date), 0) * 100, 2) as conversion_rate,

            -- 复购率（多次充值用户 / 累计付费用户）
            ROUND(CAST((SELECT COUNT(DISTINCT user_id) FROM dws_user_lifecycle WHERE topup_count >= 2 AND first_use_date <= main.stat_date) AS FLOAT) /
                  NULLIF((SELECT COUNT(DISTINCT user_id) FROM dwd_logs WHERE log_type = 1 AND log_date <= main.stat_date), 0) * 100, 2) as repurchase_rate

        FROM (
            SELECT DISTINCT stat_date
            FROM dws_user_daily
            WHERE stat_date >= ? AND stat_date <= ?
        ) main
        """

        cursor = self.db.execute(sql, (start_date, end_date))
        affected = cursor.rowcount
        print(f"计算完成: {affected} 条记录")

    def calculate_user_segment_daily(self, start_date: str = None, end_date: str = None):
        """
        计算用户分层每日数据：DWS -> ADS

        Args:
            start_date: 开始日期
            end_date: 结束日期
        """
        print("="*70)
        print("开始计算用户分层每日数据：DWS -> ADS")
        print("="*70)

        # 获取日期范围
        if not start_date or not end_date:
            cursor = self.db.execute("""
                SELECT MIN(stat_date) as min_date, MAX(stat_date) as max_date
                FROM dws_user_daily
            """)
            row = cursor.fetchone()
            start_date = start_date or row['min_date']
            end_date = end_date or row['max_date']

        print(f"日期范围: {start_date} ~ {end_date}")

        # 计算用户分层
        sql = """
        INSERT OR REPLACE INTO ads_user_segment_daily (
            stat_date, segment,
            user_count, total_calls, avg_calls_per_user,
            total_quota, total_revenue
        )
        SELECT
            d.stat_date,
            l.user_segment as segment,
            COUNT(DISTINCT d.user_id) as user_count,
            SUM(d.call_count) as total_calls,
            ROUND(AVG(d.call_count), 2) as avg_calls_per_user,
            SUM(d.total_quota) as total_quota,
            COALESCE(SUM(
                (SELECT SUM(topup_amount)
                 FROM dwd_logs
                 WHERE user_id = d.user_id
                   AND log_type = 1
                   AND log_date = d.stat_date)
            ), 0) as total_revenue
        FROM dws_user_daily d
        JOIN dws_user_lifecycle l ON d.user_id = l.user_id
        WHERE d.stat_date >= ?
          AND d.stat_date <= ?
        GROUP BY d.stat_date, l.user_segment
        """

        cursor = self.db.execute(sql, (start_date, end_date))
        affected = cursor.rowcount
        print(f"计算完成: {affected} 条记录")

    def calculate_activation_analysis(self):
        """
        计算激活点分析：DWS -> ADS
        分析不同调用次数区间的用户转化率
        """
        print("="*70)
        print("开始计算激活点分析：DWS -> ADS")
        print("="*70)

        # 获取最新日期
        cursor = self.db.execute("SELECT MAX(stat_date) as max_date FROM dws_user_daily")
        latest_date = cursor.fetchone()['max_date']
        print(f"分析日期: {latest_date}")

        # 计算激活点分析
        sql = """
        INSERT OR REPLACE INTO ads_activation_analysis (
            stat_date, call_range,
            user_count, paying_user_count, conversion_rate, avg_revenue_per_user
        )
        SELECT
            ? as stat_date,
            call_range,
            COUNT(*) as user_count,
            SUM(CASE WHEN total_topup_amount > 0 THEN 1 ELSE 0 END) as paying_user_count,
            ROUND(CAST(SUM(CASE WHEN total_topup_amount > 0 THEN 1 ELSE 0 END) AS FLOAT) /
                  NULLIF(COUNT(*), 0) * 100, 2) as conversion_rate,
            ROUND(AVG(COALESCE(total_topup_amount, 0)), 2) as avg_revenue_per_user
        FROM (
            SELECT
                user_id,
                total_call_count,
                total_topup_amount,
                CASE
                    WHEN total_call_count < 5 THEN '<5次'
                    WHEN total_call_count < 15 THEN '5-15次'
                    WHEN total_call_count < 50 THEN '15-50次'
                    WHEN total_call_count < 100 THEN '50-100次'
                    ELSE '>100次'
                END as call_range
            FROM dws_user_lifecycle
        )
        GROUP BY call_range
        """

        cursor = self.db.execute(sql, (latest_date,))
        affected = cursor.rowcount
        print(f"计算完成: {affected} 条记录")

    def calculate_channel_attribution(self, start_date: str = None, end_date: str = None):
        """
        计算渠道归因：DWS -> ADS
        基于用户首次使用的模型作为渠道

        Args:
            start_date: 开始日期
            end_date: 结束日期
        """
        print("="*70)
        print("开始计算渠道归因：DWS -> ADS")
        print("="*70)

        # 获取日期范围
        if not start_date or not end_date:
            cursor = self.db.execute("""
                SELECT MIN(first_use_date) as min_date, MAX(first_use_date) as max_date
                FROM dws_user_lifecycle
            """)
            row = cursor.fetchone()
            start_date = start_date or row['min_date']
            end_date = end_date or row['max_date']

        print(f"日期范围: {start_date} ~ {end_date}")

        # 计算渠道归因
        sql = """
        INSERT OR REPLACE INTO ads_channel_attribution (
            stat_date, first_model,
            new_user_count, paying_user_count, total_revenue,
            conversion_rate, arppu
        )
        SELECT
            first_use_date as stat_date,
            COALESCE(first_model, 'Unknown') as first_model,
            COUNT(*) as new_user_count,
            SUM(CASE WHEN total_topup_amount > 0 THEN 1 ELSE 0 END) as paying_user_count,
            SUM(COALESCE(total_topup_amount, 0)) as total_revenue,
            ROUND(CAST(SUM(CASE WHEN total_topup_amount > 0 THEN 1 ELSE 0 END) AS FLOAT) /
                  NULLIF(COUNT(*), 0) * 100, 2) as conversion_rate,
            ROUND(SUM(COALESCE(total_topup_amount, 0)) /
                  NULLIF(SUM(CASE WHEN total_topup_amount > 0 THEN 1 ELSE 0 END), 0), 2) as arppu
        FROM dws_user_lifecycle
        WHERE first_use_date >= ?
          AND first_use_date <= ?
        GROUP BY first_use_date, first_model
        """

        cursor = self.db.execute(sql, (start_date, end_date))
        affected = cursor.rowcount
        print(f"计算完成: {affected} 条记录")

    def calculate_new_user_conversion(self, start_date: str = None, end_date: str = None):
        """
        计算新用户转化率：DWS -> ADS
        按首次使用日期（cohort_date）计算新用户的D0/D3/D7/D30转化率

        Args:
            start_date: 开始日期
            end_date: 结束日期
        """
        print("="*70)
        print("开始计算新用户转化率：DWS -> ADS")
        print("="*70)

        # 获取日期范围
        if not start_date or not end_date:
            cursor = self.db.execute("""
                SELECT MIN(first_use_date) as min_date, MAX(first_use_date) as max_date
                FROM dws_user_lifecycle
                WHERE first_use_date IS NOT NULL
            """)
            row = cursor.fetchone()
            start_date = start_date or row['min_date']
            end_date = end_date or row['max_date']

        print(f"日期范围: {start_date} ~ {end_date}")

        # 计算新用户转化率
        sql = """
        INSERT OR REPLACE INTO ads_new_user_conversion (
            cohort_date,
            new_users,
            d0_paying_users,
            d3_paying_users,
            d7_paying_users,
            d30_paying_users,
            d0_conversion_rate,
            d3_conversion_rate,
            d7_conversion_rate,
            d30_conversion_rate
        )
        SELECT
            ulc.first_use_date as cohort_date,
            COUNT(*) as new_users,

            -- D0付费用户（首次使用当天付费）
            SUM(CASE
                WHEN EXISTS (
                    SELECT 1 FROM dwd_logs l
                    WHERE l.user_id = ulc.user_id
                      AND l.log_type = 1
                      AND l.log_date = ulc.first_use_date
                ) THEN 1 ELSE 0
            END) as d0_paying_users,

            -- D3付费用户（首次使用后3天内付费）
            SUM(CASE
                WHEN EXISTS (
                    SELECT 1 FROM dwd_logs l
                    WHERE l.user_id = ulc.user_id
                      AND l.log_type = 1
                      AND l.log_date <= date(ulc.first_use_date, '+3 days')
                ) THEN 1 ELSE 0
            END) as d3_paying_users,

            -- D7付费用户（首次使用后7天内付费）
            SUM(CASE
                WHEN EXISTS (
                    SELECT 1 FROM dwd_logs l
                    WHERE l.user_id = ulc.user_id
                      AND l.log_type = 1
                      AND l.log_date <= date(ulc.first_use_date, '+7 days')
                ) THEN 1 ELSE 0
            END) as d7_paying_users,

            -- D30付费用户（首次使用后30天内付费）
            SUM(CASE
                WHEN EXISTS (
                    SELECT 1 FROM dwd_logs l
                    WHERE l.user_id = ulc.user_id
                      AND l.log_type = 1
                      AND l.log_date <= date(ulc.first_use_date, '+30 days')
                ) THEN 1 ELSE 0
            END) as d30_paying_users,

            -- 转化率计算
            ROUND(CAST(SUM(CASE
                WHEN EXISTS (
                    SELECT 1 FROM dwd_logs l
                    WHERE l.user_id = ulc.user_id
                      AND l.log_type = 1
                      AND l.log_date = ulc.first_use_date
                ) THEN 1 ELSE 0
            END) AS FLOAT) / COUNT(*) * 100, 2) as d0_conversion_rate,

            ROUND(CAST(SUM(CASE
                WHEN EXISTS (
                    SELECT 1 FROM dwd_logs l
                    WHERE l.user_id = ulc.user_id
                      AND l.log_type = 1
                      AND l.log_date <= date(ulc.first_use_date, '+3 days')
                ) THEN 1 ELSE 0
            END) AS FLOAT) / COUNT(*) * 100, 2) as d3_conversion_rate,

            ROUND(CAST(SUM(CASE
                WHEN EXISTS (
                    SELECT 1 FROM dwd_logs l
                    WHERE l.user_id = ulc.user_id
                      AND l.log_type = 1
                      AND l.log_date <= date(ulc.first_use_date, '+7 days')
                ) THEN 1 ELSE 0
            END) AS FLOAT) / COUNT(*) * 100, 2) as d7_conversion_rate,

            ROUND(CAST(SUM(CASE
                WHEN EXISTS (
                    SELECT 1 FROM dwd_logs l
                    WHERE l.user_id = ulc.user_id
                      AND l.log_type = 1
                      AND l.log_date <= date(ulc.first_use_date, '+30 days')
                ) THEN 1 ELSE 0
            END) AS FLOAT) / COUNT(*) * 100, 2) as d30_conversion_rate

        FROM dws_user_lifecycle ulc
        WHERE ulc.first_use_date IS NOT NULL
          AND ulc.first_use_date >= ?
          AND ulc.first_use_date <= ?
        GROUP BY ulc.first_use_date
        ORDER BY ulc.first_use_date
        """

        cursor = self.db.execute(sql, (start_date, end_date))
        affected = cursor.rowcount
        print(f"计算完成: {affected} 条记录")

        # 显示最新的转化率数据
        cursor = self.db.execute("""
            SELECT
                cohort_date,
                new_users,
                d0_conversion_rate,
                d3_conversion_rate,
                d7_conversion_rate,
                d30_conversion_rate
            FROM ads_new_user_conversion
            ORDER BY cohort_date DESC
            LIMIT 5
        """)

        print("\n最新的新用户转化率（最近5天）:")
        print(f"{'日期':<12} {'新用户':<8} {'D0转化':<8} {'D3转化':<8} {'D7转化':<8} {'D30转化':<8}")
        print("-" * 60)
        for row in cursor.fetchall():
            print(f"{row['cohort_date']:<12} {row['new_users']:<8} "
                  f"{row['d0_conversion_rate'] or 0:<7.2f}% "
                  f"{row['d3_conversion_rate'] or 0:<7.2f}% "
                  f"{row['d7_conversion_rate'] or 0:<7.2f}% "
                  f"{row['d30_conversion_rate'] or 0:<7.2f}%")

    def calculate_repurchase_analysis(self):
        """
        计算分层复购率分析：DWS -> ADS
        按充值次数分层：单次、低频（2-5次）、中频（6-20次）、高频（>20次）
        """
        print("="*70)
        print("开始计算分层复购率分析：DWS -> ADS")
        print("="*70)

        # 获取最新日期
        cursor = self.db.execute("SELECT MAX(stat_date) as max_date FROM dws_user_daily")
        latest_date = cursor.fetchone()['max_date']
        print(f"分析日期: {latest_date}")

        # 计算分层复购率
        sql = """
        INSERT OR REPLACE INTO ads_repurchase_analysis (
            stat_date,
            total_paying_users,
            single_purchase_users,
            low_frequency_users,
            mid_frequency_users,
            high_frequency_users,
            single_purchase_rate,
            low_frequency_rate,
            mid_frequency_rate,
            high_frequency_rate,
            overall_repurchase_rate
        )
        SELECT
            ? as stat_date,

            -- 总付费用户数
            COUNT(*) as total_paying_users,

            -- 各层级用户数
            SUM(CASE WHEN topup_count = 1 THEN 1 ELSE 0 END) as single_purchase_users,
            SUM(CASE WHEN topup_count >= 2 AND topup_count <= 5 THEN 1 ELSE 0 END) as low_frequency_users,
            SUM(CASE WHEN topup_count >= 6 AND topup_count <= 20 THEN 1 ELSE 0 END) as mid_frequency_users,
            SUM(CASE WHEN topup_count > 20 THEN 1 ELSE 0 END) as high_frequency_users,

            -- 各层级占比
            ROUND(CAST(SUM(CASE WHEN topup_count = 1 THEN 1 ELSE 0 END) AS FLOAT) /
                  COUNT(*) * 100, 2) as single_purchase_rate,
            ROUND(CAST(SUM(CASE WHEN topup_count >= 2 AND topup_count <= 5 THEN 1 ELSE 0 END) AS FLOAT) /
                  COUNT(*) * 100, 2) as low_frequency_rate,
            ROUND(CAST(SUM(CASE WHEN topup_count >= 6 AND topup_count <= 20 THEN 1 ELSE 0 END) AS FLOAT) /
                  COUNT(*) * 100, 2) as mid_frequency_rate,
            ROUND(CAST(SUM(CASE WHEN topup_count > 20 THEN 1 ELSE 0 END) AS FLOAT) /
                  COUNT(*) * 100, 2) as high_frequency_rate,

            -- 整体复购率（≥2次）
            ROUND(CAST(SUM(CASE WHEN topup_count >= 2 THEN 1 ELSE 0 END) AS FLOAT) /
                  COUNT(*) * 100, 2) as overall_repurchase_rate

        FROM dws_user_lifecycle
        WHERE topup_count > 0
        """

        cursor = self.db.execute(sql, (latest_date,))
        affected = cursor.rowcount
        print(f"计算完成: {affected} 条记录")

        # 显示分层复购率数据
        cursor = self.db.execute("""
            SELECT
                stat_date,
                total_paying_users,
                single_purchase_users,
                low_frequency_users,
                mid_frequency_users,
                high_frequency_users,
                overall_repurchase_rate
            FROM ads_repurchase_analysis
            ORDER BY stat_date DESC
            LIMIT 1
        """)

        row = cursor.fetchone()
        if row:
            print(f"\n分层复购率分析结果 ({row['stat_date']}):")
            print(f"  总付费用户: {row['total_paying_users']:,} 人")
            print(f"  单次充值用户: {row['single_purchase_users']:,} 人 ({100 - (row['overall_repurchase_rate'] or 0):.2f}%)")
            print(f"  低频复购用户（2-5次）: {row['low_frequency_users']:,} 人")
            print(f"  中频复购用户（6-20次）: {row['mid_frequency_users']:,} 人")
            print(f"  高频复购用户（>20次）: {row['high_frequency_users']:,} 人")
            print(f"  整体复购率: {row['overall_repurchase_rate'] or 0:.2f}%")

    def run_full_calculation(self):
        """运行完整的DWS->ADS计算流程"""
        print("\n" + "="*70)
        print("开始DWS->ADS完整计算流程")
        print("="*70 + "\n")

        # 1. 计算每日汇总指标
        self.calculate_daily_summary()
        print()

        # 2. 计算增长漏斗
        self.calculate_funnel_daily()
        print()

        # 3. 计算用户分层
        self.calculate_user_segment_daily()
        print()

        # 4. 计算激活点分析
        self.calculate_activation_analysis()
        print()

        # 5. 计算渠道归因
        self.calculate_channel_attribution()
        print()

        # 6. 计算新用户转化率（Phase 2新增）
        self.calculate_new_user_conversion()
        print()

        # 7. 计算分层复购率（Phase 2新增）
        self.calculate_repurchase_analysis()

        print("\n" + "="*70)
        print("[OK] DWS->ADS计算完成！")
        print("="*70)

        # 统计信息
        self._print_statistics()

    def _print_statistics(self):
        """打印统计信息"""
        print("\n" + "="*70)
        print("ADS层数据统计")
        print("="*70)

        # 每日汇总
        cursor = self.db.execute("SELECT COUNT(*) as cnt FROM ads_daily_summary")
        count = cursor.fetchone()['cnt']
        print(f"每日汇总: {count:,} 天")

        # 增长漏斗
        cursor = self.db.execute("SELECT COUNT(*) as cnt FROM ads_funnel_daily")
        count = cursor.fetchone()['cnt']
        print(f"增长漏斗: {count:,} 天")

        # 用户分层
        cursor = self.db.execute("SELECT COUNT(*) as cnt FROM ads_user_segment_daily")
        count = cursor.fetchone()['cnt']
        print(f"用户分层: {count:,} 条")

        # 激活点分析
        cursor = self.db.execute("SELECT COUNT(*) as cnt FROM ads_activation_analysis")
        count = cursor.fetchone()['cnt']
        print(f"激活点分析: {count:,} 条")

        # 渠道归因
        cursor = self.db.execute("SELECT COUNT(*) as cnt FROM ads_channel_attribution")
        count = cursor.fetchone()['cnt']
        print(f"渠道归因: {count:,} 条")

        # 新用户转化率（Phase 2）
        cursor = self.db.execute("SELECT COUNT(*) as cnt FROM ads_new_user_conversion")
        count = cursor.fetchone()['cnt']
        print(f"新用户转化率: {count:,} 天")

        # 分层复购率（Phase 2）
        cursor = self.db.execute("SELECT COUNT(*) as cnt FROM ads_repurchase_analysis")
        count = cursor.fetchone()['cnt']
        print(f"分层复购率: {count:,} 条")

        # 最新指标
        cursor = self.db.execute("""
            SELECT
                stat_date,
                active_users as dau,
                total_calls,
                total_revenue,
                conversion_rate
            FROM ads_daily_summary
            ORDER BY stat_date DESC
            LIMIT 1
        """)
        row = cursor.fetchone()
        if row:
            print(f"\n最新指标 ({row['stat_date']}):")
            print(f"  DAU: {row['dau']:,}")
            print(f"  调用次数: {row['total_calls']:,}")
            print(f"  累计收入: ${row['total_revenue']:,.2f}")
            print(f"  转化率: {row['conversion_rate']}%")

        print("="*70)

    def close(self):
        """关闭数据库连接"""
        self.db.close()


if __name__ == "__main__":
    # 运行ETL转换
    etl = DWSToADS()

    try:
        etl.run_full_calculation()
    finally:
        etl.close()

    print("\n[OK] 所有计算完成！")
