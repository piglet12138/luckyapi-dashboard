"""
ODS层到DWD层的数据转换
实现数据清洗和脱敏
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from datetime import datetime
import json
import re
from src.core.database import Database
from src.core.data_masking import mask_username, mask_email, mask_ip, mask_request_id
from src.core.utils import extract_topup_amount, parse_other_field


class ODSToDWD:
    """ODS层到DWD层的ETL转换"""

    def __init__(self, db_path: str = "newapi_warehouse.db"):
        self.db = Database(db_path)
        self.db.connect()

    def transform_logs(self, batch_size: int = 5000):
        """
        转换日志数据：ODS -> DWD
        实现数据清洗和脱敏

        Args:
            batch_size: 批量处理大小
        """
        print("="*70)
        print("开始转换日志数据：ODS -> DWD")
        print("="*70)

        # 获取ODS层数据总数
        cursor = self.db.execute("SELECT COUNT(*) as cnt FROM ods_logs")
        total = cursor.fetchone()['cnt']
        print(f"ODS层日志总数: {total:,} 条")

        # 检查DWD层已有数据
        cursor = self.db.execute("SELECT COUNT(*) as cnt FROM dwd_logs")
        existing = cursor.fetchone()['cnt']
        print(f"DWD层已有数据: {existing:,} 条")

        if existing > 0:
            print(f"\n[!] DWD层已有数据，将进行增量转换...")
            # 获取DWD层最大ID
            cursor = self.db.execute("SELECT MAX(log_id) as max_id FROM dwd_logs")
            max_id = cursor.fetchone()['max_id'] or 0
            print(f"DWD层最大ID: {max_id}")
        else:
            max_id = 0
            print(f"\n开始全量转换...")

        # 分批处理
        processed = 0
        offset = max_id

        while True:
            # 读取一批ODS数据
            sql = f"""
            SELECT * FROM ods_logs
            WHERE id > ?
            ORDER BY id
            LIMIT {batch_size}
            """
            cursor = self.db.execute(sql, (offset,))
            rows = cursor.fetchall()

            if not rows:
                break

            # 转换并插入DWD层
            dwd_records = []
            for row in rows:
                dwd_record = self._transform_log_record(dict(row))
                dwd_records.append(dwd_record)

            # 批量插入
            self._batch_insert_logs(dwd_records)

            processed += len(rows)
            offset = rows[-1]['id']
            print(f"已处理: {processed:,} / {total:,} ({processed/total*100:.1f}%)")

        print(f"\n[OK] 日志数据转换完成！共转换 {processed:,} 条记录")

    def _transform_log_record(self, ods_record: dict) -> dict:
        """
        转换单条日志记录

        Args:
            ods_record: ODS层记录

        Returns:
            DWD层记录
        """
        # 时间戳转换
        created_at = ods_record['created_at']
        log_datetime = datetime.fromtimestamp(created_at)
        log_date = log_datetime.date()

        # 脱敏处理
        username_masked = mask_username(ods_record.get('username'), ods_record['user_id'])
        ip_masked = mask_ip(ods_record.get('ip'))
        request_id_masked = mask_request_id(ods_record.get('request_id'))

        # 解析other字段
        other_data = parse_other_field(ods_record.get('other'))

        # 提取充值金额（type=1时）
        topup_amount = None
        if ods_record['type'] == 1:
            topup_amount = extract_topup_amount(ods_record.get('content', ''))

        # 计算total_tokens
        prompt_tokens = ods_record.get('prompt_tokens') or 0
        completion_tokens = ods_record.get('completion_tokens') or 0
        total_tokens = prompt_tokens + completion_tokens

        # 构建DWD记录
        dwd_record = {
            'log_id': ods_record['id'],
            'user_id': ods_record['user_id'],
            'log_date': log_date,
            'log_datetime': log_datetime,
            'log_type': ods_record['type'],

            # 脱敏字段
            'username_masked': username_masked,
            'ip_masked': ip_masked,
            'request_id_masked': request_id_masked,

            # 业务字段
            'token_id': ods_record.get('token_id'),
            'token_name': ods_record.get('token_name'),
            'model_name': ods_record.get('model_name'),
            'channel_id': ods_record.get('channel'),
            'channel_name': ods_record.get('channel_name'),
            'group_name': ods_record.get('group_name'),

            # 消费字段
            'quota': ods_record.get('quota'),
            'prompt_tokens': prompt_tokens,
            'completion_tokens': completion_tokens,
            'total_tokens': total_tokens,
            'use_time': ods_record.get('use_time'),
            'is_stream': ods_record.get('is_stream'),

            # 充值字段
            'topup_amount': topup_amount,

            # 扩展字段
            'billing_source': other_data.get('billing_source'),
            'cache_tokens': other_data.get('cache_tokens'),
            'cache_ratio': other_data.get('cache_ratio'),
            'model_ratio': other_data.get('model_ratio'),
            'group_ratio': other_data.get('group_ratio'),

            # 时间维度
            'log_hour': log_datetime.hour,
            'log_weekday': log_datetime.weekday(),
            'log_week': log_datetime.isocalendar()[1],
            'log_month': log_datetime.month,
            'log_year': log_datetime.year,
        }

        return dwd_record

    def _batch_insert_logs(self, records: list):
        """批量插入日志到DWD层"""
        if not records:
            return

        sql = """
        INSERT OR IGNORE INTO dwd_logs (
            log_id, user_id, log_date, log_datetime, log_type,
            username_masked, ip_masked, request_id_masked,
            token_id, token_name, model_name, channel_id, channel_name, group_name,
            quota, prompt_tokens, completion_tokens, total_tokens, use_time, is_stream,
            topup_amount,
            billing_source, cache_tokens, cache_ratio, model_ratio, group_ratio,
            log_hour, log_weekday, log_week, log_month, log_year
        ) VALUES (
            ?, ?, ?, ?, ?,
            ?, ?, ?,
            ?, ?, ?, ?, ?, ?,
            ?, ?, ?, ?, ?, ?,
            ?,
            ?, ?, ?, ?, ?,
            ?, ?, ?, ?, ?
        )
        """

        cursor = self.db.conn.cursor()
        for record in records:
            params = (
                record['log_id'], record['user_id'], record['log_date'],
                record['log_datetime'], record['log_type'],
                record['username_masked'], record['ip_masked'], record['request_id_masked'],
                record['token_id'], record['token_name'], record['model_name'],
                record['channel_id'], record['channel_name'], record['group_name'],
                record['quota'], record['prompt_tokens'], record['completion_tokens'],
                record['total_tokens'], record['use_time'], record['is_stream'],
                record['topup_amount'],
                record['billing_source'], record['cache_tokens'], record['cache_ratio'],
                record['model_ratio'], record['group_ratio'],
                record['log_hour'], record['log_weekday'], record['log_week'],
                record['log_month'], record['log_year']
            )
            cursor.execute(sql, params)

        self.db.conn.commit()

    def transform_users(self):
        """
        转换用户数据：ODS -> DWD
        实现数据清洗和脱敏
        """
        print("="*70)
        print("开始转换用户数据：ODS -> DWD")
        print("="*70)

        # 获取最新快照日期的用户数据
        cursor = self.db.execute("""
            SELECT MAX(sync_date) as latest_date FROM ods_users
        """)
        latest_date = cursor.fetchone()['latest_date']
        print(f"最新快照日期: {latest_date}")

        # 读取最新快照的用户数据
        cursor = self.db.execute("""
            SELECT * FROM ods_users WHERE sync_date = ?
        """, (latest_date,))
        users = cursor.fetchall()
        print(f"用户总数: {len(users):,} 个")

        # 计算用户的首次和最后使用日期（从dwd_logs）
        print("\n计算用户使用时间...")
        cursor = self.db.execute("""
            SELECT
                user_id,
                MIN(log_date) as first_use_date,
                MAX(log_date) as last_use_date
            FROM dwd_logs
            WHERE log_type = 2
            GROUP BY user_id
        """)
        user_dates = {row['user_id']: dict(row) for row in cursor.fetchall()}

        # 转换并插入DWD层
        dwd_records = []
        for user in users:
            user_dict = dict(user)
            user_id = user_dict['id']

            # 脱敏处理
            username_masked = mask_username(user_dict.get('username'), user_id)
            email_masked = mask_email(user_dict.get('email'), user_id)
            display_name_masked = mask_username(user_dict.get('display_name'), user_id)

            # 获取使用时间
            dates = user_dates.get(user_id, {})

            dwd_record = {
                'user_id': user_id,
                'username_masked': username_masked,
                'email_masked': email_masked,
                'display_name_masked': display_name_masked,
                'role': user_dict.get('role'),
                'status': user_dict.get('status'),
                'group_name': user_dict.get('group_name'),
                'quota': user_dict.get('quota'),
                'used_quota': user_dict.get('used_quota'),
                'request_count': user_dict.get('request_count'),
                'aff_count': user_dict.get('aff_count'),
                'inviter_id': user_dict.get('inviter_id'),
                'first_use_date': dates.get('first_use_date'),
                'last_use_date': dates.get('last_use_date'),
                'source_sync_date': latest_date
            }
            dwd_records.append(dwd_record)

        # 批量插入
        self._batch_insert_users(dwd_records)

        print(f"\n[OK] 用户数据转换完成！共转换 {len(dwd_records):,} 个用户")

    def _batch_insert_users(self, records: list):
        """批量插入用户到DWD层"""
        if not records:
            return

        sql = """
        INSERT OR REPLACE INTO dwd_users (
            user_id, username_masked, email_masked, display_name_masked,
            role, status, group_name,
            quota, used_quota, request_count,
            aff_count, inviter_id,
            first_use_date, last_use_date,
            source_sync_date
        ) VALUES (
            ?, ?, ?, ?,
            ?, ?, ?,
            ?, ?, ?,
            ?, ?,
            ?, ?,
            ?
        )
        """

        cursor = self.db.conn.cursor()
        for record in records:
            params = (
                record['user_id'], record['username_masked'], record['email_masked'],
                record['display_name_masked'],
                record['role'], record['status'], record['group_name'],
                record['quota'], record['used_quota'], record['request_count'],
                record['aff_count'], record['inviter_id'],
                record['first_use_date'], record['last_use_date'],
                record['source_sync_date']
            )
            cursor.execute(sql, params)

        self.db.conn.commit()

    def run_full_transform(self):
        """运行完整的ODS->DWD转换"""
        print("\n" + "="*70)
        print("开始ODS->DWD完整转换流程")
        print("="*70 + "\n")

        # 1. 转换日志数据
        self.transform_logs()

        print("\n")

        # 2. 转换用户数据
        self.transform_users()

        print("\n" + "="*70)
        print("[OK] ODS->DWD转换完成！")
        print("="*70)

        # 统计信息
        self._print_statistics()

    def _print_statistics(self):
        """打印统计信息"""
        print("\n" + "="*70)
        print("DWD层数据统计")
        print("="*70)

        # 日志统计
        cursor = self.db.execute("SELECT COUNT(*) as cnt FROM dwd_logs")
        log_count = cursor.fetchone()['cnt']
        print(f"日志记录数: {log_count:,} 条")

        # 用户统计
        cursor = self.db.execute("SELECT COUNT(*) as cnt FROM dwd_users")
        user_count = cursor.fetchone()['cnt']
        print(f"用户数: {user_count:,} 个")

        # 日志类型分布
        cursor = self.db.execute("""
            SELECT
                log_type,
                COUNT(*) as cnt,
                ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM dwd_logs), 2) as pct
            FROM dwd_logs
            GROUP BY log_type
            ORDER BY log_type
        """)
        print("\n日志类型分布:")
        type_names = {1: '充值', 2: '消费', 3: '管理', 4: '错误', 5: '系统'}
        for row in cursor.fetchall():
            type_name = type_names.get(row['log_type'], '未知')
            print(f"  {type_name}(type={row['log_type']}): {row['cnt']:,} 条 ({row['pct']}%)")

        # 时间范围
        cursor = self.db.execute("""
            SELECT
                MIN(log_date) as min_date,
                MAX(log_date) as max_date
            FROM dwd_logs
        """)
        row = cursor.fetchone()
        print(f"\n时间范围: {row['min_date']} ~ {row['max_date']}")

        print("="*70)

    def close(self):
        """关闭数据库连接"""
        self.db.close()


if __name__ == "__main__":
    # 运行ETL转换
    etl = ODSToDWD()

    try:
        etl.run_full_transform()
    finally:
        etl.close()

    print("\n[OK] 所有转换完成！")
