"""
NewAPI Management API Client
用于测试和获取NewAPI管理接口数据
"""
import requests
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import time


class NewAPIClient:
    """NewAPI管理接口客户端"""
    
    def __init__(self, base_url: str, token: str):
        """
        初始化API客户端
        
        Args:
            base_url: API服务器地址，如 https://luckyapi.chat
            token: 管理员Token
        """
        self.base_url = base_url.rstrip('/')
        self.token = token
        self.user_id = None  # 将在设置后更新
        self.session = requests.Session()
        self._update_headers()
    
    def set_user_id(self, user_id: str):
        """设置用户ID（用于New-Api-User头）"""
        self.user_id = str(user_id)
        self._update_headers()
    
    def _update_headers(self):
        """更新请求头"""
        headers = {
            'Authorization': f'Bearer {self.token}',
            'Content-Type': 'application/json'
        }
        if self.user_id:
            headers['New-Api-User'] = self.user_id
        self.session.headers.update(headers)
    
    def _request(self, method: str, endpoint: str, params: Optional[Dict] = None, 
                 data: Optional[Dict] = None) -> Dict[str, Any]:
        """
        发送HTTP请求
        
        Args:
            method: HTTP方法 (GET, POST, etc.)
            endpoint: API端点路径，如 '/api/log/'
            params: URL查询参数
            data: 请求体数据
            
        Returns:
            API响应数据（JSON格式）
        """
        url = f"{self.base_url}{endpoint}"
        
        try:
            if method.upper() == 'GET':
                response = self.session.get(url, params=params, timeout=60)  # 增加超时时间到60秒
            elif method.upper() == 'POST':
                response = self.session.post(url, params=params, json=data, timeout=60)
            elif method.upper() == 'DELETE':
                response = self.session.delete(url, params=params, timeout=60)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
            
            response.raise_for_status()
            
            # 尝试解析JSON，如果失败返回文本
            try:
                return response.json()
            except json.JSONDecodeError:
                return {"raw_text": response.text, "status_code": response.status_code}
                
        except requests.exceptions.RequestException as e:
            return {
                "error": True,
                "message": str(e),
                "status_code": getattr(e.response, 'status_code', None) if hasattr(e, 'response') else None
            }
    
    def get_logs(self, page: int = 1, page_size: int = 100, 
                 start_time: Optional[int] = None, 
                 end_time: Optional[int] = None,
                 user_id: Optional[int] = None,
                 token_id: Optional[int] = None,
                 model_name: Optional[str] = None,
                 type: Optional[str] = None) -> Dict[str, Any]:
        """
        获取日志数据
        
        Args:
            page: 页码
            page_size: 每页大小
            start_time: 开始时间戳（秒）
            end_time: 结束时间戳（秒）
            user_id: 用户ID过滤
            token_id: Token ID过滤
            model_name: 模型名称过滤
            type: 日志类型过滤 (consumption, topup, management, error, system)
            
        Returns:
            日志数据
        """
        params = {
            'p': page,
            'page_size': page_size
        }
        
        if start_time:
            params['start_time'] = start_time
        if end_time:
            params['end_time'] = end_time
        if user_id:
            params['user_id'] = user_id
        if token_id:
            params['token_id'] = token_id
        if model_name:
            params['model_name'] = model_name
        if type:
            params['type'] = type
            
        return self._request('GET', '/api/log/', params=params)
    
    def get_all_logs_paginated(self, start_date: Optional[datetime] = None,
                               end_date: Optional[datetime] = None,
                               max_pages: Optional[int] = None) -> List[Dict]:
        """
        分页获取所有日志数据
        
        Args:
            start_date: 开始日期
            end_date: 结束日期
            max_pages: 最大页数限制（None表示获取全部）
            
        Returns:
            所有日志记录列表
        """
        all_logs = []
        page = 1
        page_size = 500  # 使用较大的页面大小
        
        start_ts = int(start_date.timestamp()) if start_date else None
        end_ts = int(end_date.timestamp()) if end_date else None
        
        while True:
            if max_pages and page > max_pages:
                break
                
            print(f"正在获取第 {page} 页日志...")
            response = self.get_logs(page=page, page_size=page_size,
                                    start_time=start_ts, end_time=end_ts)
            
            if response.get('error'):
                print(f"错误: {response.get('message')}")
                break
            
            # 根据实际API响应结构调整
            data = response.get('data', {})
            if isinstance(data, dict):
                logs = data.get('items', []) or []
            else:
                logs = response.get('data', []) or response.get('logs', []) or []
            
            if not logs:
                break
                
            all_logs.extend(logs)
            print(f"  获取到 {len(logs)} 条记录，累计 {len(all_logs)} 条")
            
            # 检查是否还有更多数据
            if len(logs) < page_size:
                break
                
            page += 1
            time.sleep(0.5)  # 避免请求过快
        
        return all_logs
    
    def test_connection(self) -> Dict[str, Any]:
        """
        测试API连接和认证
        
        Returns:
            连接测试结果
        """
        print("=" * 50)
        print("测试API连接...")
        print(f"服务器: {self.base_url}")
        print(f"Token: {self.token[:20]}...")
        print("=" * 50)
        
        # 尝试获取第一页日志
        response = self.get_logs(page=1, page_size=1)
        
        if response.get('error'):
            return {
                "success": False,
                "error": response.get('message'),
                "status_code": response.get('status_code')
            }
        
        return {
            "success": True,
            "response_sample": response,
            "message": "API连接成功！"
        }
    
    def get_users(self, page: int = 1, page_size: int = 100) -> Dict[str, Any]:
        """获取用户列表"""
        params = {'p': page, 'page_size': page_size}
        return self._request('GET', '/api/user/', params=params)
    
    def get_tokens(self, page: int = 1, page_size: int = 100) -> Dict[str, Any]:
        """获取Token列表"""
        params = {'p': page, 'page_size': page_size}
        return self._request('GET', '/api/token/', params=params)
    
    def get_channels(self, page: int = 1, page_size: int = 100) -> Dict[str, Any]:
        """获取渠道列表"""
        params = {'p': page, 'page_size': page_size}
        return self._request('GET', '/api/channel/', params=params)
    
    def get_groups(self, page: int = 1, page_size: int = 100) -> Dict[str, Any]:
        """获取分组列表"""
        params = {'p': page, 'page_size': page_size}
        return self._request('GET', '/api/group/', params=params)
    
    def explore_endpoints(self) -> Dict[str, Any]:
        """
        探索可用的API端点
        
        Returns:
            端点探索结果
        """
        endpoints_to_test = [
            ('/api/log/', 'GET', '日志接口'),
            ('/api/user/', 'GET', '用户接口'),
            ('/api/users/', 'GET', '用户列表接口'),
            ('/api/token/', 'GET', 'Token接口'),
            ('/api/tokens/', 'GET', 'Token列表接口'),
            ('/api/topup/', 'GET', '充值接口'),
            ('/api/topups/', 'GET', '充值列表接口'),
            ('/api/channel/', 'GET', '渠道接口'),
            ('/api/channels/', 'GET', '渠道列表接口'),
            ('/api/group/', 'GET', '分组接口'),
            ('/api/groups/', 'GET', '分组列表接口'),
            ('/api/statistics/', 'GET', '统计接口'),
            ('/api/stats/', 'GET', '统计接口（简化）'),
        ]
        
        results = {}
        
        print("\n" + "=" * 50)
        print("探索可用API端点...")
        print("=" * 50)
        
        for endpoint, method, description in endpoints_to_test:
            print(f"\n测试: {description} ({method} {endpoint})")
            response = self._request(method, endpoint, params={'p': 1, 'page_size': 1})
            
            if not response.get('error'):
                results[endpoint] = {
                    "method": method,
                    "description": description,
                    "available": True,
                    "sample_response": response
                }
                print(f"  ✓ 可用")
            else:
                status_code = response.get('status_code')
                if status_code == 404:
                    results[endpoint] = {
                        "method": method,
                        "description": description,
                        "available": False,
                        "reason": "404 Not Found"
                    }
                    print(f"  X 不可用 (404)")
                elif status_code == 403:
                    results[endpoint] = {
                        "method": method,
                        "description": description,
                        "available": False,
                        "reason": "403 Forbidden (权限不足)"
                    }
                    print(f"  X 不可用 (403 权限不足)")
                else:
                    results[endpoint] = {
                        "method": method,
                        "description": description,
                        "available": False,
                        "error": response.get('message')
                    }
                    print(f"  X 不可用: {response.get('message')}")
            
            time.sleep(0.3)  # 避免请求过快
        
        return results


if __name__ == "__main__":
    # 配置信息
    BASE_URL = "https://luckyapi.chat"
    TOKEN = "ulQjFtL5uSycaNboJ+eoO/zxCi8Qpk/s"
    USER_ID = "103"  # 管理员用户ID
    
    # 创建客户端
    client = NewAPIClient(BASE_URL, TOKEN)
    client.set_user_id(USER_ID)
    
    # 1. 测试连接
    connection_test = client.test_connection()
    print("\n连接测试结果:")
    print(json.dumps(connection_test, indent=2, ensure_ascii=False))
    
    # 2. 探索端点
    endpoints = client.explore_endpoints()
    
    # 3. 如果日志接口可用，获取样例数据
    if '/api/log/' in endpoints and endpoints['/api/log/'].get('available'):
        print("\n" + "=" * 50)
        print("获取日志数据样例...")
        print("=" * 50)
        
        # 获取最近一天的日志
        yesterday = datetime.now() - timedelta(days=1)
        sample_logs = client.get_all_logs_paginated(
            start_date=yesterday,
            max_pages=1
        )
        
        if sample_logs:
            print(f"\n获取到 {len(sample_logs)} 条样例日志")
            print("\n第一条日志结构:")
            print(json.dumps(sample_logs[0], indent=2, ensure_ascii=False))
    
    # 保存探索结果
    with open('api_exploration_result.json', 'w', encoding='utf-8') as f:
        json.dump({
            "connection_test": connection_test,
            "endpoints": endpoints,
            "exploration_time": datetime.now().isoformat()
        }, f, indent=2, ensure_ascii=False)
    
    print("\n" + "=" * 50)
    print("探索完成！结果已保存到 api_exploration_result.json")
    print("=" * 50)
