# 服务器部署和维护指南

**给服务器上的 Claude 的完整指南**

---

## 📦 部署前准备

### 1. 解压项目

```bash
# 假设项目已上传到服务器
cd /opt
tar -xzf newapi_export.tar.gz
cd newapi_export

# 检查文件完整性
ls -la
```

### 2. 检查环境

**操作系统要求**:
- Ubuntu 20.04+ / CentOS 8+ / Debian 11+
- 2GB RAM（推荐4GB）
- 10GB 磁盘空间

**检查已安装软件**:
```bash
# 检查Python版本（需要3.8+）
python3 --version

# 检查pip
pip3 --version

# 检查SQLite
sqlite3 --version

# 检查Nginx（如果需要Web访问）
nginx -v
```

### 3. 安装依赖

```bash
# 更新系统包
sudo apt-get update  # Ubuntu/Debian
# 或
sudo yum update      # CentOS/RHEL

# 安装Python依赖
pip3 install -r requirements.txt

# 如果需要Web服务
sudo apt-get install -y nginx
```

---

## 🚀 部署方式选择

### 方式1: Docker部署（推荐）

**优点**: 环境隔离、易于维护、一键启动

```bash
# 1. 检查Docker
docker --version
docker-compose --version

# 2. 配置环境变量
cp .env.example .env
vim .env
# 修改以下配置：
# - SERVER_NAME=your-domain.com
# - BASE_URL=your-api-url
# - TOKEN=your-api-token
# - USER_ID=your-user-id

# 3. 启动服务
docker-compose up -d

# 4. 查看状态
docker-compose ps
docker-compose logs -f

# 5. 访问看板
# http://your-server-ip 或 http://your-domain.com
```

**常用命令**:
```bash
# 停止服务
docker-compose down

# 重启服务
docker-compose restart

# 查看日志
docker-compose logs -f app
docker-compose logs -f nginx

# 进入容器
docker-compose exec app bash

# 手动更新数据
docker-compose exec app python3 daily_update.py
```

### 方式2: 直接部署

**适合**: 已有Nginx环境、不使用Docker

#### 步骤1: 配置API连接

```bash
# 编辑配置文件
vim src/core/config.py

# 修改以下配置：
BASE_URL = "https://your-api-url.com"
TOKEN = "your-api-token"
USER_ID = "your-user-id"
DB_PATH = "/opt/newapi_export/newapi_warehouse.db"
```

#### 步骤2: 配置Nginx

```bash
# 复制Nginx配置
sudo cp deploy/nginx.conf /etc/nginx/sites-available/newapi-dashboard

# 编辑配置，修改域名和路径
sudo vim /etc/nginx/sites-available/newapi-dashboard

# 创建软链接
sudo ln -s /etc/nginx/sites-available/newapi-dashboard /etc/nginx/sites-enabled/

# 测试配置
sudo nginx -t

# 重启Nginx
sudo systemctl reload nginx
```

#### 步骤3: 配置定时任务

```bash
# 编辑crontab
crontab -e

# 添加以下内容：
# 每天凌晨2点执行数据更新
0 2 * * * cd /opt/newapi_export && /usr/bin/python3 daily_update.py >> logs/cron.log 2>&1

# 每天凌晨3点执行数据库备份
0 3 * * * /opt/newapi_export/deploy/backup.sh >> logs/backup.log 2>&1

# 保存后验证
crontab -l
```

#### 步骤4: 首次数据同步

```bash
# 如果没有数据库，需要首次全量同步
# 注意：这可能需要2-3小时
python3 src/sync/sync_full.py

# 或者如果已有数据库，只需增量更新
python3 daily_update.py
```

#### 步骤5: 启动服务

```bash
# Nginx已配置，可以直接访问
# http://your-server-ip
```

---

## 🔧 配置防火墙

```bash
# Ubuntu/Debian (ufw)
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable
sudo ufw status

# CentOS/RHEL (firewalld)
sudo firewall-cmd --permanent --add-service=http
sudo firewall-cmd --permanent --add-service=https
sudo firewall-cmd --reload
sudo firewall-cmd --list-all
```

---

## 🔐 配置HTTPS（推荐）

```bash
# 安装Certbot
sudo apt-get install certbot python3-certbot-nginx

# 获取SSL证书
sudo certbot --nginx -d your-domain.com

# 测试自动续期
sudo certbot renew --dry-run

# Certbot会自动配置Nginx和定时任务
```

---

## 📊 验证部署

### 1. 检查数据库

```bash
# 进入数据库
sqlite3 newapi_warehouse.db

# 检查表
.tables

# 检查数据量
SELECT 'ods_logs' as table_name, COUNT(*) as count FROM ods_logs
UNION ALL SELECT 'ads_daily_summary', COUNT(*) FROM ads_daily_summary;

# 检查最新数据日期
SELECT MAX(stat_date) FROM ads_daily_summary;

# 退出
.quit
```

### 2. 检查看板数据

```bash
# 检查JSON文件
ls -lh dashboard/dashboard_data.json

# 查看更新时间
python3 -c "import json; data = json.load(open('dashboard/dashboard_data.json', encoding='utf-8')); print('Update time:', data['update_time'])"
```

### 3. 测试数据更新

```bash
# 手动执行一次更新
python3 daily_update.py

# 查看日志
tail -f logs/daily_update.log
```

### 4. 访问看板

```bash
# 获取服务器IP
hostname -I | awk '{print $1}'

# 在浏览器访问
# http://your-server-ip
# 或
# https://your-domain.com
```

---

## 📅 每日维护任务

### 自动任务（已配置）

每天会自动执行以下任务：
- **凌晨2点**: 数据增量更新（6分钟）
- **凌晨3点**: 数据库备份（1分钟）

### 手动检查（每周）

```bash
# 1. 查看定时任务日志
tail -50 logs/cron.log
tail -50 logs/daily_update.log

# 2. 检查数据是否最新
sqlite3 newapi_warehouse.db "SELECT MAX(stat_date) FROM ads_daily_summary;"

# 3. 检查备份文件
ls -lht backups/ | head -10

# 4. 检查磁盘空间
df -h

# 5. 检查系统资源
top
# 或
htop
```

---

## 🔄 数据更新说明

### 增量更新（推荐）

`daily_update.py` 会自动完成所有流程：

```bash
python3 daily_update.py
```

**执行流程**:
1. 从API增量同步新数据（5-6分钟）
   - 检查最新记录
   - 只拉取新增数据
2. ODS → DWD 数据清洗（30秒）
3. DWD → DWS 数据汇总（2秒）
4. DWS → ADS 指标计算（2秒）
5. 导出看板数据（1秒）

**总耗时**: 约6分钟

### 全量同步（仅首次）

```bash
# 仅在首次部署或数据丢失时使用
python3 src/sync/sync_full.py
```

### 只更新用户和渠道

```bash
# 快速更新用户和渠道快照（不更新日志）
python3 src/sync/sync_users_channels.py
```

---

## 🛠️ 常用运维命令

### 查看服务状态

```bash
# Docker部署
docker-compose ps
docker-compose logs -f

# 直接部署
sudo systemctl status nginx
ps aux | grep python

# 查看端口占用
netstat -tlnp | grep :80
```

### 重启服务

```bash
# Docker部署
docker-compose restart

# 直接部署
sudo systemctl reload nginx
```

### 手动备份

```bash
# 执行备份脚本
./deploy/backup.sh

# 或手动备份
cp newapi_warehouse.db backups/newapi_warehouse_$(date +%Y%m%d_%H%M%S).db
gzip backups/newapi_warehouse_$(date +%Y%m%d_%H%M%S).db
```

### 恢复备份

```bash
# 1. 停止服务（Docker）
docker-compose down

# 2. 备份当前数据库
mv newapi_warehouse.db newapi_warehouse_broken.db

# 3. 恢复备份
gunzip -k backups/newapi_warehouse_20260315_020000.db.gz
mv backups/newapi_warehouse_20260315_020000.db newapi_warehouse.db

# 4. 重启服务
docker-compose up -d

# 5. 更新数据
python3 daily_update.py
```

### 数据库维护

```bash
# 优化数据库（每月执行一次）
sqlite3 newapi_warehouse.db "PRAGMA optimize; VACUUM; ANALYZE;"

# 检查数据库完整性
sqlite3 newapi_warehouse.db "PRAGMA integrity_check;"

# 查看数据库大小
du -h newapi_warehouse.db
```

### 日志管理

```bash
# 查看最近的日志
tail -100 logs/daily_update.log

# 实时查看日志
tail -f logs/daily_update.log

# 清理旧日志（保留30天）
find logs/ -name "*.log" -mtime +30 -delete

# 配置logrotate（自动轮转）
sudo cat > /etc/logrotate.d/newapi << EOF
/opt/newapi_export/logs/*.log {
    daily
    rotate 30
    compress
    delaycompress
    missingok
    notifempty
}
EOF
```

---

## 🚨 故障排查

### 问题1: 数据未更新

**症状**: 看板数据显示过期

**排查步骤**:
```bash
# 1. 检查定时任务是否执行
grep CRON /var/log/syslog | tail -20
tail -50 logs/cron.log

# 2. 手动执行测试
python3 daily_update.py

# 3. 检查数据库最新日期
sqlite3 newapi_warehouse.db "SELECT MAX(stat_date) FROM ads_daily_summary;"

# 4. 检查API连接
python3 -c "from src.core.api_client import NewAPIClient; from src.core.config import BASE_URL, TOKEN; client = NewAPIClient(BASE_URL, TOKEN); print(client.get_logs(page=1, page_size=1))"
```

### 问题2: 看板无法访问

**症状**: 浏览器无法打开看板

**排查步骤**:
```bash
# 1. 检查Nginx状态
sudo systemctl status nginx
sudo nginx -t

# 2. 检查端口
netstat -tlnp | grep :80

# 3. 检查防火墙
sudo ufw status  # Ubuntu
sudo firewall-cmd --list-all  # CentOS

# 4. 重启Nginx
sudo systemctl reload nginx

# 5. 查看Nginx日志
tail -50 /var/log/nginx/error.log
```

### 问题3: Docker容器异常

**症状**: Docker服务无法启动

**排查步骤**:
```bash
# 1. 查看容器状态
docker-compose ps

# 2. 查看日志
docker-compose logs -f

# 3. 重新构建
docker-compose down
docker-compose up -d --build

# 4. 检查配置
cat .env
cat docker-compose.yml
```

### 问题4: 磁盘空间不足

**症状**: 数据库或备份失败

**排查步骤**:
```bash
# 1. 检查磁盘使用
df -h

# 2. 查找大文件
du -sh * | sort -hr | head -10

# 3. 清理旧备份
find backups/ -name "*.gz" -mtime +30 -delete

# 4. 清理旧日志
find logs/ -name "*.log" -mtime +30 -delete

# 5. 优化数据库
sqlite3 newapi_warehouse.db "VACUUM;"
```

### 问题5: 内存不足

**症状**: Python进程被杀

**排查步骤**:
```bash
# 1. 查看内存使用
free -h

# 2. 查看进程内存
top -o %MEM

# 3. 检查swap
swapon --show

# 4. 增加swap（如果需要）
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
```

---

## 🔄 更新升级

### 更新代码

```bash
# 1. 备份当前版本
cd /opt
tar -czf newapi_export_backup_$(date +%Y%m%d).tar.gz newapi_export/

# 2. 上传新版本并解压
# （假设已上传到 /tmp/newapi_export_new.tar.gz）
cd /opt/newapi_export
tar -xzf /tmp/newapi_export_new.tar.gz --strip-components=1

# 3. 重启服务
# Docker:
docker-compose down && docker-compose up -d --build

# 直接部署:
sudo systemctl reload nginx

# 4. 测试
python3 daily_update.py
```

### 更新依赖

```bash
# 更新Python包
pip3 install -r requirements.txt --upgrade

# 重启服务
docker-compose restart  # Docker
```

---

## 📊 监控和告警（可选）

### 简单的监控脚本

创建 `monitor.sh`:
```bash
#!/bin/bash

# 检查数据新鲜度
LATEST_DATE=$(sqlite3 newapi_warehouse.db "SELECT MAX(stat_date) FROM ads_daily_summary;")
TODAY=$(date +%Y-%m-%d)
YESTERDAY=$(date -d "yesterday" +%Y-%m-%d)

if [ "$LATEST_DATE" != "$TODAY" ] && [ "$LATEST_DATE" != "$YESTERDAY" ]; then
    echo "警告: 数据不是最新的! 最新日期: $LATEST_DATE"
    # 可以在这里添加邮件或Slack通知
fi

# 检查磁盘空间
DISK_USAGE=$(df -h / | awk 'NR==2 {print $5}' | sed 's/%//')
if [ $DISK_USAGE -gt 80 ]; then
    echo "警告: 磁盘使用率过高: ${DISK_USAGE}%"
fi

# 检查服务状态
if ! pgrep nginx > /dev/null; then
    echo "警告: Nginx未运行"
fi
```

### 配置监控定时任务

```bash
# 每小时检查一次
crontab -e
# 添加:
0 * * * * /opt/newapi_export/monitor.sh >> logs/monitor.log 2>&1
```

---

## 📞 获取帮助

### 文档索引

- **快速启动**: [QUICKSTART.md](QUICKSTART.md)
- **完整部署**: [DEPLOYMENT.md](DEPLOYMENT.md)
- **定时任务**: [CRON_SETUP.md](CRON_SETUP.md)
- **项目总结**: [项目完成总结.md](项目完成总结.md)
- **问题解答**: [看板问题解答文档.md](看板问题解答文档.md)

### 常用查询

```bash
# 查看数据统计
sqlite3 newapi_warehouse.db << EOF
SELECT
    'ODS日志' as 表名, COUNT(*) as 记录数 FROM ods_logs
UNION ALL SELECT 'ODS用户', COUNT(*) FROM ods_users
UNION ALL SELECT 'ADS每日汇总', COUNT(*) FROM ads_daily_summary
UNION ALL SELECT '最新日期', MAX(stat_date) FROM ads_daily_summary;
.quit
EOF

# 查看最近7天的数据趋势
sqlite3 newapi_warehouse.db << EOF
SELECT
    stat_date as 日期,
    total_users as 总用户,
    active_users as 活跃用户,
    paying_users as 付费用户,
    total_calls as 总调用,
    total_revenue as 总收入
FROM ads_daily_summary
ORDER BY stat_date DESC
LIMIT 7;
.quit
EOF
```

---

## ✅ 部署检查清单

部署完成后，请验证以下项目：

- [ ] 项目已解压到正确位置（/opt/newapi_export）
- [ ] Python依赖已安装（pip3 install -r requirements.txt）
- [ ] API配置已更新（config.py 或 .env）
- [ ] 数据库存在且有数据
- [ ] Nginx已配置并运行
- [ ] 防火墙已开放80/443端口
- [ ] 定时任务已配置（crontab -l）
- [ ] HTTPS已配置（可选但推荐）
- [ ] 备份脚本已配置
- [ ] 可以通过浏览器访问看板
- [ ] 手动执行一次更新成功（python3 daily_update.py）
- [ ] 看板显示最新数据

---

## 🎉 部署完成

如果以上检查清单全部通过，恭喜！部署已成功完成。

**日常使用**:
- 系统每天凌晨2点自动更新数据
- 每天凌晨3点自动备份数据库
- 通过浏览器访问看板查看数据

**需要帮助时**:
- 查看日志: `tail -f logs/daily_update.log`
- 查看文档: `DEPLOYMENT.md`, `QUICKSTART.md`
- 手动更新: `python3 daily_update.py`

**祝使用愉快！** 🚀
