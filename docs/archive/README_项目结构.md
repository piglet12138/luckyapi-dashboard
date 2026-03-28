# 项目结构说明

## 📁 目录结构

```
newapi_export/
├── src/                          # 源代码目录
│   ├── core/                      # 核心模块
│   │   ├── __init__.py
│   │   ├── config.py              # 配置文件（API、数据库、同步配置）
│   │   ├── api_client.py          # API客户端
│   │   ├── database.py            # 数据库操作
│   │   └── utils.py               # 工具函数
│   │
│   ├── sync/                      # 同步模块
│   │   ├── __init__.py
│   │   ├── sync_strategy.py       # 同步策略（BetterSyncStrategy类）
│   │   ├── sync_full.py           # 全量同步脚本
│   │   └── sync_users_channels.py # 用户渠道同步脚本
│   │
│   ├── tools/                      # 工具模块
│   │   ├── __init__.py
│   │   ├── check_progress.py      # 进度检查
│   │   ├── verify_completion.py   # 完成情况验证
│   │   └── monitor_sync.py        # 实时监控
│   │
│   └── analysis/                  # 分析模块（待实现）
│       └── __init__.py
│
├── docs/                          # 文档目录
│   ├── 数据字典.md
│   ├── 数仓设计方案.md
│   ├── 数仓表分类说明.md
│   ├── 部署方案.md
│   ├── 内存需求评估.md
│   ├── 同步完成评估报告.md
│   └── 数据管道评估报告.md
│
├── tests/                         # 测试目录（待整理）
│
├── sync.py                        # 主同步入口（全量同步）
├── sync_users_channels.py         # 用户渠道同步入口
├── check_sync_progress.py         # 进度检查入口（兼容旧路径）
├── verify_completion.py           # 验证入口（兼容旧路径）
├── README.md                      # 项目说明
└── newapi_warehouse.db            # SQLite数据库文件
```

## 🔧 模块说明

### core 模块
- **config.py**: 集中管理所有配置（API、数据库、同步参数）
- **api_client.py**: NewAPI管理接口客户端
- **database.py**: 数据库连接和表管理
- **utils.py**: 数据清洗和转换工具函数

### sync 模块
- **sync_strategy.py**: 核心同步策略类 `BetterSyncStrategy`
- **sync_full.py**: 全量同步脚本（日志+用户+渠道）
- **sync_users_channels.py**: 快速同步用户和渠道数据

### tools 模块
- **check_progress.py**: 检查同步进度
- **verify_completion.py**: 验证数据完整性
- **monitor_sync.py**: 实时监控同步进度

## 📝 使用说明

### 全量同步
```bash
python sync.py
```

### 用户渠道同步
```bash
python sync_users_channels.py
```

### 检查进度
```bash
python check_sync_progress.py
```

### 验证完成情况
```bash
python verify_completion.py
```

## 🔄 导入路径

所有模块使用相对导入，通过 `sys.path` 添加项目根目录：

```python
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.core.api_client import NewAPIClient
from src.core.database import Database
from src.core.config import BASE_URL, TOKEN, USER_ID
```

## ⚙️ 配置管理

所有配置集中在 `src/core/config.py`，支持环境变量：

```python
# 环境变量优先级高于默认值
BASE_URL = os.getenv("NEWAPI_BASE_URL", "https://luckyapi.chat")
TOKEN = os.getenv("NEWAPI_TOKEN", "your_token")
USER_ID = os.getenv("NEWAPI_USER_ID", "103")
```

## 📦 待实现功能

1. **增量同步**: `src/sync/sync_incremental.py`
2. **数据清洗层**: `src/etl/dwd_*.py`
3. **数据汇总层**: `src/etl/dws_*.py`
4. **应用数据层**: `src/etl/ads_*.py`
5. **数据看板**: `src/dashboard/`
