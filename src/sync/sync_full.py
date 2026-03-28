"""
主同步脚本
使用时间范围分批同步策略，更稳定高效
"""
import sys
import io
from datetime import datetime

# 修复Windows控制台编码问题（必须在导入其他模块之前）
if sys.platform == 'win32':
    try:
        # 检查是否已经被包装过
        if not isinstance(sys.stdout, io.TextIOWrapper) or sys.stdout.encoding != 'utf-8':
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        if not isinstance(sys.stderr, io.TextIOWrapper) or sys.stderr.encoding != 'utf-8':
            sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
    except (AttributeError, ValueError):
        # 如果重定向失败，忽略错误（可能是在非交互式环境中）
        pass

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.sync.sync_strategy import BetterSyncStrategy


def main():
    """主函数"""
    start_time = datetime.now()
    
    print("="*70)
    print("NewAPI 数据同步系统")
    print("="*70)
    print(f"开始时间: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*70)
    
    sync = None
    try:
        sync = BetterSyncStrategy()
        
        # 1. 同步日志数据（增量表，全量同步）
        print("\n" + "="*70)
        print("步骤 1/3: 同步日志数据（增量表）")
        print("="*70)
        logs_result = sync.sync_by_time_range()
        
        if logs_result is None:
            print("⚠️  日志数据同步未完成或出错")
        else:
            print(f"✅ 日志数据同步完成")
        
        # 2. 同步用户数据（快照表）
        print("\n" + "="*70)
        print("步骤 2/3: 同步用户数据（快照表）")
        print("="*70)
        try:
            sync._sync_users()
            print("✅ 用户数据同步完成")
        except Exception as e:
            print(f"❌ 用户数据同步出错: {e}")
        
        # 3. 同步渠道数据（快照表）
        print("\n" + "="*70)
        print("步骤 3/3: 同步渠道数据（快照表）")
        print("="*70)
        try:
            sync._sync_channels()
            print("✅ 渠道数据同步完成")
        except Exception as e:
            print(f"❌ 渠道数据同步出错: {e}")
        
        # 完成统计
        end_time = datetime.now()
        duration = end_time - start_time
        
        print("\n" + "="*70)
        print("所有数据同步完成！")
        print("="*70)
        print(f"开始时间: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"完成时间: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"总耗时: {duration}")
        print("="*70)
        
    except KeyboardInterrupt:
        print("\n\n⚠️  用户中断同步")
        print("已同步的数据已保存，下次运行将从中断位置继续")
    except Exception as e:
        print(f"\n\n❌ 同步过程出错: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if sync:
            sync.close()
            print("\n数据库连接已关闭")


if __name__ == "__main__":
    main()
