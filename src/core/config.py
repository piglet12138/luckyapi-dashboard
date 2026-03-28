"""
配置文件
集中管理API配置、数据库配置等
"""
import os
from typing import Optional

# API配置
BASE_URL = os.getenv("NEWAPI_BASE_URL", "https://luckyapi.chat")
TOKEN = os.getenv("NEWAPI_TOKEN", "ulQjFtL5uSycaNboJ+eoO/zxCi8Qpk/s")
USER_ID = os.getenv("NEWAPI_USER_ID", "103")

# 数据库配置
DB_PATH = os.getenv("NEWAPI_DB_PATH", "newapi_warehouse.db")

# 同步配置
SYNC_CONFIG = {
    "request_delay": 2.0,  # 请求延迟（秒）
    "max_page_size": 100,  # API实际限制：每页最多100条
    "batch_rest_interval": 10,  # 每N页休息一次
    "batch_rest_duration": 5,  # 每次休息时间（秒）
    "max_retries": 3,  # 最大重试次数
    "retry_delay": 10,  # 重试延迟（秒）
}

# 增量同步配置
INCREMENTAL_CONFIG = {
    "sync_hour": 2,  # 每日同步时间（小时）
    "sync_minute": 0,  # 每日同步时间（分钟）
    "lookback_days": 1,  # 回看天数（同步最近N天的数据）
}
