"""
数据脱敏工具模块
用于对敏感信息进行脱敏处理
"""
import hashlib
import re
from typing import Optional


def mask_username(username: Optional[str], user_id: int) -> str:
    """
    用户名脱敏

    Args:
        username: 原始用户名
        user_id: 用户ID

    Returns:
        脱敏后的用户名，格式：user_{user_id}

    Examples:
        >>> mask_username("stone.liu", 1007)
        'user_1007'
    """
    if not username:
        return f"user_{user_id}"
    return f"user_{user_id}"


def mask_email(email: Optional[str], user_id: int) -> str:
    """
    邮箱脱敏
    保留邮箱域名，脱敏用户名部分

    Args:
        email: 原始邮箱
        user_id: 用户ID

    Returns:
        脱敏后的邮箱，格式：user_{user_id}@domain.com

    Examples:
        >>> mask_email("freelz940219@gmail.com", 1007)
        'user_1007@gmail.com'
    """
    if not email or '@' not in email:
        return f"user_{user_id}@unknown.com"

    domain = email.split('@')[1]
    return f"user_{user_id}@{domain}"


def mask_ip(ip: Optional[str]) -> str:
    """
    IP地址脱敏
    保留前两段，脱敏后两段

    Args:
        ip: 原始IP地址

    Returns:
        脱敏后的IP地址，格式：xxx.xxx.*.*

    Examples:
        >>> mask_ip("192.168.1.100")
        '192.168.*.*'
    """
    if not ip:
        return None

    parts = ip.split('.')
    if len(parts) == 4:
        return f"{parts[0]}.{parts[1]}.*.*"

    return ip


def mask_request_id(request_id: Optional[str]) -> str:
    """
    请求ID脱敏
    保留前8位，脱敏后续字符

    Args:
        request_id: 原始请求ID

    Returns:
        脱敏后的请求ID

    Examples:
        >>> mask_request_id("20260313124013176119058vznGNpIL")
        '20260313************************'
    """
    if not request_id or len(request_id) < 8:
        return request_id

    return request_id[:8] + "*" * (len(request_id) - 8)


def hash_sensitive_field(value: Optional[str]) -> str:
    """
    对敏感字段进行哈希处理
    使用MD5哈希，取前8位

    Args:
        value: 原始值

    Returns:
        哈希后的值

    Examples:
        >>> hash_sensitive_field("sensitive_data")
        'a1b2c3d4'
    """
    if not value:
        return None

    return hashlib.md5(value.encode()).hexdigest()[:8]


# 测试函数
if __name__ == "__main__":
    print("=== 数据脱敏工具测试 ===\n")

    # 测试用户名脱敏
    print("1. 用户名脱敏:")
    print(f"   原始: stone.liu -> 脱敏: {mask_username('stone.liu', 1007)}")
    print(f"   原始: None -> 脱敏: {mask_username(None, 1007)}\n")

    # 测试邮箱脱敏
    print("2. 邮箱脱敏:")
    print(f"   原始: freelz940219@gmail.com -> 脱敏: {mask_email('freelz940219@gmail.com', 1007)}")
    print(f"   原始: None -> 脱敏: {mask_email(None, 1007)}\n")

    # 测试IP脱敏
    print("3. IP地址脱敏:")
    print(f"   原始: 192.168.1.100 -> 脱敏: {mask_ip('192.168.1.100')}")
    print(f"   原始: None -> 脱敏: {mask_ip(None)}\n")

    # 测试请求ID脱敏
    print("4. 请求ID脱敏:")
    print(f"   原始: 20260313124013176119058vznGNpIL -> 脱敏: {mask_request_id('20260313124013176119058vznGNpIL')}\n")

    # 测试哈希
    print("5. 哈希处理:")
    print(f"   原始: sensitive_data -> 哈希: {hash_sensitive_field('sensitive_data')}")
