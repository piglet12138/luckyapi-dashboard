# 脚本功能说明

## 核心脚本

### daily_update.py
**功能**：每日自动更新主脚本
- 增量同步API数据到ODS
- 执行完整ETL流程（ODS→DWD→DWS→ADS）
- 导出看板数据
- **运行方式**：cron每天凌晨2点自动执行
- **幂等性**：部分幂等，增量同步可能跳过缺失数据

### repair_data.py
**功能**：数据修复脚本（解耦设计）
- 检查ODS→DWD缺失并补齐
- 检查DWD→ADS缺失并重新计算
- 重新导出看板数据
- **运行方式**：手动执行 `python3 repair_data.py`
- **幂等性**：完全幂等，可重复运行

### export_dashboard_data.py
**功能**：从ADS层导出看板JSON数据
- 导出核心指标、趋势、用户分层等
- 输出到 `dashboard/dashboard_data.json`
- **运行方式**：被daily_update调用，或手动执行

## 数据同步脚本

### sync_by_time.py
**功能**：按时间范围同步数据
- 使用API的start_time/end_time参数
- 用于补齐特定时间段的缺失数据
- **运行方式**：`python3 sync_by_time.py '2026-03-26 18:00:00' '2026-03-27 00:00:00'`

### force_sync.py
**功能**：按ID范围强制同步（已废弃）
- 原计划按ID范围同步，但实现有问题
- 建议使用sync_by_time.py替代

## 数据补齐脚本

### backfill_data.py
**功能**：重新计算指定日期的DWD/ADS数据
- 删除指定日期的旧数据
- 从ODS重新转换到DWD
- 重新计算ADS指标
- **运行方式**：`python3 backfill_data.py 2026-03-27`
- **注意**：有bug，建议使用repair_data.py

## 初始化脚本

### init_dwd.py
**功能**：初始化DWD层表结构和数据

### init_dws.py
**功能**：初始化DWS层表结构和数据

### init_ads.py
**功能**：初始化ADS层表结构和数据

### start_dashboard.py
**功能**：启动看板HTTP服务器
- 在8080端口提供看板访问

## 推荐使用流程

### 日常运行
```bash
# 自动执行，无需手动
# cron: 0 2 * * * python3 daily_update.py
```

### 数据修复
```bash
# 检查并修复所有缺失数据
python3 repair_data.py
```

### 补齐特定时间段
```bash
# 补齐26号晚上的数据
python3 sync_by_time.py '2026-03-26 18:00:00' '2026-03-27 00:00:00'
# 然后运行修复
python3 repair_data.py
```

