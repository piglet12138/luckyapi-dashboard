# 部署完成说明

## 部署位置

- **项目目录**: `/root/newapi_export`
- **看板静态文件**: `/root/newapi_export/dashboard/`
- **数据库**: `/root/newapi_export/newapi_warehouse.db`

## 当前运行方式

看板已通过 Python 内置 HTTP 服务在 **端口 8080** 提供访问：

- **本机访问**: http://127.0.0.1:8080
- **局域网/外网访问**: http://<服务器IP>:8080

如需长期运行或开机自启，可安装为 systemd 服务：

```bash
sudo cp /root/newapi_export/deploy/newapi-dashboard.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable newapi-dashboard
sudo systemctl start newapi-dashboard
sudo systemctl status newapi-dashboard
```

（若当前已用 `python3 -m http.server` 在前台运行，先 Ctrl+C 停止后再用 systemd 启动。）

## 每日数据更新

项目已包含数据库和看板数据。若需每日从 API 拉取新数据并更新看板：

```bash
cd /root/newapi_export
python3 daily_update.py
```

配置定时任务（每天凌晨 2 点执行）：

```bash
crontab -e
# 添加一行：
0 2 * * * cd /root/newapi_export && /usr/bin/python3 daily_update.py >> /root/newapi_export/logs/cron.log 2>&1
```

## API 配置（可选）

若需修改 API 地址、Token 等，可设置环境变量或改代码中的默认值：

- 环境变量：`NEWAPI_BASE_URL`、`NEWAPI_TOKEN`、`NEWAPI_USER_ID`、`NEWAPI_DB_PATH`
- 或直接编辑：`/root/newapi_export/src/core/config.py`

## 使用 Docker 部署（可选）

若之后安装 Docker，可用项目自带的编排一键启动（含 Nginx）：

```bash
cd /root/newapi_export
docker-compose up -d
# 看板将监听 80 端口
```

## 更多文档

- 完整部署与维护：`SERVER_DEPLOYMENT_GUIDE.md`
- 快速上手：`QUICKSTART.md`
- 部署细节：`DEPLOYMENT.md`
