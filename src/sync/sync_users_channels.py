"""
仅同步用户和渠道数据
快速同步，不涉及日志数据
"""
import sys
import io
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.sync.sync_strategy import BetterSyncStrategy
from datetime import datetime

# 修复Windows控制台编码问题
if sys.platform == 'win32':
    try:
        if not isinstance(sys.stdout, io.TextIOWrapper) or sys.stdout.encoding != 'utf-8':
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        if not isinstance(sys.stderr, io.TextIOWrapper) or sys.stderr.encoding != 'utf-8':
            sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
    except Exception as e:
        print(f"Warning: Failed to set UTF-8 encoding for console: {e}", file=sys.stderr)


def main():
    start_time = datetime.now()
    print("="*70)
    print("用户和渠道数据同步")
    print("="*70)
    print(f"开始时间: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*70)
    
    sync = None
    try:
        sync = BetterSyncStrategy()
        
        # 1. 同步用户数据（快照表）
        print("\n" + "="*70)
        print("步骤 1/2: 同步用户数据（快照表）")
        print("="*70)
        try:
            sync._sync_users()
            print("✅ 用户数据同步完成")
        except Exception as e:
            print(f"❌ 用户数据同步出错: {e}")
            import traceback
            traceback.print_exc()
        
        # 2. 同步渠道数据（快照表）
        print("\n" + "="*70)
        print("步骤 2/2: 同步渠道数据（快照表）")
        print("="*70)
        try:
            sync._sync_channels()
            print("✅ 渠道数据同步完成")
        except Exception as e:
            print(f"❌ 渠道数据同步出错: {e}")
            import traceback
            traceback.print_exc()
        
        # 完成统计
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        print("\n" + "="*70)
        print("同步完成")
        print("="*70)
        print(f"结束时间: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"总耗时: {duration:.1f}秒 ({duration/60:.1f}分钟)")
        print("="*70)
        
    except KeyboardInterrupt:
        print("\n\n⚠️  用户中断同步")
        print("已同步的数据已保存")
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
