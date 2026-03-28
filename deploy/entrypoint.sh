#!/bin/bash
set -e

echo "Starting NewAPI Dashboard..."

# 启动cron服务
service cron start

# 执行一次数据更新（如果数据库为空）
if [ ! -f /app/dashboard/dashboard_data.json ]; then
    echo "初始化数据..."
    python3 /app/daily_update.py
fi

# 保持容器运行
echo "NewAPI Dashboard is ready!"
exec "$@"
