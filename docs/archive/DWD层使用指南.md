# DWD层使用指南

**更新时间**: 2026-03-14

---

## 📋 概述

DWD层（Data Warehouse Detail，数据明细层）是数据仓库的清洗层，包含：
- ✅ **数据清洗**：时间戳转换、JSON解析、字段标准化
- ✅ **数据脱敏**：用户名、邮箱、IP地址等敏感信息脱敏
- ✅ **数据增强**：时间维度、充值金额提取、Token汇总

**重要**：日常分析请使用DWD层数据，避免直接查询ODS层原始数据。

---

## 🚀 快速开始

### 1. 初始化DWD层

首次使用需要创建DWD层表结构并转换数据：

```bash
python init_dwd.py
```

**执行内容**：
- 创建 `dwd_logs` 表（日志明细，脱敏）
- 创建 `dwd_users` 表（用户明细，脱敏）
- 将ODS层数据转换并加载到DWD层

**预计耗时**：5-10分钟（取决于数据量）

### 2. 查询DWD层数据

```python
import sqlite3
import pandas as pd

# 连接数据库
conn = sqlite3.connect('newapi_warehouse.db')

# 查询日志数据（脱敏）
df_logs = pd.read_sql("""
    SELECT * FROM dwd_logs
    WHERE log_date >= '2026-03-01'
    LIMIT 100
""", conn)

# 查询用户数据（脱敏）
df_users = pd.read_sql("""
    SELECT * FROM dwd_users
    WHERE status = 1
""", conn)

conn.close()
```

---

## 📊 DWD层表结构

### dwd_logs - 日志明细表（脱敏）

| 字段 | 类型 | 说明 | 脱敏 |
|------|------|------|------|
| **log_id** | BIGINT | 日志ID（主键） | - |
| **user_id** | INT | 用户ID | - |
| **log_date** | DATE | 日志日期 | - |
| **log_datetime** | DATETIME | 日志时间 | - |
| **log_type** | INT | 日志类型（1=充值, 2=消费, 3=管理, 4=错误） | - |
| **username_masked** | VARCHAR | 用户名 | ✅ 脱敏为 user_{user_id} |
| **ip_masked** | VARCHAR | IP地址 | ✅ 脱敏为 xxx.xxx.*.* |
| **request_id_masked** | VARCHAR | 请求ID | ✅ 保留前8位 |
| model_name | VARCHAR | 模型名称 | - |
| channel_id | INT | 渠道ID | - |
| quota | BIGINT | 配额消耗 | - |
| prompt_tokens | INT | 提示Token数 | - |
| completion_tokens | INT | 完成Token数 | - |
| total_tokens | INT | 总Token数 | - |
| topup_amount | DECIMAL | 充值金额（type=1时） | - |
| log_hour | INT | 小时（0-23） | - |
| log_weekday | INT | 星期（0-6） | - |
| log_month | INT | 月份（1-12） | - |
| log_year | INT | 年份 | - |

### dwd_users - 用户明细表（脱敏）

| 字段 | 类型 | 说明 | 脱敏 |
|------|------|------|------|
| **user_id** | INT | 用户ID（主键） | - |
| **username_masked** | VARCHAR | 用户名 | ✅ 脱敏为 user_{user_id} |
| **email_masked** | VARCHAR | 邮箱 | ✅ 脱敏为 user_{user_id}@domain.com |
| **display_name_masked** | VARCHAR | 显示名称 | ✅ 脱敏 |
| role | INT | 角色（1=管理员, 100=普通用户） | - |
| status | INT | 状态（1=启用, 2=禁用） | - |
| group_name | VARCHAR | 分组名称 | - |
| quota | BIGINT | 配额余额 | - |
| used_quota | BIGINT | 已使用配额 | - |
| request_count | INT | 请求次数 | - |
| first_use_date | DATE | 首次使用日期 | - |
| last_use_date | DATE | 最后使用日期 | - |

---

## 🔒 脱敏规则

### 1. 用户名脱敏
```
原始: stone.liu
脱敏: user_1007
```

### 2. 邮箱脱敏
```
原始: freelz940219@gmail.com
脱敏: user_1007@gmail.com
```
保留域名，便于分析邮箱域名分布。

### 3. IP地址脱敏
```
原始: 192.168.1.100
脱敏: 192.168.*.*
```
保留前两段，便于分析地域分布。

### 4. 请求ID脱敏
```
原始: 20260313124013176119058vznGNpIL
脱敏: 20260313************************
```
保留前8位（日期部分）。

---

## 📝 常用查询示例

### 1. 每日活跃用户数（DAU）

```sql
SELECT
    log_date,
    COUNT(DISTINCT user_id) as dau
FROM dwd_logs
WHERE log_type = 2  -- 消费日志
GROUP BY log_date
ORDER BY log_date DESC
LIMIT 30;
```

### 2. 用户消费统计

```sql
SELECT
    user_id,
    username_masked,
    COUNT(*) as call_count,
    SUM(quota) as total_quota,
    SUM(total_tokens) as total_tokens
FROM dwd_logs
WHERE log_type = 2
GROUP BY user_id, username_masked
ORDER BY total_quota DESC
LIMIT 20;
```

### 3. 模型使用分布

```sql
SELECT
    model_name,
    COUNT(*) as call_count,
    COUNT(DISTINCT user_id) as user_count,
    SUM(total_tokens) as total_tokens
FROM dwd_logs
WHERE log_type = 2
GROUP BY model_name
ORDER BY call_count DESC;
```

### 4. 充值统计

```sql
SELECT
    log_date,
    COUNT(*) as topup_count,
    SUM(topup_amount) as total_amount
FROM dwd_logs
WHERE log_type = 1
GROUP BY log_date
ORDER BY log_date DESC;
```

### 5. 时段分析

```sql
SELECT
    log_hour,
    COUNT(*) as call_count,
    COUNT(DISTINCT user_id) as user_count
FROM dwd_logs
WHERE log_type = 2
GROUP BY log_hour
ORDER BY log_hour;
```

---

## 🔄 增量更新

当ODS层有新数据时，运行增量转换：

```bash
python src/etl/ods_to_dwd.py
```

脚本会自动检测DWD层已有数据，只转换新增的记录。

---

## ⚠️ 注意事项

### 1. 数据访问规范

- ✅ **推荐**：日常分析使用DWD层数据
- ❌ **避免**：直接查询ODS层原始数据（包含敏感信息）

### 2. 数据一致性

- DWD层数据来源于ODS层
- 如果ODS层数据有更新，需要重新运行ETL转换
- 建议每日定时运行增量转换

### 3. 性能优化

- DWD层已创建常用索引
- 大数据量查询建议添加日期范围过滤
- 使用 `EXPLAIN QUERY PLAN` 分析查询性能

---

## 📈 下一步

DWD层完成后，可以继续构建：

1. **DWS层**（数据汇总层）
   - 用户每日汇总
   - 模型每日汇总
   - 用户生命周期

2. **ADS层**（应用数据层）
   - 每日汇总指标
   - 增长漏斗
   - 用户分层

3. **数据看板**
   - 可视化展示
   - 自动更新

---

## 🛠️ 故障排查

### 问题1：转换失败

```bash
# 检查ODS层数据
sqlite3 newapi_warehouse.db "SELECT COUNT(*) FROM ods_logs;"

# 检查DWD层表是否存在
sqlite3 newapi_warehouse.db ".tables"
```

### 问题2：数据不一致

```bash
# 清空DWD层重新转换
sqlite3 newapi_warehouse.db "DELETE FROM dwd_logs; DELETE FROM dwd_users;"
python init_dwd.py
```

---

**文档版本**: v1.0
**最后更新**: 2026-03-14
