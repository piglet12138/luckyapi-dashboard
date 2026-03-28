"""
数据看板数据导出脚本
从ADS层导出JSON数据供前端看板使用
"""
import sys
import os
sys.path.append(os.path.dirname(__file__))

import sqlite3
import json
from datetime import datetime, date


class DashboardDataExporter:
    """数据看板数据导出器"""

    def __init__(self, db_path: str = "newapi_warehouse.db"):
        self.db_path = db_path
        self.conn = None

    def connect(self):
        """连接数据库"""
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row

    def close(self):
        """关闭数据库连接"""
        if self.conn:
            self.conn.close()

    def _row_to_dict(self, row):
        """将数据库行转换为字典，处理日期类型"""
        if row is None:
            return None
        d = dict(row)
        # 转换日期类型为字符串
        for key, value in d.items():
            if isinstance(value, date):
                d[key] = value.isoformat()
        return d

    def export_core_metrics(self):
        """导出核心指标（昨天和前天）- 分为健康度和增长质量两组"""
        # 健康度指标（跳过今天，取昨天和前天）
        cursor = self.conn.execute("""
            SELECT
                f.stat_date,
                f.active_users as dau,
                (SELECT COUNT(DISTINCT user_id) FROM dwd_logs
                 WHERE log_type = 1 AND log_date = f.stat_date) as paying_users,
                (SELECT COALESCE(SUM(topup_amount), 0) FROM dwd_logs
                 WHERE log_type = 1 AND log_date = f.stat_date) as daily_revenue,
                (SELECT COUNT(DISTINCT user_id) FROM dwd_logs
                 WHERE log_type = 1 AND log_date = f.stat_date
                   AND user_id IN (
                       SELECT user_id FROM dws_user_lifecycle WHERE topup_count >= 2
                   )) as repurchase_users,
                (SELECT COUNT(DISTINCT user_id) FROM (SELECT user_id, MIN(log_date) as reg FROM dwd_logs GROUP BY user_id) WHERE reg <= f.stat_date) as total_registered,
                (SELECT COUNT(DISTINCT user_id) FROM dws_user_lifecycle WHERE first_use_date <= f.stat_date) as total_activated,
                ((SELECT COUNT(DISTINCT user_id) FROM (SELECT user_id, MIN(log_date) as reg FROM dwd_logs GROUP BY user_id) WHERE reg <= f.stat_date) -
                 (SELECT COUNT(DISTINCT user_id) FROM dws_user_lifecycle WHERE first_use_date <= f.stat_date)) as inactive_pool
            FROM ads_funnel_daily f
            ORDER BY f.stat_date DESC
            LIMIT 3
        """)
        rows = cursor.fetchall()
        yesterday = self._row_to_dict(rows[1]) if len(rows) > 1 else {}
        day_before = self._row_to_dict(rows[2]) if len(rows) > 2 else {}

        health_metrics = {
            'today': yesterday,
            'yesterday': day_before
        }

        # 增长质量指标
        cursor = self.conn.execute("""
            SELECT
                stat_date,
                new_users,
                activated_new_users,
                (SELECT COUNT(DISTINCT user_id) FROM dwd_logs
                 WHERE log_type = 1 AND log_date = ads_funnel_daily.stat_date
                   AND user_id IN (
                       SELECT user_id FROM (SELECT user_id, MIN(log_date) as register_date FROM dwd_logs GROUP BY user_id)
                       WHERE register_date = ads_funnel_daily.stat_date
                   )) as d0_paying_users,
                d3_retention_rate
            FROM ads_funnel_daily
            ORDER BY stat_date DESC
            LIMIT 3
        """)
        rows = cursor.fetchall()
        yesterday = self._row_to_dict(rows[1]) if len(rows) > 1 else {}
        day_before = self._row_to_dict(rows[2]) if len(rows) > 2 else {}

        growth_metrics = {
            'today': yesterday,
            'yesterday': day_before
        }

        return {
            'health': health_metrics,
            'growth': growth_metrics
        }

    def export_daily_trends(self, days: int = 30):
        """导出每日趋势数据"""
        cursor = self.conn.execute(f"""
            SELECT
                stat_date,
                active_users as dau,
                total_calls,
                total_revenue,
                arpu,
                conversion_rate
            FROM ads_daily_summary
            ORDER BY stat_date DESC
            LIMIT {days}
        """)
        rows = cursor.fetchall()
        # 反转顺序，使时间从早到晚
        return [self._row_to_dict(row) for row in reversed(rows)]

    def export_user_segments(self):
        """导出用户分层数据"""
        cursor = self.conn.execute("""
            SELECT
                user_segment,
                COUNT(*) as user_count,
                SUM(total_call_count) as total_calls,
                SUM(total_topup_amount) as total_revenue
            FROM dws_user_lifecycle
            GROUP BY user_segment
            ORDER BY user_segment
        """)
        return [self._row_to_dict(row) for row in cursor.fetchall()]

    def export_model_usage(self, limit: int = 10):
        """导出模型使用Top N"""
        cursor = self.conn.execute(f"""
            SELECT
                model_name,
                SUM(call_count) as total_calls,
                SUM(user_count) as total_users
            FROM dws_model_daily
            GROUP BY model_name
            ORDER BY total_calls DESC
            LIMIT {limit}
        """)
        return [self._row_to_dict(row) for row in cursor.fetchall()]

    def export_activation_analysis(self):
        """导出激活点分析（仅取最新 stat_date，避免同一区间多日重复柱体）"""
        cursor = self.conn.execute("""
            SELECT
                call_range,
                user_count,
                paying_user_count,
                conversion_rate,
                avg_revenue_per_user
            FROM ads_activation_analysis
            WHERE stat_date = (SELECT MAX(stat_date) FROM ads_activation_analysis)
            ORDER BY CASE call_range
                WHEN '<5次' THEN 1
                WHEN '5-15次' THEN 2
                WHEN '15-50次' THEN 3
                WHEN '50-100次' THEN 4
                ELSE 5
            END
        """)
        return [self._row_to_dict(row) for row in cursor.fetchall()]

    def export_channel_attribution(self, limit: int = 10):
        """导出渠道归因Top N"""
        cursor = self.conn.execute(f"""
            SELECT
                first_model as channel,
                SUM(new_user_count) as new_users,
                SUM(paying_user_count) as paying_users,
                SUM(total_revenue) as revenue,
                ROUND(AVG(conversion_rate), 2) as avg_conversion_rate
            FROM ads_channel_attribution
            GROUP BY first_model
            ORDER BY new_users DESC
            LIMIT {limit}
        """)
        return [self._row_to_dict(row) for row in cursor.fetchall()]

    def export_funnel_latest(self):
        """导出最新的增长漏斗数据"""
        cursor = self.conn.execute("""
            SELECT
                registered_users,
                active_users,
                paying_users,
                new_users,
                activated_new_users,
                activation_rate,
                conversion_rate
            FROM ads_funnel_daily
            ORDER BY stat_date DESC
            LIMIT 1
        """)
        row = cursor.fetchone()
        return self._row_to_dict(row) if row else {}

    def export_user_growth(self, days: int = 30):
        """导出用户增长趋势"""
        cursor = self.conn.execute(f"""
            SELECT
                stat_date,
                new_users,
                active_users,
                paying_users
            FROM ads_daily_summary
            ORDER BY stat_date DESC
            LIMIT {days}
        """)
        rows = cursor.fetchall()
        return [self._row_to_dict(row) for row in reversed(rows)]

    def export_retention_trends(self, days: int = 30):
        """导出留存率趋势"""
        cursor = self.conn.execute(f"""
            SELECT
                stat_date,
                retention_rate,
                conversion_rate,
                repurchase_rate
            FROM ads_funnel_daily
            ORDER BY stat_date DESC
            LIMIT {days}
        """)
        rows = cursor.fetchall()
        return [self._row_to_dict(row) for row in reversed(rows)]

    def export_channel_details(self):
        """导出渠道详细数据（按渠道汇总）"""
        cursor = self.conn.execute("""
            SELECT
                first_model as channel,
                SUM(new_user_count) as new_users,
                SUM(paying_user_count) as paying_users,
                SUM(total_revenue) as revenue,
                ROUND(CAST(SUM(paying_user_count) AS FLOAT) / NULLIF(SUM(new_user_count), 0) * 100, 2) as conversion_rate,
                ROUND(SUM(total_revenue) / NULLIF(SUM(paying_user_count), 0), 2) as arppu
            FROM ads_channel_attribution
            GROUP BY first_model
            ORDER BY new_users DESC
        """)
        return [self._row_to_dict(row) for row in cursor.fetchall()]

    def export_new_user_conversion(self, days: int = 30):
        """导出新用户转化率数据（Phase 2新增）"""
        cursor = self.conn.execute(f"""
            SELECT
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
            FROM ads_new_user_conversion
            ORDER BY cohort_date DESC
            LIMIT {days}
        """)
        rows = cursor.fetchall()
        return [self._row_to_dict(row) for row in reversed(rows)]

    def export_repurchase_analysis(self):
        """导出分层复购率分析（Phase 2新增）"""
        cursor = self.conn.execute("""
            SELECT
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
            FROM ads_repurchase_analysis
            ORDER BY stat_date DESC
            LIMIT 1
        """)
        row = cursor.fetchone()
        return self._row_to_dict(row) if row else {}

    def export_registration_activation_analysis(self, days: int = 30):
        """导出注册激活分析（Phase 3新增）"""
        cursor = self.conn.execute(f"""
            SELECT
                stat_date,
                (SELECT COUNT(DISTINCT user_id) FROM (SELECT user_id, MIN(log_date) as reg FROM dwd_logs GROUP BY user_id) WHERE reg <= ads_funnel_daily.stat_date) as total_registered,
                (SELECT COUNT(DISTINCT user_id) FROM dws_user_lifecycle WHERE first_use_date <= ads_funnel_daily.stat_date) as total_activated,
                ((SELECT COUNT(DISTINCT user_id) FROM (SELECT user_id, MIN(log_date) as reg FROM dwd_logs GROUP BY user_id) WHERE reg <= ads_funnel_daily.stat_date) -
                 (SELECT COUNT(DISTINCT user_id) FROM dws_user_lifecycle WHERE first_use_date <= ads_funnel_daily.stat_date)) as inactive_pool,
                ROUND(CAST((SELECT COUNT(DISTINCT user_id) FROM dws_user_lifecycle WHERE first_use_date <= ads_funnel_daily.stat_date) AS FLOAT) /
                      NULLIF((SELECT COUNT(DISTINCT user_id) FROM (SELECT user_id, MIN(log_date) as reg FROM dwd_logs GROUP BY user_id) WHERE reg <= ads_funnel_daily.stat_date), 0) * 100, 2) as overall_activation_rate
            FROM ads_funnel_daily
            ORDER BY stat_date DESC
            LIMIT {days}
        """)
        rows = cursor.fetchall()
        return [self._row_to_dict(row) for row in reversed(rows)]

    def export_all(self, output_file: str = "dashboard/dashboard_data.json"):
        """导出所有数据到JSON文件"""
        print("="*70)
        print("开始导出数据看板数据")
        print("="*70)

        self.connect()

        try:
            # 收集所有数据
            data = {
                'update_time': datetime.now().isoformat(),
                'core_metrics': self.export_core_metrics(),
                'daily_trends': self.export_daily_trends(30),
                'user_growth': self.export_user_growth(30),
                'retention_trends': self.export_retention_trends(30),
                'user_segments': self.export_user_segments(),
                'model_usage': self.export_model_usage(10),
                'activation_analysis': self.export_activation_analysis(),
                'channel_attribution': self.export_channel_attribution(10),
                'channel_details': self.export_channel_details(),
                'funnel': self.export_funnel_latest(),
                # Phase 2 新增指标
                'new_user_conversion': self.export_new_user_conversion(30),
                'repurchase_analysis': self.export_repurchase_analysis(),
                # Phase 3 新增指标
                'registration_activation_analysis': self.export_registration_activation_analysis(30)
            }

            # 创建输出目录
            os.makedirs(os.path.dirname(output_file), exist_ok=True)

            # 保存为JSON
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2, default=str)

            print(f"\n[OK] 数据导出成功！")
            print(f"输出文件: {output_file}")
            print(f"更新时间: {data['update_time']}")
            print(f"\n数据统计:")
            print(f"  - 核心指标: {len(data['core_metrics'])} 项")
            print(f"  - 每日趋势: {len(data['daily_trends'])} 天")
            print(f"  - 用户增长: {len(data['user_growth'])} 天")
            print(f"  - 留存趋势: {len(data['retention_trends'])} 天")
            print(f"  - 用户分层: {len(data['user_segments'])} 个分层")
            print(f"  - 模型使用: {len(data['model_usage'])} 个模型")
            print(f"  - 激活分析: {len(data['activation_analysis'])} 个区间")
            print(f"  - 渠道归因: {len(data['channel_attribution'])} 个渠道")
            print(f"  - 渠道详情: {len(data['channel_details'])} 个渠道")
            print(f"  - 新用户转化率: {len(data['new_user_conversion'])} 天 (Phase 2)")
            print(f"  - 分层复购率: {len(data['repurchase_analysis'])} 项 (Phase 2)")

        finally:
            self.close()


if __name__ == "__main__":
    exporter = DashboardDataExporter()
    exporter.export_all()
    print("\n[OK] 导出完成！")
