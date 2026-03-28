"""
初始化DWS层
创建DWS层表结构并执行首次数据汇总
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from src.core.database import Database
from src.etl.dwd_to_dws import DWDToDWS


def main():
    print("="*70)
    print("DWS层初始化")
    print("="*70)

    # 1. 创建DWS层表结构
    print("\n步骤1: 创建DWS层表结构...")
    db = Database()
    db.connect()
    db.create_dws_tables()
    db.close()

    print("\n" + "="*70)
    print("继续执行数据汇总...")
    print("="*70)

    # 2. 执行DWD->DWS数据汇总
    print("\n步骤2: 执行DWD->DWS数据汇总...")
    etl = DWDToDWS()
    try:
        etl.run_full_aggregation()
    finally:
        etl.close()

    print("\n" + "="*70)
    print("[OK] DWS层初始化完成！")
    print("="*70)
    print("\n现在你可以查询DWS层的汇总数据了：")
    print("  - dws_user_daily: 用户每日汇总")
    print("  - dws_model_daily: 模型每日汇总")
    print("  - dws_channel_daily: 渠道每日汇总")
    print("  - dws_user_lifecycle: 用户生命周期")
    print("\n建议：使用DWS层数据进行趋势分析和指标计算")


if __name__ == "__main__":
    main()
