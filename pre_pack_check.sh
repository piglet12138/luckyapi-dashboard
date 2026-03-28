#!/bin/bash
# 打包前最终检查脚本
# Pre-packaging validation script

echo "======================================================================="
echo "NewAPI 数据看板 - 打包前检查"
echo "======================================================================="
echo ""

# 颜色定义
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

ERRORS=0
WARNINGS=0

# 检查函数
check_file() {
    if [ -f "$1" ]; then
        echo -e "${GREEN}✓${NC} $1 存在"
    else
        echo -e "${RED}✗${NC} $1 不存在"
        ((ERRORS++))
    fi
}

check_dir() {
    if [ -d "$1" ]; then
        echo -e "${GREEN}✓${NC} $1/ 目录存在"
    else
        echo -e "${YELLOW}!${NC} $1/ 目录不存在（将创建）"
        ((WARNINGS++))
    fi
}

warn_file() {
    if [ -f "$1" ]; then
        echo -e "${YELLOW}!${NC} $1 存在（包含敏感信息，确保已在.packignore中排除）"
        ((WARNINGS++))
    else
        echo -e "${GREEN}✓${NC} $1 不存在（正确）"
    fi
}

echo "1. 检查核心Python脚本..."
echo "-----------------------------------"
check_file "daily_update.py"
check_file "export_dashboard_data.py"
check_file "requirements.txt"
echo ""

echo "2. 检查源代码目录..."
echo "-----------------------------------"
check_dir "src"
check_dir "src/core"
check_dir "src/etl"
check_dir "src/sync"
check_file "src/sync/sync_incremental.py"
check_file "src/etl/ods_to_dwd.py"
check_file "src/etl/dwd_to_dws.py"
check_file "src/etl/dws_to_ads.py"
echo ""

echo "3. 检查看板文件..."
echo "-----------------------------------"
check_dir "dashboard"
check_file "dashboard/index.html"
echo ""

echo "4. 检查部署文件..."
echo "-----------------------------------"
check_dir "deploy"
check_file "deploy.sh"
check_file "deploy/backup.sh"
check_file "deploy/entrypoint.sh"
check_file "deploy/nginx.conf"
check_file "Dockerfile"
check_file "docker-compose.yml"
check_file ".env.example"
check_file ".packignore"
echo ""

echo "5. 检查文档..."
echo "-----------------------------------"
check_file "README.md"
check_file "SERVER_DEPLOYMENT_GUIDE.md"
check_file "PACKAGING_GUIDE.md"
check_file "QUICKSTART.md"
check_file "DEPLOYMENT.md"
check_file "CRON_SETUP.md"
check_file "项目完成总结.md"
echo ""

echo "6. 检查工作目录..."
echo "-----------------------------------"
check_dir "logs"
check_dir "backups"
echo ""

echo "7. 检查敏感文件（应该不存在或被排除）..."
echo "-----------------------------------"
warn_file ".env"
warn_file "config.ini"
warn_file "*.key"
warn_file "*.pem"
echo ""

echo "8. 检查缓存文件（应该已清理）..."
echo "-----------------------------------"
CACHE_COUNT=$(find . -type d -name "__pycache__" 2>/dev/null | wc -l)
PYC_COUNT=$(find . -type f -name "*.pyc" 2>/dev/null | wc -l)

if [ $CACHE_COUNT -eq 0 ]; then
    echo -e "${GREEN}✓${NC} __pycache__ 已清理"
else
    echo -e "${RED}✗${NC} 发现 $CACHE_COUNT 个 __pycache__ 目录"
    ((ERRORS++))
fi

if [ $PYC_COUNT -eq 0 ]; then
    echo -e "${GREEN}✓${NC} *.pyc 已清理"
else
    echo -e "${RED}✗${NC} 发现 $PYC_COUNT 个 .pyc 文件"
    ((ERRORS++))
fi
echo ""

echo "9. 检查脚本权限..."
echo "-----------------------------------"
for script in deploy.sh deploy/*.sh; do
    if [ -x "$script" ]; then
        echo -e "${GREEN}✓${NC} $script 可执行"
    else
        echo -e "${YELLOW}!${NC} $script 不可执行（将在服务器上设置）"
        ((WARNINGS++))
    fi
done
echo ""

echo "10. 数据库检查..."
echo "-----------------------------------"
if [ -f "newapi_warehouse.db" ]; then
    DB_SIZE=$(du -h newapi_warehouse.db | cut -f1)
    echo -e "${GREEN}✓${NC} 数据库存在，大小: $DB_SIZE"

    # 检查数据库是否可访问
    if command -v sqlite3 &> /dev/null; then
        LATEST_DATE=$(sqlite3 newapi_warehouse.db "SELECT MAX(stat_date) FROM ads_daily_summary;" 2>/dev/null)
        if [ -n "$LATEST_DATE" ]; then
            echo -e "${GREEN}✓${NC} 数据库可访问，最新数据: $LATEST_DATE"
        else
            echo -e "${YELLOW}!${NC} 数据库可能为空或损坏"
            ((WARNINGS++))
        fi
    fi
else
    echo -e "${YELLOW}!${NC} 数据库不存在（服务器需要重新同步）"
    ((WARNINGS++))
fi
echo ""

echo "11. 估算压缩包大小..."
echo "-----------------------------------"
if [ -f "newapi_warehouse.db" ]; then
    echo "预计大小（含数据库）: 500-600MB"
else
    echo "预计大小（不含数据库）: 1-2MB"
fi
echo ""

echo "======================================================================="
echo "检查完成！"
echo "======================================================================="
echo ""

if [ $ERRORS -eq 0 ] && [ $WARNINGS -eq 0 ]; then
    echo -e "${GREEN}✓ 所有检查通过！可以开始打包。${NC}"
    echo ""
    echo "打包命令："
    echo "  cd .."
    echo "  tar --exclude-from=newapi_export/.packignore -czf newapi_export.tar.gz newapi_export/"
    exit 0
elif [ $ERRORS -eq 0 ]; then
    echo -e "${YELLOW}! 检查完成，有 $WARNINGS 个警告${NC}"
    echo "  这些警告通常不影响打包，但请注意查看"
    echo ""
    echo "打包命令："
    echo "  cd .."
    echo "  tar --exclude-from=newapi_export/.packignore -czf newapi_export.tar.gz newapi_export/"
    exit 0
else
    echo -e "${RED}✗ 发现 $ERRORS 个错误，$WARNINGS 个警告${NC}"
    echo "  请修复错误后再打包"
    exit 1
fi
