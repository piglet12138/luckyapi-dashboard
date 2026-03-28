#!/bin/bash
# 看板健康检查看门狗：若 8080 无响应则重启 newapi-dashboard 服务
CHECK_URL="http://127.0.0.1:8080/"
TIMEOUT=5
LOG="/root/newapi_export/logs/watchdog.log"

mkdir -p "$(dirname "$LOG")"

export no_proxy='*'; export NO_PROXY='*'
if ! curl -sf --connect-timeout "$TIMEOUT" --max-time "$TIMEOUT" -o /dev/null "$CHECK_URL"; then
    echo "[$(date -Iseconds)] 8080 无响应，重启 newapi-dashboard" >> "$LOG"
    systemctl restart newapi-dashboard
fi
