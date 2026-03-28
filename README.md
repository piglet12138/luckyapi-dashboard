# NewAPI 数据仓库项目

**版本**: v2.0
**状态**: ✅ 已完成（含每日自动更新）
**更新时间**: 2026-03-15

---

## 项目简介

NewAPI 数据仓库项目为 NewAPI 服务构建了完整的数据分析体系，包括四层数据仓库架构（ODS → DWD → DWS → ADS）和可视化数据看板，支持业务指标监控、用户行为分析和渠道效果评估。

### 核心功能

- ✅ 四层数据仓库（ODS/DWD/DWS/ADS）
- ✅ **每日增量自动更新**（新）
- ✅ 数据脱敏和隐私保护
- ✅ 业务指标计算和分析
- ✅ 数据可视化看板（双Tab布局）
- ✅ 用户增长和留存分析
- ✅ 渠道归因和效果评估
- ✅ **新用户转化率分析**（Phase 2）
- ✅ **分层复购率分析**（Phase 2）

### 技术栈

- **数据库**: SQLite
- **开发语言**: Python 3.8+
- **前端框架**: Bootstrap 5 + ECharts 5
- **数据格式**: JSON

---

## 快速开始

### 1. 环境要求

- Python 3.8+
- SQLite 3
- 现代浏览器（Chrome/Firefox/Safari）

### 2. 查看数据看板

**本地访问**:

```bash
cd dashboard
python -m http.server 8000
```

然后在浏览器中访问：`http://localhost:8000`

### 3. 每日更新数据（推荐）

**自动更新** - 一键完成所有流程：

```bash
# 执行每日增量更新（包含API数据同步）
python daily_update.py
```

此脚本会自动完成：
1. 从API增量同步新数据
2. ETL处理（ODS → DWD → DWS → ADS）
3. 导出看板数据

**配置定时任务**（每天自动更新）：

```bash
# Linux/Mac
crontab -e
# 添加：每天凌晨2点执行
0 2 * * * cd /path/to/newapi_export && python3 daily_update.py >> logs/cron.log 2>&1
```

详见 [CRON_SETUP.md](CRON_SETUP.md)

### 4. 手动更新数据（可选）

如果只需要重新计算指标，不同步API数据：

```bash
python export_dashboard_data.py
```

---

## 项目结构

```
newapi_export/
├── README.md                      # 项目说明
├── 开发文档.md                    # 开发指南（技术人员）
├── 使用文档.md                    # 使用指南（业务人员）
├── 数据字典.md                    # 字段说明
│
├── export_dashboard_data.py       # 看板数据导出脚本
├── init_ads.py                    # ADS层初始化
├── init_dwd.py                    # DWD层初始化
├── init_dws.py                    # DWS层初始化
│
├── newapi_warehouse.db            # 数据仓库数据库
│
├── src/                           # 源代码
│   ├── core/                      # 核心模块
│   │   ├── database.py           # 数据库管理
│   │   └── data_masking.py       # 数据脱敏
│   └── etl/                       # ETL脚本
│       ├── ods_to_dwd.py         # ODS → DWD
│       ├── dwd_to_dws.py         # DWD → DWS
│       └── dws_to_ads.py         # DWS → ADS
│
├── dashboard/                     # 数据看板
│   ├── index.html                # 看板页面
│   └── dashboard_data.json       # 看板数据
│
└── docs/                          # 文档
    └── archive/                   # 历史文档归档
```

---

## 数据仓库架构

### 分层设计

```
原始数据
   ↓
ODS层（原始数据层）
   ↓ 数据清洗 + 脱敏
DWD层（明细数据层）
   ↓ 数据汇总
DWS层（汇总数据层）
   ↓ 指标计算
ADS层（应用数据层）
   ↓ JSON导出
数据看板
```

### 数据规模

| 层级 | 主要表 | 记录数 | 说明 |
|------|--------|--------|------|
| ODS | ods_logs | 486,195 | 原始日志 |
| DWD | dwd_logs | 486,195 | 脱敏后日志 |
| DWS | dws_user_daily | 3,078 | 用户每日汇总 |
| DWS | dws_user_lifecycle | 1,082 | 用户生命周期 |
| DWS | dws_model_daily | 1,532 | 模型每日汇总 |
| ADS | ads_daily_summary | 73 | 每日核心指标 |
| ADS | ads_funnel_daily | 73 | 增长漏斗 |
| ADS | ads_user_segment_daily | 229 | 用户分层 |
| ADS | ads_activation_analysis | 5 | 激活点分析 |
| ADS | ads_channel_attribution | 184 | 渠道归因 |

---

## 核心业务指标

### 最新指标（2026-03-14）

| 指标 | 数值 | 说明 |
|------|------|------|
| DAU | 64 | 日活跃用户数 |
| 总调用次数 | 4,642 | 当日API调用 |
| 累计收入 | $66,817 | 总充值金额 |
| 转化率 | 29.69% | 付费转化率 |

### 关键发现

1. **激活临界点**: 15次调用
   - <15次：转化率<18%
   - 15-50次：转化率41.67%
   - >50次：转化率>63%

2. **高价值用户**: >100次调用
   - 占用户15.6%
   - 转化率92.31%
   - 人均收入$380.41

3. **最佳渠道**: Claude Sonnet 4-6
   - 171个用户
   - 转化率54.29%

4. **重度用户**: 贡献93%收入

---

## 文档指南

### 面向不同角色

| 角色 | 推荐文档 | 说明 |
|------|---------|------|
| **业务人员** | [使用文档.md](使用文档.md) | 看板使用、指标解读、常用查询 |
| **数据分析师** | [使用文档.md](使用文档.md) + [数据字典.md](数据字典.md) | 数据分析和SQL查询 |
| **开发人员** | [开发文档.md](开发文档.md) | 技术架构、开发指南、扩展开发 |
| **数据工程师** | [开发文档.md](开发文档.md) + [数据字典.md](数据字典.md) | ETL流程、性能优化 |

### 核心文档

- **[开发文档.md](开发文档.md)**: 完整的技术文档，包含架构设计、模块说明、ETL流程、扩展开发指南
- **[使用文档.md](使用文档.md)**: 完整的使用指南，包含看板使用、指标解读、常用查询、最佳实践
- **[数据字典.md](数据字典.md)**: 所有表和字段的详细说明

### 历史文档

项目开发过程中的评估报告、建设总结等文档已归档到 `docs/archive/` 目录。

---

## 使用场景

### 日常监控

```bash
# 每日更新看板数据
python export_dashboard_data.py

# 启动看板服务
cd dashboard && python -m http.server 8000
```

### 数据分析

```bash
# 连接数据库
sqlite3 newapi_warehouse.db

# 查询核心指标
SELECT * FROM ads_daily_summary ORDER BY stat_date DESC LIMIT 7;

# 查询用户分层
SELECT * FROM dws_user_lifecycle WHERE user_segment = '3_重度';
```

### 自定义分析

参考 [开发文档.md](开发文档.md) 中的"扩展开发"章节，了解如何：
- 添加新的业务指标
- 创建自定义图表
- 实现增量更新

---

## 数据更新

### 手动更新

```bash
python export_dashboard_data.py
```

### 自动更新（推荐）

**Linux/Mac**:

```bash
# 编辑crontab
crontab -e

# 添加定时任务（每日凌晨2点）
0 2 * * * cd /path/to/newapi_export && python export_dashboard_data.py
```

**Windows**:

使用"任务计划程序"创建每日定时任务。

---

## 数据隐私

项目实现了完整的数据脱敏机制：

- **用户名**: `user_1007` 格式
- **邮箱**: `user_1007@domain.com` 格式
- **IP地址**: `192.168.*.*` 格式

所有敏感信息在DWD层已完成脱敏处理。

---

## 性能指标

- **数据处理**: 486,195条日志，处理时间<5分钟
- **看板加载**: <1秒
- **数据库大小**: ~150MB
- **查询响应**: 大部分查询<100ms

---

## 常见问题

### Q: 如何查看最新数据？

A: 运行 `python export_dashboard_data.py` 更新数据，然后刷新看板页面。

### Q: 数据多久更新一次？

A: 建议配置每日自动更新。数据是T+1，今天看到的是昨天的数据。

### Q: 如何导出数据到Excel？

A: 使用SQLite命令导出CSV，然后用Excel打开：

```bash
sqlite3 newapi_warehouse.db
.mode csv
.output data.csv
SELECT * FROM ads_daily_summary;
.quit
```

### Q: 如何添加新的分析指标？

A: 参考 [开发文档.md](开发文档.md) 的"扩展开发"章节。

---

## 项目历史

### v1.0 (2026-03-14)

- ✅ 完成四层数据仓库建设
- ✅ 实现数据脱敏机制
- ✅ 开发数据可视化看板
- ✅ 完成用户增长和留存分析
- ✅ 实现渠道归因分析
- ✅ 编写完整的开发和使用文档

### 数据统计

- 日志记录: 486,195条
- 用户数量: 1,082个
- 时间范围: 2026-01-01 ~ 2026-03-14
- 数据完整性: 100%

---

## 技术支持

### 获取帮助

1. 查看 [使用文档.md](使用文档.md) 了解常见问题
2. 查看 [开发文档.md](开发文档.md) 了解技术细节
3. 查看 [数据字典.md](数据字典.md) 了解字段说明

### 反馈建议

欢迎提出功能需求和改进建议：
- 看板功能优化
- 新增分析指标
- 性能优化建议
- 文档改进建议

---

## 许可证

本项目仅供内部使用。

---

**项目维护**: 数据团队
**最后更新**: 2026-03-14
**版本**: v1.0
