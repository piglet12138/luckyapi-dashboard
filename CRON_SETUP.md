# 每日增量更新定时任务配置

## 方案1: Linux Cron (推荐)

### 1. 编辑crontab

```bash
crontab -e
```

### 2. 添加定时任务

每天凌晨2点执行更新：

```cron
# NewAPI数据仓库每日更新
0 2 * * * cd /path/to/newapi_export && /usr/bin/python3 daily_update.py >> logs/cron.log 2>&1
```

### 3. 查看定时任务

```bash
crontab -l
```

### 4. 查看执行日志

```bash
tail -f logs/daily_update.log
tail -f logs/cron.log
```

---

## 方案2: systemd Timer (Linux)

### 1. 创建服务文件

创建 `/etc/systemd/system/newapi-daily-update.service`：

```ini
[Unit]
Description=NewAPI Data Warehouse Daily Update
After=network.target

[Service]
Type=oneshot
User=your_username
WorkingDirectory=/path/to/newapi_export
ExecStart=/usr/bin/python3 /path/to/newapi_export/daily_update.py
StandardOutput=append:/path/to/newapi_export/logs/systemd.log
StandardError=append:/path/to/newapi_export/logs/systemd.log

[Install]
WantedBy=multi-user.target
```

### 2. 创建定时器文件

创建 `/etc/systemd/system/newapi-daily-update.timer`：

```ini
[Unit]
Description=NewAPI Data Warehouse Daily Update Timer
Requires=newapi-daily-update.service

[Timer]
OnCalendar=daily
OnCalendar=02:00
Persistent=true

[Install]
WantedBy=timers.target
```

### 3. 启用定时器

```bash
sudo systemctl daemon-reload
sudo systemctl enable newapi-daily-update.timer
sudo systemctl start newapi-daily-update.timer
```

### 4. 查看定时器状态

```bash
sudo systemctl status newapi-daily-update.timer
sudo systemctl list-timers --all
```

### 5. 手动触发

```bash
sudo systemctl start newapi-daily-update.service
```

---

## 方案3: Windows Task Scheduler

### 1. 创建批处理文件

创建 `daily_update.bat`：

```batch
@echo off
cd /d C:\path\to\newapi_export
python daily_update.py >> logs\cron.log 2>&1
```

### 2. 打开任务计划程序

- 开始菜单搜索"任务计划程序"
- 或运行 `taskschd.msc`

### 3. 创建基本任务

1. 点击"创建基本任务"
2. 名称：NewAPI Daily Update
3. 触发器：每天
4. 时间：凌晨2:00
5. 操作：启动程序
6. 程序：`C:\path\to\newapi_export\daily_update.bat`

### 4. 高级设置

- 勾选"如果错过计划开始时间，立即启动任务"
- 勾选"如果任务失败，重新启动间隔：5分钟，尝试次数：3"

---

## 方案4: Docker + Cron

如果使用Docker部署，可以在容器内配置cron：

### Dockerfile 添加：

```dockerfile
# 安装cron
RUN apt-get update && apt-get install -y cron

# 添加cron任务
RUN echo "0 2 * * * cd /app && python3 daily_update.py >> /app/logs/cron.log 2>&1" | crontab -

# 启动cron
CMD cron && tail -f /dev/null
```

---

## 监控和告警

### 1. 邮件通知（Linux）

修改 `daily_update.py`，添加邮件发送功能：

```python
import smtplib
from email.mime.text import MIMEText

def send_email_notification(subject, message):
    """发送邮件通知"""
    msg = MIMEText(message)
    msg['Subject'] = subject
    msg['From'] = 'your_email@example.com'
    msg['To'] = 'admin@example.com'

    try:
        server = smtplib.SMTP('smtp.example.com', 587)
        server.starttls()
        server.login('your_email@example.com', 'password')
        server.send_message(msg)
        server.quit()
        logger.info("邮件通知已发送")
    except Exception as e:
        logger.error(f"邮件发送失败: {e}")
```

### 2. Slack通知

```python
import requests

def send_slack_notification(message):
    """发送Slack通知"""
    webhook_url = "https://hooks.slack.com/services/YOUR/WEBHOOK/URL"
    payload = {"text": message}

    try:
        response = requests.post(webhook_url, json=payload)
        if response.status_code == 200:
            logger.info("Slack通知已发送")
    except Exception as e:
        logger.error(f"Slack通知失败: {e}")
```

### 3. 日志监控

使用 `logwatch` 或 `fail2ban` 监控日志：

```bash
# 安装logwatch
sudo apt-get install logwatch

# 配置监控规则
# /etc/logwatch/conf/logfiles/newapi.conf
```

---

## 测试定时任务

### 手动测试

```bash
# 进入项目目录
cd /path/to/newapi_export

# 创建日志目录
mkdir -p logs

# 手动执行
python3 daily_update.py

# 查看日志
cat logs/daily_update.log
```

### 模拟定时执行

使用 `at` 命令模拟未来某个时间执行：

```bash
# 5分钟后执行
echo "cd /path/to/newapi_export && python3 daily_update.py" | at now + 5 minutes

# 查看计划任务
atq

# 查看任务详情
at -c <job_id>
```

---

## 常见问题

### 1. Python环境问题

如果使用虚拟环境：

```bash
# 激活虚拟环境后执行
source /path/to/venv/bin/activate
python daily_update.py
```

或在cron中指定完整路径：

```cron
0 2 * * * cd /path/to/newapi_export && /path/to/venv/bin/python daily_update.py
```

### 2. 权限问题

确保文件有执行权限：

```bash
chmod +x daily_update.py
chmod +x daily_update.bat  # Windows
```

### 3. 路径问题

使用绝对路径：

```python
# 在脚本开头
import os
os.chdir('/path/to/newapi_export')
```

---

## 最佳实践

1. **日志轮转**: 防止日志文件过大

```bash
# 使用logrotate
# /etc/logrotate.d/newapi

/path/to/newapi_export/logs/*.log {
    daily
    rotate 30
    compress
    delaycompress
    missingok
    notifempty
}
```

2. **备份数据库**: 每次更新前备份

```python
import shutil
from datetime import datetime

def backup_database():
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    src = 'newapi_warehouse.db'
    dst = f'backups/newapi_warehouse_{timestamp}.db'
    shutil.copy2(src, dst)
    logger.info(f"数据库备份: {dst}")
```

3. **健康检查**: 定期检查数据完整性

```python
def health_check():
    """健康检查"""
    db = Database()
    db.connect()

    # 检查最新数据
    cursor = db.execute("SELECT MAX(stat_date) FROM ads_daily_summary")
    latest_date = cursor.fetchone()[0]

    if latest_date != datetime.now().strftime('%Y-%m-%d'):
        logger.warning(f"数据可能不是最新的: {latest_date}")

    db.close()
```

---

**配置完成后，数据仓库将每天自动更新！**
