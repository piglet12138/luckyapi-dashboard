#!/usr/bin/env python3
"""
每日增量更新脚本
自动执行：增量同步 -> ETL计算 -> 导出看板数据
"""
import sys
import os
from datetime import datetime, timedelta
import logging

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.core.database import Database
from src.etl.ods_to_dwd import ODSToDWD
from src.etl.dwd_to_dws import DWDToDWS
from src.etl.dws_to_ads import DWSToADS
from export_dashboard_data import DashboardDataExporter
from src.sync.sync_incremental import IncrementalSync

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/daily_update.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class DailyUpdateTask:
    """每日增量更新任务"""

    def __init__(self, db_path: str = "newapi_warehouse.db"):
        self.db_path = db_path
        self.start_time = datetime.now()

    def run(self):
        """执行完整的每日更新流程"""
        logger.info("="*70)
        logger.info("开始每日增量更新")
        logger.info(f"执行时间: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info("="*70)

        try:
            # 步骤1: 增量同步API数据
            self.sync_incremental_data()

            # 步骤2: ODS -> DWD (数据清洗和脱敏)
            self.run_ods_to_dwd()

            # 步骤3: DWD -> DWS (数据汇总)
            self.run_dwd_to_dws()

            # 步骤4: DWS -> ADS (指标计算)
            self.run_dws_to_ads()

            # 步骤5: 导出看板数据
            self.export_dashboard_data()

            # 完成
            self.finish()

        except Exception as e:
            logger.error(f"更新失败: {str(e)}", exc_info=True)
            sys.exit(1)

    def sync_incremental_data(self):
        """增量同步API数据"""
        logger.info("\n步骤1: 增量同步API数据")
        logger.info("-"*70)

        sync = IncrementalSync(self.db_path)
        try:
            result = sync.sync_all()
            logger.info(f"API数据同步完成:")
            logger.info(f"  - 新增日志: {result['logs']} 条")
            logger.info(f"  - 同步用户: {result['users']} 条")
            logger.info(f"  - 同步渠道: {result['channels']} 条")
            logger.info(f"  - 耗时: {result['duration']:.1f}秒")
        finally:
            sync.close()

    def run_ods_to_dwd(self):
        """执行 ODS -> DWD"""
        logger.info("\n步骤2: ODS -> DWD (数据清洗和脱敏)")
        logger.info("-"*70)

        etl = ODSToDWD(self.db_path)
        try:
            # 增量处理：transform_logs会自动处理新数据
            logger.info("执行日志数据转换（增量）...")
            etl.transform_logs()

            logger.info("执行用户数据转换...")
            etl.transform_users()

            logger.info("ODS -> DWD 完成")
        finally:
            etl.close()

    def run_dwd_to_dws(self):
        """执行 DWD -> DWS"""
        logger.info("\n步骤3: DWD -> DWS (数据汇总)")
        logger.info("-"*70)

        etl = DWDToDWS(self.db_path)
        try:
            # 增量处理：只处理最近7天的数据
            end_date = datetime.now().strftime('%Y-%m-%d')
            start_date = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')

            logger.info(f"处理日期范围: {start_date} ~ {end_date}")

            etl.aggregate_user_daily(start_date, end_date)
            etl.aggregate_model_daily(start_date, end_date)
            etl.aggregate_channel_daily(start_date, end_date)
            etl.aggregate_user_lifecycle()  # 全量更新

            logger.info("DWD -> DWS 完成")
        finally:
            etl.close()

    def run_dws_to_ads(self):
        """执行 DWS -> ADS"""
        logger.info("\n步骤4: DWS -> ADS (指标计算)")
        logger.info("-"*70)

        etl = DWSToADS(self.db_path)
        try:
            # 增量处理：只处理最近30天的数据
            end_date = datetime.now().strftime('%Y-%m-%d')
            start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')

            logger.info(f"处理日期范围: {start_date} ~ {end_date}")

            # 每日汇总和漏斗（增量）
            etl.calculate_daily_summary(start_date, end_date)
            etl.calculate_funnel_daily(start_date, end_date)
            etl.calculate_user_segment_daily(start_date, end_date)
            etl.calculate_channel_attribution(start_date, end_date)
            etl.calculate_new_user_conversion(start_date, end_date)

            # 激活点分析和复购率（全量）
            etl.calculate_activation_analysis()
            etl.calculate_repurchase_analysis()

            logger.info("DWS -> ADS 完成")
        finally:
            etl.close()

    def export_dashboard_data(self):
        """导出看板数据"""
        logger.info("\n步骤5: 导出看板数据")
        logger.info("-"*70)

        exporter = DashboardDataExporter(self.db_path)
        exporter.export_all()
        logger.info("看板数据导出完成")

    def finish(self):
        """完成"""
        end_time = datetime.now()
        duration = (end_time - self.start_time).total_seconds()

        logger.info("\n" + "="*70)
        logger.info("每日增量更新完成！")
        logger.info(f"开始时间: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info(f"结束时间: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info(f"总耗时: {duration:.2f} 秒")
        logger.info("="*70)


if __name__ == "__main__":
    # 创建日志目录
    os.makedirs("logs", exist_ok=True)

    # 执行每日更新
    task = DailyUpdateTask()
    task.run()
