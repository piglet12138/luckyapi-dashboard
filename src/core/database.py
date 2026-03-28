"""
数据库操作模块
创建SQLite数据库和表结构
"""
import sqlite3
import json
from datetime import datetime
from typing import Optional
import os


class Database:
    """数据库操作类"""
    
    def __init__(self, db_path: str = "newapi_warehouse.db"):
        """
        初始化数据库连接
        
        Args:
            db_path: 数据库文件路径
        """
        self.db_path = db_path
        self.conn = None
    
    def connect(self):
        """连接数据库"""
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row  # 返回字典格式
        # 启用WAL模式，提高并发性能
        self.conn.execute("PRAGMA journal_mode = WAL")
        # 设置较小的缓存（16MB），适合2GB内存服务器
        self.conn.execute("PRAGMA cache_size = -16000")
        # 设置外键约束
        self.conn.execute("PRAGMA foreign_keys = ON")
        return self.conn
    
    def close(self):
        """关闭数据库连接"""
        if self.conn:
            self.conn.close()
    
    def execute(self, sql: str, params: tuple = None):
        """执行SQL语句"""
        cursor = self.conn.cursor()
        if params:
            cursor.execute(sql, params)
        else:
            cursor.execute(sql)
        self.conn.commit()
        return cursor
    
    def create_tables(self):
        """创建所有表结构"""
        print("="*70)
        print("创建数据库表结构...")
        print("="*70)

        # ODS层表
        self._create_ods_logs_table()
        self._create_ods_users_table()
        self._create_ods_channels_table()
        self._create_ods_groups_table()

        # 同步记录表
        self._create_sync_records_table()

        print("\n所有表创建完成！")

    def create_dwd_tables(self):
        """创建DWD层表结构（数据清洗层，脱敏数据）"""
        print("="*70)
        print("创建DWD层表结构...")
        print("="*70)

        self._create_dwd_logs_table()
        self._create_dwd_users_table()

        print("\nDWD层表创建完成！")

    def create_dws_tables(self):
        """创建DWS层表结构（数据汇总层）"""
        print("="*70)
        print("创建DWS层表结构...")
        print("="*70)

        self._create_dws_user_daily_table()
        self._create_dws_model_daily_table()
        self._create_dws_channel_daily_table()
        self._create_dws_user_lifecycle_table()

        print("\nDWS层表创建完成！")

    def create_ads_tables(self):
        """创建ADS层表结构（应用数据服务层）"""
        print("="*70)
        print("创建ADS层表结构...")
        print("="*70)

        self._create_ads_daily_summary_table()
        self._create_ads_funnel_daily_table()
        self._create_ads_user_segment_daily_table()
        self._create_ads_activation_analysis_table()
        self._create_ads_channel_attribution_table()
        self._create_ads_new_user_conversion_table()
        self._create_ads_repurchase_analysis_table()

        print("\nADS层表创建完成！")
    
    def _create_ods_logs_table(self):
        """创建ODS层日志表"""
        sql = """
        CREATE TABLE IF NOT EXISTS ods_logs (
            id BIGINT PRIMARY KEY,
            user_id INT,
            created_at BIGINT,
            type INT,
            content TEXT,
            username VARCHAR(255),
            token_name VARCHAR(255),
            model_name VARCHAR(255),
            quota BIGINT,
            prompt_tokens INT,
            completion_tokens INT,
            use_time INT,
            is_stream BOOLEAN,
            channel INT,
            channel_name VARCHAR(500),
            token_id INT,
            group_name VARCHAR(255),
            ip VARCHAR(50),
            request_id VARCHAR(100),
            other TEXT,
            sync_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            sync_date DATE DEFAULT (date('now'))
        );
        """
        self.execute(sql)
        
        # 创建索引
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_ods_logs_user_id ON ods_logs(user_id);",
            "CREATE INDEX IF NOT EXISTS idx_ods_logs_created_at ON ods_logs(created_at);",
            "CREATE INDEX IF NOT EXISTS idx_ods_logs_type ON ods_logs(type);",
            "CREATE INDEX IF NOT EXISTS idx_ods_logs_sync_date ON ods_logs(sync_date);",
            "CREATE INDEX IF NOT EXISTS idx_ods_logs_log_date ON ods_logs(date(datetime(created_at, 'unixepoch')));"
        ]
        for idx_sql in indexes:
            self.execute(idx_sql)
        
        print("[OK] 创建表: ods_logs")
    
    def _create_ods_users_table(self):
        """创建ODS层用户表（全量快照表）"""
        sql = """
        CREATE TABLE IF NOT EXISTS ods_users (
            id INT,
            username VARCHAR(255),
            display_name VARCHAR(255),
            role INT,
            status INT,
            email VARCHAR(255),
            quota BIGINT,
            used_quota BIGINT,
            request_count INT,
            group_name VARCHAR(255),
            aff_code VARCHAR(100),
            aff_count INT,
            inviter_id INT,
            sync_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            sync_date DATE DEFAULT (date('now')),
            PRIMARY KEY (id, sync_date)
        );
        """
        self.execute(sql)
        
        # 创建索引
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_ods_users_id ON ods_users(id);",
            "CREATE INDEX IF NOT EXISTS idx_ods_users_sync_date ON ods_users(sync_date);",
            "CREATE INDEX IF NOT EXISTS idx_ods_users_group_name ON ods_users(group_name);"
        ]
        for idx_sql in indexes:
            self.execute(idx_sql)
        
        print("[OK] 创建表: ods_users")
    
    def _create_ods_channels_table(self):
        """创建ODS层渠道表（全量快照表）"""
        sql = """
        CREATE TABLE IF NOT EXISTS ods_channels (
            id INT,
            name VARCHAR(255),
            type INT,
            status INT,
            group_name VARCHAR(255),
            weight INT,
            priority INT,
            balance BIGINT,
            balance_updated_time BIGINT,
            models TEXT,
            sync_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            sync_date DATE DEFAULT (date('now')),
            PRIMARY KEY (id, sync_date)
        );
        """
        self.execute(sql)
        
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_ods_channels_id ON ods_channels(id);",
            "CREATE INDEX IF NOT EXISTS idx_ods_channels_sync_date ON ods_channels(sync_date);"
        ]
        for idx_sql in indexes:
            self.execute(idx_sql)
        
        print("[OK] 创建表: ods_channels")
    
    def _create_ods_groups_table(self):
        """创建ODS层分组表（全量快照表）"""
        sql = """
        CREATE TABLE IF NOT EXISTS ods_groups (
            id INT PRIMARY KEY,
            name VARCHAR(255),
            sync_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            sync_date DATE DEFAULT (date('now'))
        );
        """
        self.execute(sql)
        
        print("[OK] 创建表: ods_groups")
    
    def _create_sync_records_table(self):
        """创建同步记录表"""
        sql = """
        CREATE TABLE IF NOT EXISTS sync_records (
            table_name VARCHAR(50) PRIMARY KEY,
            last_sync_time TIMESTAMP,
            last_max_created_at BIGINT,
            total_records INT DEFAULT 0,
            last_sync_date DATE,
            update_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
        self.execute(sql)
        
        print("[OK] 创建表: sync_records")

    def _create_dwd_logs_table(self):
        """创建DWD层日志明细表（脱敏后）"""
        sql = """
        CREATE TABLE IF NOT EXISTS dwd_logs (
            log_id BIGINT PRIMARY KEY,
            user_id INT NOT NULL,
            log_date DATE NOT NULL,
            log_datetime DATETIME NOT NULL,
            log_type INT NOT NULL,

            -- 脱敏后的字段
            username_masked VARCHAR(255),
            ip_masked VARCHAR(50),
            request_id_masked VARCHAR(100),

            -- 业务字段
            token_id INT,
            token_name VARCHAR(255),
            model_name VARCHAR(255),
            channel_id INT,
            channel_name VARCHAR(500),
            group_name VARCHAR(255),

            -- 消费相关字段（type=2时有效）
            quota BIGINT,
            prompt_tokens INT,
            completion_tokens INT,
            total_tokens INT,
            use_time INT,
            is_stream BOOLEAN,

            -- 充值相关字段（type=1时有效）
            topup_amount DECIMAL(10,2),

            -- 从other字段解析的扩展字段
            billing_source VARCHAR(50),
            cache_tokens INT,
            cache_ratio DECIMAL(5,4),
            model_ratio DECIMAL(5,2),
            group_ratio DECIMAL(5,2),

            -- 时间维度
            log_hour INT,
            log_weekday INT,
            log_week INT,
            log_month INT,
            log_year INT,

            -- 元数据
            etl_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
        self.execute(sql)

        # 创建索引
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_dwd_logs_user_id ON dwd_logs(user_id);",
            "CREATE INDEX IF NOT EXISTS idx_dwd_logs_log_date ON dwd_logs(log_date);",
            "CREATE INDEX IF NOT EXISTS idx_dwd_logs_log_type ON dwd_logs(log_type);",
            "CREATE INDEX IF NOT EXISTS idx_dwd_logs_model_name ON dwd_logs(model_name);",
            "CREATE INDEX IF NOT EXISTS idx_dwd_logs_channel_id ON dwd_logs(channel_id);",
            "CREATE INDEX IF NOT EXISTS idx_dwd_logs_log_year_month ON dwd_logs(log_year, log_month);"
        ]
        for idx_sql in indexes:
            self.execute(idx_sql)

        print("[OK] 创建表: dwd_logs（脱敏）")

    def _create_dwd_users_table(self):
        """创建DWD层用户明细表（脱敏后）"""
        sql = """
        CREATE TABLE IF NOT EXISTS dwd_users (
            user_id INT PRIMARY KEY,

            -- 脱敏后的字段
            username_masked VARCHAR(255),
            email_masked VARCHAR(255),
            display_name_masked VARCHAR(255),

            -- 业务字段
            role INT,
            status INT,
            group_name VARCHAR(255),

            -- 配额相关
            quota BIGINT,
            used_quota BIGINT,
            request_count INT,

            -- 推广相关
            aff_count INT,
            inviter_id INT,

            -- 时间字段
            first_use_date DATE,
            last_use_date DATE,

            -- 元数据
            etl_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            source_sync_date DATE
        );
        """
        self.execute(sql)

        # 创建索引
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_dwd_users_group_name ON dwd_users(group_name);",
            "CREATE INDEX IF NOT EXISTS idx_dwd_users_status ON dwd_users(status);",
            "CREATE INDEX IF NOT EXISTS idx_dwd_users_first_use_date ON dwd_users(first_use_date);"
        ]
        for idx_sql in indexes:
            self.execute(idx_sql)

        print("[OK] 创建表: dwd_users（脱敏）")

    def _create_dws_user_daily_table(self):
        """创建DWS层用户每日汇总表"""
        sql = """
        CREATE TABLE IF NOT EXISTS dws_user_daily (
            stat_date DATE NOT NULL,
            user_id INT NOT NULL,

            -- 使用统计
            call_count INT DEFAULT 0,
            total_quota BIGINT DEFAULT 0,
            total_prompt_tokens BIGINT DEFAULT 0,
            total_completion_tokens BIGINT DEFAULT 0,
            total_tokens BIGINT DEFAULT 0,
            total_use_time INT DEFAULT 0,

            -- 模型统计
            model_count INT DEFAULT 0,
            top_model VARCHAR(255),

            -- 渠道统计
            channel_count INT DEFAULT 0,
            top_channel_id INT,

            -- 元数据
            etl_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

            PRIMARY KEY (stat_date, user_id)
        );
        """
        self.execute(sql)

        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_dws_user_daily_stat_date ON dws_user_daily(stat_date);",
            "CREATE INDEX IF NOT EXISTS idx_dws_user_daily_user_id ON dws_user_daily(user_id);"
        ]
        for idx_sql in indexes:
            self.execute(idx_sql)

        print("[OK] 创建表: dws_user_daily")

    def _create_dws_model_daily_table(self):
        """创建DWS层模型每日汇总表"""
        sql = """
        CREATE TABLE IF NOT EXISTS dws_model_daily (
            stat_date DATE NOT NULL,
            model_name VARCHAR(255) NOT NULL,

            -- 使用统计
            call_count INT DEFAULT 0,
            user_count INT DEFAULT 0,
            total_quota BIGINT DEFAULT 0,
            total_tokens BIGINT DEFAULT 0,
            avg_tokens_per_call DECIMAL(10,2),
            avg_use_time DECIMAL(10,2),

            -- 元数据
            etl_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

            PRIMARY KEY (stat_date, model_name)
        );
        """
        self.execute(sql)

        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_dws_model_daily_stat_date ON dws_model_daily(stat_date);"
        ]
        for idx_sql in indexes:
            self.execute(idx_sql)

        print("[OK] 创建表: dws_model_daily")

    def _create_dws_channel_daily_table(self):
        """创建DWS层渠道每日汇总表"""
        sql = """
        CREATE TABLE IF NOT EXISTS dws_channel_daily (
            stat_date DATE NOT NULL,
            channel_id INT NOT NULL,
            channel_name VARCHAR(500),

            -- 使用统计
            call_count INT DEFAULT 0,
            user_count INT DEFAULT 0,
            total_quota BIGINT DEFAULT 0,
            avg_response_time DECIMAL(10,2),

            -- 元数据
            etl_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

            PRIMARY KEY (stat_date, channel_id)
        );
        """
        self.execute(sql)

        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_dws_channel_daily_stat_date ON dws_channel_daily(stat_date);"
        ]
        for idx_sql in indexes:
            self.execute(idx_sql)

        print("[OK] 创建表: dws_channel_daily")

    def _create_dws_user_lifecycle_table(self):
        """创建DWS层用户生命周期表"""
        sql = """
        CREATE TABLE IF NOT EXISTS dws_user_lifecycle (
            user_id INT PRIMARY KEY,

            -- 首次行为
            first_use_date DATE,
            first_model VARCHAR(255),
            first_channel_id INT,

            -- 最后行为
            last_use_date DATE,

            -- 累计统计
            total_call_count INT DEFAULT 0,
            total_quota BIGINT DEFAULT 0,
            total_topup_amount DECIMAL(10,2) DEFAULT 0,
            topup_count INT DEFAULT 0,

            -- 留存相关
            days_since_first INT,
            days_since_last INT,
            is_active_7d BOOLEAN DEFAULT FALSE,
            is_active_30d BOOLEAN DEFAULT FALSE,

            -- 用户分层
            user_segment VARCHAR(50),

            -- 元数据
            update_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
        self.execute(sql)

        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_dws_user_lifecycle_first_use_date ON dws_user_lifecycle(first_use_date);",
            "CREATE INDEX IF NOT EXISTS idx_dws_user_lifecycle_user_segment ON dws_user_lifecycle(user_segment);",
            "CREATE INDEX IF NOT EXISTS idx_dws_user_lifecycle_is_active_7d ON dws_user_lifecycle(is_active_7d);"
        ]
        for idx_sql in indexes:
            self.execute(idx_sql)

        print("[OK] 创建表: dws_user_lifecycle")

    def _create_ads_daily_summary_table(self):
        """创建ADS层每日汇总表"""
        sql = """
        CREATE TABLE IF NOT EXISTS ads_daily_summary (
            stat_date DATE PRIMARY KEY,

            -- 用户指标
            total_users INT DEFAULT 0,
            active_users INT DEFAULT 0,
            new_users INT DEFAULT 0,
            paying_users INT DEFAULT 0,

            -- 使用指标
            total_calls INT DEFAULT 0,
            total_quota BIGINT DEFAULT 0,
            total_tokens BIGINT DEFAULT 0,

            -- 财务指标
            total_revenue DECIMAL(10,2) DEFAULT 0,
            new_revenue DECIMAL(10,2) DEFAULT 0,
            arpu DECIMAL(10,2),
            arppu DECIMAL(10,2),

            -- 转化指标
            conversion_rate DECIMAL(5,2),
            activation_rate DECIMAL(5,2),

            -- 元数据
            update_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
        self.execute(sql)

        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_ads_daily_summary_stat_date ON ads_daily_summary(stat_date);"
        ]
        for idx_sql in indexes:
            self.execute(idx_sql)

        print("[OK] 创建表: ads_daily_summary")

    def _create_ads_funnel_daily_table(self):
        """创建ADS层增长漏斗每日表"""
        sql = """
        CREATE TABLE IF NOT EXISTS ads_funnel_daily (
            stat_date DATE PRIMARY KEY,

            -- 漏斗各层
            registered_users INT DEFAULT 0,
            active_users INT DEFAULT 0,
            retained_7d_users INT DEFAULT 0,
            paying_users INT DEFAULT 0,
            repurchase_users INT DEFAULT 0,

            -- 新用户激活
            new_users INT DEFAULT 0,
            activated_new_users INT DEFAULT 0,

            -- 转化率
            activation_rate DECIMAL(5,2),
            retention_rate DECIMAL(5,2),
            d3_retention_rate DECIMAL(5,2),
            conversion_rate DECIMAL(5,2),
            repurchase_rate DECIMAL(5,2),

            -- 元数据
            update_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
        self.execute(sql)

        print("[OK] 创建表: ads_funnel_daily")

    def _create_ads_user_segment_daily_table(self):
        """创建ADS层用户分层每日表"""
        sql = """
        CREATE TABLE IF NOT EXISTS ads_user_segment_daily (
            stat_date DATE NOT NULL,
            segment VARCHAR(50) NOT NULL,

            user_count INT DEFAULT 0,
            total_calls INT DEFAULT 0,
            avg_calls_per_user DECIMAL(10,2),
            total_quota BIGINT DEFAULT 0,
            total_revenue DECIMAL(10,2) DEFAULT 0,

            -- 元数据
            update_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

            PRIMARY KEY (stat_date, segment)
        );
        """
        self.execute(sql)

        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_ads_user_segment_daily_stat_date ON ads_user_segment_daily(stat_date);"
        ]
        for idx_sql in indexes:
            self.execute(idx_sql)

        print("[OK] 创建表: ads_user_segment_daily")

    def _create_ads_activation_analysis_table(self):
        """创建ADS层激活点分析表"""
        sql = """
        CREATE TABLE IF NOT EXISTS ads_activation_analysis (
            stat_date DATE NOT NULL,
            call_range VARCHAR(20) NOT NULL,

            user_count INT DEFAULT 0,
            paying_user_count INT DEFAULT 0,
            conversion_rate DECIMAL(5,2),
            avg_revenue_per_user DECIMAL(10,2),

            -- 元数据
            update_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

            PRIMARY KEY (stat_date, call_range)
        );
        """
        self.execute(sql)

        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_ads_activation_analysis_stat_date ON ads_activation_analysis(stat_date);"
        ]
        for idx_sql in indexes:
            self.execute(idx_sql)

        print("[OK] 创建表: ads_activation_analysis")

    def _create_ads_channel_attribution_table(self):
        """创建ADS层渠道归因表"""
        sql = """
        CREATE TABLE IF NOT EXISTS ads_channel_attribution (
            stat_date DATE NOT NULL,
            first_model VARCHAR(255) NOT NULL,

            new_user_count INT DEFAULT 0,
            paying_user_count INT DEFAULT 0,
            total_revenue DECIMAL(10,2) DEFAULT 0,
            conversion_rate DECIMAL(5,2),
            arppu DECIMAL(10,2),

            -- 元数据
            update_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

            PRIMARY KEY (stat_date, first_model)
        );
        """
        self.execute(sql)

        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_ads_channel_attribution_stat_date ON ads_channel_attribution(stat_date);"
        ]
        for idx_sql in indexes:
            self.execute(idx_sql)

        print("[OK] 创建表: ads_channel_attribution")

    def _create_ads_new_user_conversion_table(self):
        """创建ADS层新用户转化率表"""
        sql = """
        CREATE TABLE IF NOT EXISTS ads_new_user_conversion (
            cohort_date TEXT PRIMARY KEY,  -- 新用户首次使用日期
            new_users INTEGER DEFAULT 0,              -- 新增用户数
            d0_paying_users INTEGER DEFAULT 0,        -- 当日付费用户数
            d3_paying_users INTEGER DEFAULT 0,        -- 3日内付费用户数
            d7_paying_users INTEGER DEFAULT 0,        -- 7日内付费用户数
            d30_paying_users INTEGER DEFAULT 0,       -- 30日内付费用户数
            d0_conversion_rate REAL,        -- 当日转化率
            d3_conversion_rate REAL,        -- 3日转化率
            d7_conversion_rate REAL,        -- 7日转化率
            d30_conversion_rate REAL,       -- 30日转化率

            -- 元数据
            update_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
        self.execute(sql)

        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_ads_new_user_conversion_cohort_date ON ads_new_user_conversion(cohort_date);"
        ]
        for idx_sql in indexes:
            self.execute(idx_sql)

        print("[OK] 创建表: ads_new_user_conversion")

    def _create_ads_repurchase_analysis_table(self):
        """创建ADS层分层复购率分析表"""
        sql = """
        CREATE TABLE IF NOT EXISTS ads_repurchase_analysis (
            stat_date TEXT PRIMARY KEY,
            total_paying_users INTEGER DEFAULT 0,      -- 累计付费用户数
            single_purchase_users INTEGER DEFAULT 0,   -- 单次充值用户（1次）
            low_frequency_users INTEGER DEFAULT 0,     -- 低频复购用户（2-5次）
            mid_frequency_users INTEGER DEFAULT 0,     -- 中频复购用户（6-20次）
            high_frequency_users INTEGER DEFAULT 0,    -- 高频复购用户（>20次）
            single_purchase_rate REAL,                 -- 单次充值率
            low_frequency_rate REAL,                   -- 低频复购率
            mid_frequency_rate REAL,                   -- 中频复购率
            high_frequency_rate REAL,                  -- 高频复购率
            overall_repurchase_rate REAL,              -- 整体复购率（≥2次）

            -- 元数据
            update_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
        self.execute(sql)

        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_ads_repurchase_analysis_stat_date ON ads_repurchase_analysis(stat_date);"
        ]
        for idx_sql in indexes:
            self.execute(idx_sql)

        print("[OK] 创建表: ads_repurchase_analysis")

    def get_last_sync_info(self, table_name: str) -> Optional[dict]:
        """获取上次同步信息"""
        sql = "SELECT * FROM sync_records WHERE table_name = ?"
        cursor = self.execute(sql, (table_name,))
        row = cursor.fetchone()
        if row:
            return dict(row)
        return None
    
    def update_sync_record(self, table_name: str, last_max_created_at: int = None, 
                          total_records: int = None):
        """更新同步记录"""
        existing = self.get_last_sync_info(table_name)
        
        if existing:
            # 更新现有记录
            updates = ["update_time = CURRENT_TIMESTAMP"]
            params = []
            
            if last_max_created_at is not None:
                updates.append("last_max_created_at = ?")
                params.append(last_max_created_at)
            
            if total_records is not None:
                updates.append("total_records = total_records + ?")
                params.append(total_records)
            
            updates.append("last_sync_date = date('now')")
            params.append(table_name)
            
            sql = f"UPDATE sync_records SET {', '.join(updates)} WHERE table_name = ?"
            self.execute(sql, tuple(params))
        else:
            # 插入新记录
            sql = """
            INSERT INTO sync_records 
            (table_name, last_max_created_at, total_records, last_sync_date)
            VALUES (?, ?, ?, date('now'))
            """
            self.execute(sql, (table_name, last_max_created_at or 0, total_records or 0))


if __name__ == "__main__":
    # 创建数据库和表
    db = Database()
    db.connect()
    db.create_tables()
    db.close()
    print("\n数据库初始化完成！")
