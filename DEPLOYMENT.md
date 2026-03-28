# NewAPI 数据仓库 - 服务器部署方案

**版本**: v1.0
**更新时间**: 2026-03-15
**部署方式**: Docker + Nginx

---

## 📋 目录

1. [部署架构](#部署架构)
2. [前置要求](#前置要求)
3. [快速部署](#快速部署)
4. [详细配置](#详细配置)
5. [监控和维护](#监控和维护)
6. [常见问题](#常见问题)

---

## 部署架构

```
┌─────────────────────────────────────────┐
│           Internet / LAN                 │
└──────────────┬──────────────────────────┘
               │
               ↓
┌──────────────────────────────────────────┐
│          Nginx (反向代理)                 │
│      - 静态文件服务                       │
│      - HTTPS (可选)                       │
│      - Gzip压缩                          │
└──────────────┬───────────────────────────┘
               │
               ↓
┌──────────────────────────────────────────┐
│      数据看板 (Static HTML/JS)            │
│      - Bootstrap 5                       │
│      - ECharts 5                         │
│      - dashboard_data.json               │
└──────────────┬───────────────────────────┘
               │
               ↓
┌──────────────────────────────────────────┐
│       数据仓库 (SQLite)                   │
│      - newapi_warehouse.db               │
│      - ODS/DWD/DWS/ADS 四层架构          │
└──────────────┬───────────────────────────┘
               │
               ↓
┌──────────────────────────────────────────┐
│      定时任务 (Cron)                      │
│      - 每日增量更新                       │
│      - 自动ETL计算                        │
│      - 看板数据导出                       │
└──────────────────────────────────────────┘
```

---

## 前置要求

### 服务器配置

| 资源 | 最低配置 | 推荐配置 |
|------|---------|---------|
| CPU | 1核 | 2核 |
| 内存 | 1GB | 2GB |
| 硬盘 | 5GB | 10GB |
| 带宽 | 1Mbps | 5Mbps |

### 软件要求

- **操作系统**: Ubuntu 20.04+ / CentOS 8+ / Debian 11+
- **Docker**: 20.10+
- **Docker Compose**: 1.29+
- **Git**: 2.x

---

## 快速部署

### 方案1: Docker Compose 一键部署 (推荐)

```bash
# 1. 克隆或上传项目
cd /opt
git clone <your-repo-url> newapi-dashboard
cd newapi-dashboard

# 2. 配置环境变量
cp .env.example .env
vim .env  # 修改配置

# 3. 一键部署
docker-compose up -d

# 4. 查看状态
docker-compose ps
docker-compose logs -f

# 5. 访问看板
# http://your-server-ip
# 或 http://your-domain.com
```

### 方案2: 直接部署 (不使用Docker)

```bash
# 1. 安装依赖
sudo apt-get update
sudo apt-get install -y python3 python3-pip nginx

# 2. 安装Python包
pip3 install -r requirements.txt

# 3. 配置Nginx
sudo cp deploy/nginx.conf /etc/nginx/sites-available/newapi-dashboard
sudo ln -s /etc/nginx/sites-available/newapi-dashboard /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx

# 4. 配置定时任务
crontab -e
# 添加：0 2 * * * cd /opt/newapi-dashboard && python3 daily_update.py

# 5. 手动执行一次更新
python3 daily_update.py

# 6. 访问看板
# http://your-server-ip
```

---

## 详细配置

### 1. 环境变量配置

创建 `.env` 文件：

```bash
# 服务器配置
SERVER_NAME=your-domain.com
SERVER_PORT=80

# 数据库配置
DB_PATH=/app/newapi_warehouse.db

# 日志配置
LOG_LEVEL=INFO
LOG_DIR=/app/logs

# 定时任务配置
CRON_SCHEDULE=0 2 * * *

# Nginx配置
NGINX_WORKER_PROCESSES=auto
NGINX_WORKER_CONNECTIONS=1024

# 安全配置 (生产环境建议配置)
ENABLE_HTTPS=false
SSL_CERTIFICATE=/etc/nginx/ssl/cert.pem
SSL_CERTIFICATE_KEY=/etc/nginx/ssl/key.pem

# 数据脱敏 (如果需要公开访问)
ENABLE_DATA_MASKING=true
```

### 2. Nginx配置

查看 `deploy/nginx.conf` 配置详情。

### 3. Docker配置

查看 `Dockerfile` 和 `docker-compose.yml` 配置详情。

---

## 监控和维护

### 1. 日志查看

```bash
# Docker部署
docker-compose logs -f nginx
docker-compose logs -f app

# 直接部署
tail -f logs/daily_update.log
tail -f /var/log/nginx/access.log
tail -f /var/log/nginx/error.log
```

### 2. 数据库备份

```bash
# 手动备份
./deploy/backup.sh

# 自动备份 (每天3点)
echo "0 3 * * * /opt/newapi-dashboard/deploy/backup.sh" | crontab -
```

### 3. 性能监控

```bash
# 安装监控工具
sudo apt-get install htop iotop nethogs

# 查看资源使用
htop                    # CPU和内存
iotop                   # 磁盘IO
nethogs                 # 网络流量
docker stats            # Docker容器资源
```

### 4. 健康检查

```bash
# 检查服务状态
systemctl status nginx
docker-compose ps

# 检查端口监听
netstat -tlnp | grep 80

# 检查数据库
sqlite3 newapi_warehouse.db "SELECT COUNT(*) FROM ads_daily_summary"

# 检查最新数据
sqlite3 newapi_warehouse.db "SELECT MAX(stat_date) FROM ads_daily_summary"
```

---

## 安全配置

### 1. 防火墙配置

```bash
# UFW (Ubuntu)
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable

# Firewalld (CentOS)
sudo firewall-cmd --permanent --add-service=http
sudo firewall-cmd --permanent --add-service=https
sudo firewall-cmd --reload
```

### 2. HTTPS配置

#### 使用 Let's Encrypt (免费)

```bash
# 安装 Certbot
sudo apt-get install certbot python3-certbot-nginx

# 获取证书
sudo certbot --nginx -d your-domain.com

# 自动续期
sudo certbot renew --dry-run
```

#### 手动配置SSL

修改 `deploy/nginx.conf`：

```nginx
server {
    listen 443 ssl http2;
    server_name your-domain.com;

    ssl_certificate /etc/nginx/ssl/cert.pem;
    ssl_certificate_key /etc/nginx/ssl/key.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;

    # 其他配置...
}

# HTTP 重定向到 HTTPS
server {
    listen 80;
    server_name your-domain.com;
    return 301 https://$server_name$request_uri;
}
```

### 3. 访问控制

#### 基本认证

```bash
# 安装工具
sudo apt-get install apache2-utils

# 创建密码文件
sudo htpasswd -c /etc/nginx/.htpasswd admin

# Nginx配置添加
auth_basic "Restricted Access";
auth_basic_user_file /etc/nginx/.htpasswd;
```

#### IP白名单

```nginx
location / {
    allow 192.168.1.0/24;  # 允许内网访问
    allow 1.2.3.4;         # 允许特定IP
    deny all;              # 拒绝其他
}
```

---

## 更新和升级

### 1. 更新看板数据

```bash
# Docker部署
docker-compose exec app python3 daily_update.py

# 直接部署
cd /opt/newapi-dashboard
python3 daily_update.py
```

### 2. 更新代码

```bash
# 拉取最新代码
git pull origin main

# 重启服务 (Docker)
docker-compose down
docker-compose up -d --build

# 重启服务 (直接部署)
sudo systemctl reload nginx
```

### 3. 数据库迁移

```bash
# 备份现有数据库
cp newapi_warehouse.db newapi_warehouse_backup.db

# 运行迁移脚本 (如果有)
python3 migrate.py

# 验证数据
python3 -c "from src.core.database import Database; db = Database(); db.connect(); print('OK')"
```

---

## 故障排查

### 1. 看板无法访问

```bash
# 检查Nginx状态
sudo systemctl status nginx
sudo nginx -t

# 检查端口占用
netstat -tlnp | grep :80

# 检查防火墙
sudo ufw status
sudo iptables -L
```

### 2. 数据未更新

```bash
# 检查定时任务
crontab -l
sudo systemctl status cron

# 查看更新日志
tail -f logs/daily_update.log

# 手动执行测试
python3 daily_update.py
```

### 3. 数据库锁定

```bash
# 检查数据库连接
lsof newapi_warehouse.db

# 重启可能占用的进程
docker-compose restart
```

### 4. 内存不足

```bash
# 查看内存使用
free -h
docker stats

# 清理Docker缓存
docker system prune -a

# 优化SQLite
sqlite3 newapi_warehouse.db "VACUUM;"
```

---

## 常见问题

### Q1: 如何修改更新时间？

修改cron配置：

```bash
# 编辑crontab
crontab -e

# 修改时间（例如改为每天凌晨3点）
0 3 * * * cd /opt/newapi-dashboard && python3 daily_update.py
```

### Q2: 如何备份数据？

```bash
# 手动备份
./deploy/backup.sh

# 查看备份
ls -lh backups/
```

### Q3: 如何迁移到其他服务器？

```bash
# 1. 在旧服务器打包
tar -czf newapi-dashboard.tar.gz newapi-dashboard/

# 2. 传输到新服务器
scp newapi-dashboard.tar.gz user@new-server:/opt/

# 3. 在新服务器解压
cd /opt
tar -xzf newapi-dashboard.tar.gz

# 4. 重新部署
cd newapi-dashboard
docker-compose up -d
```

### Q4: 数据库性能优化？

```bash
# 优化SQLite
sqlite3 newapi_warehouse.db <<EOF
PRAGMA journal_mode = WAL;
PRAGMA synchronous = NORMAL;
PRAGMA cache_size = -64000;
PRAGMA temp_store = MEMORY;
ANALYZE;
VACUUM;
EOF
```

---

## 性能优化

### 1. Nginx优化

```nginx
# 启用Gzip压缩
gzip on;
gzip_types text/plain text/css application/json application/javascript text/xml application/xml application/xml+rss text/javascript;
gzip_min_length 1000;
gzip_comp_level 6;

# 启用缓存
location ~* \.(jpg|jpeg|png|gif|ico|css|js)$ {
    expires 30d;
    add_header Cache-Control "public, immutable";
}

# 启用HTTP/2
listen 443 ssl http2;
```

### 2. SQLite优化

```python
# 在database.py中添加
conn.execute("PRAGMA journal_mode = WAL")
conn.execute("PRAGMA synchronous = NORMAL")
conn.execute("PRAGMA cache_size = -64000")
conn.execute("PRAGMA temp_store = MEMORY")
```

### 3. CDN加速 (可选)

使用CDN加速ECharts和Bootstrap：

```html
<!-- 使用CDN -->
<script src="https://cdn.jsdelivr.net/npm/echarts@5.4.3/dist/echarts.min.js"></script>
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css">
```

---

## 联系支持

如有问题，请查看：
- [开发文档.md](开发文档.md)
- [使用文档.md](使用文档.md)
- [看板问题解答文档.md](看板问题解答文档.md)

---

**部署完成后，访问 `http://your-server-ip` 即可查看数据看板！**
