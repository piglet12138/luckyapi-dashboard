"""
工具函数模块
包含数据清洗、转换等工具函数
"""
import re
from datetime import datetime
from typing import Optional, Dict, Any
import json


def extract_topup_amount(content: str) -> float:
    """
    从content字段提取充值金额
    
    Args:
        content: 充值日志的content字段
        
    Returns:
        充值金额（浮点数），如果提取失败返回0.0
        
    示例:
        "通过兑换码充值 ＄575.000000 额度，兑换码ID 603" -> 575.0
        "使用在线充值成功，充值金额: ＄10.000000 额度，支付金额：10.000000" -> 10.0
    """
    if not content:
        return 0.0
    
    # 匹配货币符号后的数字（支持美元、人民币）
    # 优先匹配"充值金额:"后面的金额
    patterns = [
        r'充值金额:\s*[＄$¥￥](\d+\.?\d*)',  # 充值金额: ¥10.000000
        r'[＄$¥￥](\d+\.?\d*)',  # ＄575.000000 或 ¥575.000000
    ]
    
    for pattern in patterns:
        match = re.search(pattern, content)
        if match:
            try:
                return float(match.group(1))
            except ValueError:
                continue
    
    return 0.0


def parse_other_field(other_str: str) -> Dict[str, Any]:
    """
    解析other字段（JSON字符串）
    
    Args:
        other_str: other字段的JSON字符串
        
    Returns:
        解析后的字典，如果解析失败返回空字典
    """
    if not other_str:
        return {}
    
    try:
        return json.loads(other_str)
    except (json.JSONDecodeError, TypeError):
        return {}


def timestamp_to_datetime(timestamp: int) -> datetime:
    """
    将Unix时间戳（秒）转换为datetime对象
    
    Args:
        timestamp: Unix时间戳（秒）
        
    Returns:
        datetime对象
    """
    return datetime.fromtimestamp(timestamp)


def timestamp_to_date(timestamp: int) -> str:
    """
    将Unix时间戳（秒）转换为日期字符串（YYYY-MM-DD）
    
    Args:
        timestamp: Unix时间戳（秒）
        
    Returns:
        日期字符串
    """
    dt = timestamp_to_datetime(timestamp)
    return dt.strftime('%Y-%m-%d')


def get_time_dimensions(timestamp: int) -> Dict[str, int]:
    """
    获取时间维度字段
    
    Args:
        timestamp: Unix时间戳（秒）
        
    Returns:
        包含时间维度的字典
    """
    dt = timestamp_to_datetime(timestamp)
    
    return {
        'log_hour': dt.hour,
        'log_weekday': dt.weekday(),  # 0=Monday, 6=Sunday
        'log_week': dt.isocalendar()[1],  # ISO周数
        'log_month': dt.month,
    }


def clean_model_name(model_name: str) -> str:
    """
    清洗模型名称
    
    Args:
        model_name: 原始模型名称
        
    Returns:
        清洗后的模型名称
    """
    if not model_name:
        return ""
    
    # 移除前缀，如"(按次)"等
    model_name = re.sub(r'^\([^)]+\)', '', model_name).strip()
    
    return model_name


def batch_insert(cursor, table: str, records: list, batch_size: int = 1000):
    """
    批量插入数据
    
    Args:
        cursor: 数据库游标
        table: 表名
        records: 记录列表
        batch_size: 每批大小
    """
    if not records:
        return
    
    # 获取字段名
    if isinstance(records[0], dict):
        fields = list(records[0].keys())
    else:
        raise ValueError("records must be a list of dictionaries")
    
    # 构建插入SQL
    placeholders = ', '.join(['?' for _ in fields])
    fields_str = ', '.join(fields)
    sql = f"INSERT OR IGNORE INTO {table} ({fields_str}) VALUES ({placeholders})"
    
    # 分批插入
    for i in range(0, len(records), batch_size):
        batch = records[i:i + batch_size]
        values = [tuple(record.get(field) for field in fields) for record in batch]
        cursor.executemany(sql, values)


if __name__ == "__main__":
    # 测试充值金额提取
    test_cases = [
        "通过兑换码充值 ＄575.000000 额度，兑换码ID 603",
        "使用在线充值成功，充值金额: ＄10.000000 额度，支付金额：10.000000",
        "通过兑换码充值 ＄5.000000 额度，兑换码ID 794",
    ]
    
    print("测试充值金额提取:")
    for content in test_cases:
        amount = extract_topup_amount(content)
        print(f"  '{content}' -> {amount}")
