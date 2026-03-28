#!/bin/bash
# 数据库备份脚本（使用 Python，不依赖 sqlite3 命令行）

set -e
cd "$(dirname "$0")/.."
BACKUP_DIR="backups"
DB_FILE="newapi_warehouse.db"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_FILE="${BACKUP_DIR}/newapi_warehouse_${TIMESTAMP}.db"
KEEP_DAYS=30

mkdir -p "${BACKUP_DIR}"
echo "开始备份数据库..."
echo "时间: $(date)"

python3 -c "
import sqlite3
import os
src = sqlite3.connect('${DB_FILE}')
dst = sqlite3.connect('${BACKUP_FILE}')
with dst:
    src.backup(dst)
src.close()
dst.close()
print('备份文件已生成:', '${BACKUP_FILE}')
"

if [ -f "${BACKUP_FILE}" ]; then
    gzip "${BACKUP_FILE}"
    echo "压缩完成: ${BACKUP_FILE}.gz"
    SIZE=$(du -h "${BACKUP_FILE}.gz" | cut -f1)
    echo "备份文件大小: ${SIZE}"
    echo "清理旧备份（保留${KEEP_DAYS}天）..."
    find "${BACKUP_DIR}" -name "newapi_warehouse_*.db.gz" -mtime +${KEEP_DAYS} -delete 2>/dev/null || true
    echo ""
    echo "当前备份列表:"
    ls -lh "${BACKUP_DIR}"/newapi_warehouse_*.db.gz 2>/dev/null | tail -5 || echo "（暂无）"
    echo "备份完成！"
else
    echo "备份失败！"
    exit 1
fi
