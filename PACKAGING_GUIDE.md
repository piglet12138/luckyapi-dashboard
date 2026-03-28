# 项目打包和传输指南

**打包前最后检查**

---

## ✅ 打包前清理检查

已完成的清理：
- ✅ Python缓存文件已清理（__pycache__, *.pyc）
- ✅ 临时文件已清理（*.swp, *~, .DS_Store）
- ✅ 文档已整理完成
- ✅ 脚本已检查和优化

---

## 📦 打包方法

### 方式1: 使用tar（推荐）

**在当前目录（newapi_export）的父目录执行**:

```bash
# Windows (Git Bash / WSL)
cd /c/Users/87975/Desktop
tar --exclude-from=newapi_export/.packignore -czf newapi_export.tar.gz newapi_export/

# 检查压缩包大小
ls -lh newapi_export.tar.gz
```

**预计大小**: 约500-600MB（包含数据库）

### 方式2: 排除数据库（如果服务器要重新同步）

```bash
cd /c/Users/87975/Desktop
tar --exclude='newapi_export/newapi_warehouse.db' \
    --exclude-from=newapi_export/.packignore \
    -czf newapi_export_no_db.tar.gz newapi_export/
```

**预计大小**: 约1-2MB（不含数据库）

### 方式3: 手动压缩（Windows）

使用7-Zip或WinRAR：
1. 右键点击 `newapi_export` 文件夹
2. 选择"添加到压缩文件..."
3. 排除以下内容：
   - `__pycache__` 文件夹
   - `*.pyc` 文件
   - `.env` 文件（敏感信息）
   - `logs/*.log`（可选）
   - `backups/*.gz`（可选）

---

## 📋 打包清单

### 必须包含的文件

**核心代码**:
- ✅ `src/` - 所有源代码
- ✅ `dashboard/` - 看板文件
- ✅ `deploy/` - 部署脚本
- ✅ `daily_update.py` - 每日更新主脚本
- ✅ `export_dashboard_data.py` - 数据导出脚本

**配置文件**:
- ✅ `requirements.txt` - Python依赖
- ✅ `.env.example` - 环境变量模板
- ✅ `Dockerfile` - Docker镜像配置
- ✅ `docker-compose.yml` - Docker编排
- ✅ `.packignore` - 打包排除列表

**文档**:
- ✅ `README.md` - 项目介绍
- ✅ `SERVER_DEPLOYMENT_GUIDE.md` - **服务器部署指南（重要）**
- ✅ `QUICKSTART.md` - 快速启动
- ✅ `DEPLOYMENT.md` - 详细部署
- ✅ `CRON_SETUP.md` - 定时任务配置
- ✅ `项目完成总结.md` - 完整总结
- ✅ `部署和更新方案总结.md` - 部署总结
- ✅ 其他*.md文档

**Shell脚本**:
- ✅ `deploy.sh` - 一键部署脚本
- ✅ `deploy/backup.sh` - 备份脚本
- ✅ `deploy/entrypoint.sh` - Docker启动脚本
- ✅ `deploy/nginx.conf` - Nginx配置

**数据**（可选）:
- ⚠️ `newapi_warehouse.db` - 数据库（504MB）
  - 如果服务器有API访问，可以不传，到服务器重新同步
  - 如果想直接使用现有数据，建议包含

**目录结构**:
- ✅ `logs/` - 日志目录（可以是空的）
- ✅ `backups/` - 备份目录（可以是空的）

### 可以排除的文件

**自动排除**（.packignore已配置）:
- ❌ `__pycache__/` - Python缓存
- ❌ `*.pyc`, `*.pyo` - 编译文件
- ❌ `.env` - 环境变量（包含密钥，不要传输！）
- ❌ `.vscode/`, `.idea/` - IDE配置
- ❌ `*.swp`, `*~` - 临时文件
- ❌ `.DS_Store`, `Thumbs.db` - 系统文件

**可选排除**:
- ⚠️ `logs/*.log` - 日志文件（服务器会重新生成）
- ⚠️ `backups/*.gz` - 备份文件（服务器会重新生成）
- ⚠️ `newapi_warehouse.db` - 数据库（如果服务器重新同步）

---

## 📤 上传到服务器

### 上传后解压

```bash
# SSH登录到服务器
ssh user@your-server.com

# 创建目录
sudo mkdir -p /opt/newapi_export
sudo chown $USER:$USER /opt/newapi_export

# 上传压缩包（从本地执行，或使用SFTP/SCP工具）
# scp newapi_export.tar.gz user@your-server.com:/opt/

# 在服务器上解压
cd /opt
tar -xzf newapi_export.tar.gz

# 检查文件
cd newapi_export
ls -la
```

### 设置权限

```bash
# 设置脚本可执行权限
chmod +x deploy.sh
chmod +x deploy/*.sh

# 创建日志和备份目录
mkdir -p logs backups
```

---

## 🔍 解压后检查

```bash
# 进入项目目录
cd /opt/newapi_export

# 检查文件完整性
echo "检查核心文件..."
ls -l daily_update.py
ls -l export_dashboard_data.py
ls -l src/sync/sync_incremental.py
ls -l dashboard/index.html
ls -l SERVER_DEPLOYMENT_GUIDE.md

# 检查Python依赖文件
echo "检查依赖文件..."
cat requirements.txt

# 检查数据库（如果包含）
echo "检查数据库..."
ls -lh newapi_warehouse.db 2>/dev/null || echo "数据库不存在，需要同步"

# 检查目录结构
echo "目录结构："
tree -L 2 -d  # 如果有tree命令
# 或
find . -maxdepth 2 -type d
```

---

## 🚀 下一步：开始部署

解压完成后，请按照 **SERVER_DEPLOYMENT_GUIDE.md** 开始部署：

```bash
# 阅读部署指南
cat SERVER_DEPLOYMENT_GUIDE.md

# 或使用less查看
less SERVER_DEPLOYMENT_GUIDE.md
```

**快速部署**:
```bash
# 方式1: Docker部署（推荐）
cp .env.example .env
vim .env  # 配置API信息
docker-compose up -d

# 方式2: 一键部署
./deploy.sh

# 方式3: 手动部署
# 参考 SERVER_DEPLOYMENT_GUIDE.md 的详细步骤
```

---

## 📝 重要提醒

### ⚠️ 敏感信息检查

打包前确保以下敏感信息已移除：
- ❌ `.env` - 包含API密钥（已在.packignore中排除）
- ❌ `config.py` 中的硬编码密钥（需要在服务器重新配置）
- ❌ 任何包含密码、token的文件

### ✅ 服务器配置

到服务器后需要配置：
1. **API连接信息**:
   - BASE_URL
   - TOKEN
   - USER_ID

2. **服务器信息**:
   - SERVER_NAME（域名）
   - Nginx配置
   - 防火墙规则

3. **定时任务**:
   - crontab配置
   - 日志轮转

### 📖 文档位置

给服务器Claude的文档：
- **主要**: `SERVER_DEPLOYMENT_GUIDE.md` - 完整部署和维护指南
- **备用**: `QUICKSTART.md` - 快速启动
- **参考**: `DEPLOYMENT.md` - 详细部署文档

---

## 🎯 压缩包验证

打包完成后检查：

```bash
# 查看压缩包大小
ls -lh newapi_export.tar.gz

# 查看压缩包内容（不解压）
tar -tzf newapi_export.tar.gz | head -50

# 检查是否包含敏感文件（不应该出现）
tar -tzf newapi_export.tar.gz | grep -E '\.env$|\.key$|\.pem$'

# 统计文件数
tar -tzf newapi_export.tar.gz | wc -l
```

**预期结果**:
- 包含100-200个文件
- 大小：500-600MB（含数据库）或 1-2MB（不含数据库）
- 不包含 .env 文件
- 不包含 __pycache__ 目录

---

## ✅ 打包完成清单

打包前确认：
- [ ] 已清理Python缓存
- [ ] 已清理临时文件
- [ ] 已检查不包含.env文件
- [ ] 已确认包含所有必要文档
- [ ] 已确认包含SERVER_DEPLOYMENT_GUIDE.md
- [ ] 已确认所有脚本有可执行权限
- [ ] 压缩包大小合理
- [ ] 已验证压缩包内容

**准备就绪！可以上传到服务器了。** 🚀
