"""
初始化DWD层
创建DWD层表结构并执行首次数据转换
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from src.core.database import Database
from src.etl.ods_to_dwd import ODSToDWD


def main():
    print("="*70)
    print("DWD层初始化")
    print("="*70)

    # 1. 创建DWD层表结构
    print("\n步骤1: 创建DWD层表结构...")
    db = Database()
    db.connect()
    db.create_dwd_tables()
    db.close()

    print("\n" + "="*70)
    print("继续执行数据转换...")
    print("="*70)

    # 2. 执行ODS->DWD数据转换
    print("\n步骤2: 执行ODS->DWD数据转换...")
    etl = ODSToDWD()
    try:
        etl.run_full_transform()
    finally:
        etl.close()

    print("\n" + "="*70)
    print("✅ DWD层初始化完成！")
    print("="*70)
    print("\n现在你可以查询DWD层的脱敏数据了：")
    print("  - dwd_logs: 日志明细表（脱敏）")
    print("  - dwd_users: 用户明细表（脱敏）")
    print("\n建议：日常分析使用DWD层数据，避免直接查询ODS层")


if __name__ == "__main__":
    main()
