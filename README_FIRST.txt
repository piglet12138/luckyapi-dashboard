================================================================================
NewAPI 数据看板项目
================================================================================

版本: v2.0
状态: 生产就绪
更新: 2026-03-15

================================================================================
📖 首次部署必读
================================================================================

如果你是第一次在服务器上部署这个项目，请按以下顺序阅读文档：

1. **SERVER_DEPLOYMENT_GUIDE.md** ⭐⭐⭐⭐⭐ （最重要）
   - 完整的服务器部署指南
   - 包含所有部署方式（Docker/直接部署）
   - 包含维护、监控、故障排查
   - 给服务器上的Claude的专用文档

2. **QUICKSTART.md** ⭐⭐⭐⭐
   - 快速启动指南
   - 3分钟快速部署
   - 常用命令速查

3. **README.md** ⭐⭐⭐
   - 项目介绍
   - 核心功能说明
   - 技术栈

================================================================================
🚀 快速开始（3分钟）
================================================================================

方式1: Docker部署（推荐）
--------------------------
cd /opt/newapi_export
cp .env.example .env
vim .env  # 配置 BASE_URL, TOKEN, USER_ID
docker-compose up -d

方式2: 一键部署
--------------------------
cd /opt/newapi_export
./deploy.sh

方式3: 查看完整指南
--------------------------
cat SERVER_DEPLOYMENT_GUIDE.md
# 或
less SERVER_DEPLOYMENT_GUIDE.md

================================================================================
📋 项目结构
================================================================================

newapi_export/
├── src/                              源代码
│   ├── core/                         核心模块（API、数据库、配置）
│   ├── sync/                         数据同步
│   │   └── sync_incremental.py       增量同步（新）⭐
│   ├── etl/                          ETL处理
│   └── tools/                        工具脚本
├── dashboard/                        数据看板
│   ├── index.html                    看板页面
│   └── dashboard_data.json           看板数据
├── deploy/                           部署文件
│   ├── nginx.conf                    Nginx配置
│   ├── backup.sh                     备份脚本
│   └── entrypoint.sh                 Docker启动脚本
├── logs/                             日志目录
├── backups/                          备份目录
├── daily_update.py                   每日更新脚本（主要）⭐
├── export_dashboard_data.py          数据导出
├── deploy.sh                         一键部署
├── Dockerfile                        Docker镜像
├── docker-compose.yml                Docker编排
├── .env.example                      环境变量模板
├── requirements.txt                  Python依赖
├── newapi_warehouse.db               数据库（504MB）
└── 文档/                             *.md 文档文件

================================================================================
⚙️ 核心配置
================================================================================

在部署前，需要配置以下信息：

方式1: 使用 .env 文件（Docker部署）
-----------------------------------
cp .env.example .env
vim .env

# 修改以下配置：
BASE_URL=https://your-api-url.com
TOKEN=your-api-token
USER_ID=your-user-id
SERVER_NAME=your-domain.com

方式2: 修改 config.py（直接部署）
-----------------------------------
vim src/core/config.py

# 修改以下配置：
BASE_URL = "https://your-api-url.com"
TOKEN = "your-api-token"
USER_ID = "your-user-id"

================================================================================
🔄 每日自动更新
================================================================================

项目已包含完整的每日增量更新功能：

执行命令:
---------
python3 daily_update.py

功能说明:
---------
1. 从API增量同步新数据（约5-6分钟）
2. ETL处理：ODS → DWD → DWS → ADS（约30秒）
3. 导出看板数据（约1秒）

总耗时: 约6分钟

配置定时任务:
-------------
crontab -e

# 添加：每天凌晨2点自动更新
0 2 * * * cd /opt/newapi_export && python3 daily_update.py >> logs/cron.log 2>&1

# 添加：每天凌晨3点自动备份
0 3 * * * /opt/newapi_export/deploy/backup.sh >> logs/backup.log 2>&1

================================================================================
🎯 核心功能
================================================================================

✅ 四层数据仓库（ODS/DWD/DWS/ADS）
✅ 每日增量自动更新（新功能）
✅ 数据可视化看板（双Tab布局）
✅ 用户增长和留存分析
✅ 渠道归因和效果评估
✅ 新用户转化率分析（Phase 2）
✅ 分层复购率分析（Phase 2）

================================================================================
📊 看板访问
================================================================================

Docker部署:
-----------
http://your-server-ip
或
https://your-domain.com

直接部署:
---------
通过Nginx配置的域名访问

本地测试:
---------
cd dashboard
python3 -m http.server 8000
# 访问 http://localhost:8000

================================================================================
🛠️ 常用命令
================================================================================

Docker部署:
-----------
docker-compose ps                     # 查看状态
docker-compose logs -f                # 查看日志
docker-compose restart                # 重启服务
docker-compose exec app bash          # 进入容器
docker-compose exec app python3 daily_update.py  # 手动更新

直接部署:
---------
python3 daily_update.py               # 手动更新数据
./deploy/backup.sh                    # 手动备份
sudo systemctl status nginx           # 查看Nginx状态
tail -f logs/daily_update.log         # 查看更新日志

数据库:
-------
sqlite3 newapi_warehouse.db           # 进入数据库
.tables                               # 查看所有表
SELECT MAX(stat_date) FROM ads_daily_summary;  # 查看最新日期
.quit                                 # 退出

================================================================================
📞 需要帮助？
================================================================================

1. 查看部署指南: cat SERVER_DEPLOYMENT_GUIDE.md
2. 查看快速启动: cat QUICKSTART.md
3. 查看完整文档: ls *.md
4. 查看日志: tail -f logs/daily_update.log
5. 故障排查: 参考 SERVER_DEPLOYMENT_GUIDE.md 中的"故障排查"章节

================================================================================
✅ 部署检查清单
================================================================================

解压后:
  [ ] 检查文件完整性: ls -la
  [ ] 配置API连接: vim .env 或 vim src/core/config.py
  [ ] 安装依赖: pip3 install -r requirements.txt
  [ ] 选择部署方式: Docker 或 直接部署

Docker部署:
  [ ] 启动服务: docker-compose up -d
  [ ] 查看状态: docker-compose ps
  [ ] 查看日志: docker-compose logs -f

直接部署:
  [ ] 配置Nginx: 参考 SERVER_DEPLOYMENT_GUIDE.md
  [ ] 配置定时任务: crontab -e
  [ ] 配置防火墙: 参考 SERVER_DEPLOYMENT_GUIDE.md
  [ ] 首次更新: python3 daily_update.py

验证:
  [ ] 访问看板: http://your-server-ip
  [ ] 检查数据: 看板显示最新数据
  [ ] 查看日志: tail -f logs/daily_update.log

================================================================================
🎉 准备完成，开始部署！
================================================================================

接下来请阅读: SERVER_DEPLOYMENT_GUIDE.md

祝部署顺利！🚀
