# NewAPI 数据看板 - 快速启动指南

## 🚀 快速部署（3分钟）

### 前置要求
- Ubuntu 20.04+ / CentOS 8+ / Debian 11+
- 2GB RAM（最低1GB）
- 10GB 硬盘空间

---

## 方式1: 一键部署（推荐）

```bash
# 1. 克隆或上传项目到服务器
cd /opt
git clone <your-repo> newapi-dashboard
cd newapi-dashboard

# 2. 执行一键部署脚本
chmod +x deploy.sh
./deploy.sh

# 3. 等待部署完成（约2-3分钟）

# 4. 访问看板
# http://your-server-ip
```

**就这么简单！** 🎉

---

## 方式2: Docker Compose手动部署

```bash
# 1. 进入项目目录
cd /opt/newapi-dashboard

# 2. 配置环境变量
cp .env.example .env
vim .env  # 修改SERVER_NAME等配置

# 3. 启动服务
docker-compose up -d

# 4. 查看状态
docker-compose ps
docker-compose logs -f

# 5. 访问看板
# http://your-server-ip
```

---

## 方式3: 不使用Docker

### 步骤1: 安装依赖

```bash
# Ubuntu/Debian
sudo apt-get update
sudo apt-get install -y python3 python3-pip nginx sqlite3

# CentOS/RHEL
sudo yum install -y python3 python3-pip nginx sqlite
```

### 步骤2: 安装Python包

```bash
cd /opt/newapi-dashboard
pip3 install -r requirements.txt
```

### 步骤3: 配置Nginx

```bash
# 复制配置文件
sudo cp deploy/nginx.conf /etc/nginx/sites-available/newapi-dashboard
sudo ln -s /etc/nginx/sites-available/newapi-dashboard /etc/nginx/sites-enabled/

# 测试配置
sudo nginx -t

# 重启Nginx
sudo systemctl reload nginx
```

### 步骤4: 配置定时任务

```bash
# 编辑crontab
crontab -e

# 添加定时任务（每天凌晨2点更新）
0 2 * * * cd /opt/newapi-dashboard && python3 daily_update.py >> logs/cron.log 2>&1
```

### 步骤5: 手动执行一次更新

```bash
python3 daily_update.py
```

### 步骤6: 访问看板

浏览器访问: `http://your-server-ip`

---

## 常用命令

### Docker部署

```bash
# 查看服务状态
docker-compose ps

# 查看日志
docker-compose logs -f
docker-compose logs -f nginx    # 只看Nginx日志
docker-compose logs -f app      # 只看应用日志

# 重启服务
docker-compose restart

# 停止服务
docker-compose down

# 更新数据
docker-compose exec app python3 daily_update.py

# 进入容器
docker-compose exec app bash

# 备份数据库
docker-compose exec app /app/deploy/backup.sh
```

### 直接部署

```bash
# 查看Nginx状态
sudo systemctl status nginx
sudo systemctl reload nginx

# 查看定时任务
crontab -l

# 手动更新数据
cd /opt/newapi-dashboard
python3 daily_update.py

# 查看日志
tail -f logs/daily_update.log
tail -f /var/log/nginx/access.log

# 备份数据库
./deploy/backup.sh
```

---

## 访问看板

### 本地访问
- `http://localhost`
- `http://127.0.0.1`

### 远程访问
- `http://your-server-ip`
- `http://your-domain.com` (如果配置了域名)

### HTTPS访问（可选）
- `https://your-domain.com`

配置HTTPS请查看: [DEPLOYMENT.md](DEPLOYMENT.md#安全配置)

---

## 数据更新

### 自动更新
每天凌晨2点自动执行（通过cron配置）

### 手动更新

```bash
# Docker部署
docker-compose exec app python3 daily_update.py

# 直接部署
cd /opt/newapi-dashboard
python3 daily_update.py
```

---

## 故障排查

### 看板无法访问

```bash
# 检查Nginx状态
sudo systemctl status nginx
sudo nginx -t

# 检查端口
netstat -tlnp | grep :80

# 检查防火墙
sudo ufw status          # Ubuntu
sudo firewall-cmd --list-all  # CentOS
```

### 数据未更新

```bash
# 查看更新日志
tail -f logs/daily_update.log

# 检查定时任务
crontab -l

# 手动执行测试
python3 daily_update.py
```

### Docker服务异常

```bash
# 查看服务状态
docker-compose ps

# 查看日志
docker-compose logs -f

# 重启服务
docker-compose restart

# 重新构建
docker-compose down
docker-compose up -d --build
```

---

## 性能优化

### 1. 启用HTTP/2和Gzip

已在 `deploy/nginx.conf` 中预配置

### 2. 数据库优化

```bash
# 优化SQLite
sqlite3 newapi_warehouse.db "PRAGMA optimize; VACUUM;"
```

### 3. 使用CDN加速静态资源

ECharts和Bootstrap已使用CDN

---

## 安全建议

### 1. 配置防火墙

```bash
# Ubuntu
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable

# CentOS
sudo firewall-cmd --permanent --add-service=http
sudo firewall-cmd --permanent --add-service=https
sudo firewall-cmd --reload
```

### 2. 配置HTTPS

使用Let's Encrypt免费证书：

```bash
# 安装Certbot
sudo apt-get install certbot python3-certbot-nginx

# 获取证书
sudo certbot --nginx -d your-domain.com

# 自动续期
sudo certbot renew --dry-run
```

### 3. 访问控制（可选）

添加基本认证：

```bash
# 安装工具
sudo apt-get install apache2-utils

# 创建密码文件
sudo htpasswd -c /etc/nginx/.htpasswd admin

# 在nginx配置中添加
auth_basic "Restricted Access";
auth_basic_user_file /etc/nginx/.htpasswd;
```

---

## 监控和维护

### 查看系统资源

```bash
# CPU和内存
htop

# 磁盘使用
df -h

# Docker容器资源
docker stats
```

### 备份数据

```bash
# 手动备份
./deploy/backup.sh

# 查看备份
ls -lh backups/

# 恢复备份
cp backups/newapi_warehouse_YYYYMMDD_HHMMSS.db.gz ./
gunzip newapi_warehouse_YYYYMMDD_HHMMSS.db.gz
mv newapi_warehouse_YYYYMMDD_HHMMSS.db newapi_warehouse.db
```

---

## 更新升级

### 更新代码

```bash
# 拉取最新代码
git pull origin main

# Docker部署 - 重新构建
docker-compose down
docker-compose up -d --build

# 直接部署 - 重启Nginx
sudo systemctl reload nginx
```

### 更新数据

```bash
# 执行一次完整更新
python3 daily_update.py
```

---

## 卸载

### Docker部署

```bash
# 停止并删除容器
docker-compose down

# 删除镜像
docker rmi newapi-dashboard_app

# 删除项目文件
rm -rf /opt/newapi-dashboard
```

### 直接部署

```bash
# 删除Nginx配置
sudo rm /etc/nginx/sites-enabled/newapi-dashboard
sudo rm /etc/nginx/sites-available/newapi-dashboard
sudo systemctl reload nginx

# 删除定时任务
crontab -e  # 删除相关行

# 删除项目文件
rm -rf /opt/newapi-dashboard
```

---

## 更多帮助

- 📖 [完整部署文档](DEPLOYMENT.md)
- 📖 [定时任务配置](CRON_SETUP.md)
- 📖 [开发文档](开发文档.md)
- 📖 [使用文档](使用文档.md)
- 📖 [问题解答](看板问题解答文档.md)

---

**部署完成后，访问 `http://your-server-ip` 查看数据看板！** 🎉
