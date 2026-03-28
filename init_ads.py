"""
初始化ADS层
创建ADS层表结构并执行首次指标计算
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from src.core.database import Database
from src.etl.dws_to_ads import DWSToADS


def main():
    print("="*70)
    print("ADS层初始化")
    print("="*70)

    # 1. 创建ADS层表结构
    print("\n步骤1: 创建ADS层表结构...")
    db = Database()
    db.connect()
    db.create_ads_tables()
    db.close()

    print("\n" + "="*70)
    print("继续执行指标计算...")
    print("="*70)

    # 2. 执行DWS->ADS指标计算
    print("\n步骤2: 执行DWS->ADS指标计算...")
    etl = DWSToADS()
    try:
        etl.run_full_calculation()
    finally:
        etl.close()

    print("\n" + "="*70)
    print("[OK] ADS层初始化完成！")
    print("="*70)
    print("\n现在你可以查询ADS层的业务指标了：")
    print("  - ads_daily_summary: 每日汇总指标")
    print("  - ads_funnel_daily: 增长漏斗")
    print("  - ads_user_segment_daily: 用户分层每日")
    print("  - ads_activation_analysis: 激活点分析")
    print("  - ads_channel_attribution: 渠道归因")
    print("\n这些数据可以直接用于数据看板展示！")


if __name__ == "__main__":
    main()
