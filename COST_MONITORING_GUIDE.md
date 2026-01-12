# 成本监控系统使用指南

## 概述

成本监控系统现已升级，支持将 API 成本统计数据记录到 `tp_alarm.api_cost_tracking` 数据库表中，方便长期跟踪和分析。

## 系统架构

```
监控脚本 (monitor_daily_cost.sh)
    ↓
解析日志文件，提取统计数据
    ↓
显示统计报告（终端输出）
    ↓
调用 Python 记录器 (cost_db_logger.py)
    ↓
写入数据库 (tp_alarm.api_cost_tracking)
```

## 三个 Daily 项目

### 1. KOL Following 服务
**位置**: `daily_kol_following_crawler/monitor_daily_cost.sh`

**监控内容**:
- API 调用次数
- 缓存命中次数
- KOL 处理统计（成功/失败/跳过）
- Following 数据统计
- 总成本和平均成本

**使用方法**:
```bash
cd daily_kol_following_crawler
./monitor_daily_cost.sh
```

**记录字段**:
- `task_name`: "kol_following"
- `total_requests`: API 调用次数
- `tweets_fetched`: 新增入库的 Following 数量
- `error_count`: 失败的 KOL 数量
- `metadata`: 包含 success_kols, total_kols, cache_hits

---

### 2. KOL Tweet 服务
**位置**: `daily_kol_tweet_crawler/monitor_daily_cost.sh`

**监控内容**:
- API 调用次数
- 推文获取统计
- 智能早停触发次数
- 总成本和平均成本
- 每条推文成本

**使用方法**:
```bash
cd daily_kol_tweet_crawler
./monitor_daily_cost.sh
```

**记录字段**:
- `task_name`: "kol_tweet"
- `total_requests`: API 请求次数
- `tweets_fetched`: 获取的推文数量
- `error_count`: 失败的运行次数

---

### 3. Project Tweet 服务
**位置**: `daily_tweet_crawler/monitor_daily_cost.sh`

**监控内容**:
- 运行次数统计
- 推文获取和入库统计
- 总成本和平均成本
- 月成本预估

**使用方法**:
```bash
cd daily_tweet_crawler
./monitor_daily_cost.sh
```

**记录字段**:
- `task_name`: "project_tweet"
- `total_requests`: 估算的 API 请求次数
- `tweets_fetched`: 获取的推文数量
- `error_count`: 0（暂无错误统计）

---

## 数据库记录器

### Python 脚本位置
`src/utils/cost_db_logger.py`

### 命令行用法
```bash
python cost_db_logger.py \
    --task-name "任务名称" \
    --run-id "运行ID" \
    --total-requests 100 \
    --total-cost 1.5 \
    --tweets-fetched 2000 \
    --error-count 5 \
    --success-kols 50 \
    --total-kols 60 \
    --cache-hits 10
```

### 参数说明
| 参数 | 必填 | 说明 |
|------|------|------|
| `--task-name` | ✓ | 任务名称（如 kol_following, kol_tweet, project_tweet） |
| `--run-id` | ✓ | 运行ID（格式: 20251231_120000） |
| `--total-requests` | ✓ | 总API调用次数 |
| `--total-cost` | ✓ | 总成本USD |
| `--tweets-fetched` | ✗ | 获取的推文/数据数量 |
| `--error-count` | ✗ | 错误次数 |
| `--list-ids` | ✗ | 列表ID |
| `--success-kols` | ✗ | 成功处理的KOL数量 |
| `--total-kols` | ✗ | 总KOL数量 |
| `--cache-hits` | ✗ | 缓存命中次数 |

### 作为 Python 模块使用
```python
from src.utils.cost_db_logger import CostDBLogger

logger = CostDBLogger()
success = logger.log_cost(
    task_name="kol_following",
    run_id="20251231_120000",
    total_requests=100,
    total_cost_usd=1.5,
    tweets_fetched=2000,
    error_count=5,
    metadata={
        "success_kols": 50,
        "total_kols": 60,
        "cache_hits": 10
    }
)
```

---

## 数据库表结构

### tp_alarm.api_cost_tracking

| 字段名 | 类型 | 说明 |
|--------|------|------|
| id | bigint | 主键 |
| timestamp | datetime | 记录时间 |
| task_name | varchar(100) | 任务名称 |
| run_id | varchar(50) | 运行ID |
| list_ids | varchar(500) | 列表ID（可选） |
| total_requests | int | 总API请求次数 |
| tweets_fetched | int | 获取的推文/数据数量 |
| error_count | int | 错误次数 |
| total_cost_usd | decimal(10,6) | 总成本USD |
| avg_cost_per_request | decimal(10,6) | 每次请求平均成本（自动计算） |
| cost_per_tweet | decimal(10,6) | 每条推文成本（自动计算） |
| server_host | varchar(100) | 服务器主机名 |
| success_rate | decimal(5,2) | 成功率（自动计算） |
| metadata | json | 元数据（JSON格式） |
| created_at | timestamp | 创建时间 |

---

## 查询示例

### 查看最近10条记录
```sql
SELECT
    timestamp,
    task_name,
    total_requests,
    total_cost_usd,
    tweets_fetched,
    avg_cost_per_request
FROM api_cost_tracking
ORDER BY timestamp DESC
LIMIT 10;
```

### 按任务分组统计
```sql
SELECT
    task_name,
    COUNT(*) as run_count,
    SUM(total_requests) as total_api_calls,
    SUM(total_cost_usd) as total_cost,
    SUM(tweets_fetched) as total_tweets,
    AVG(avg_cost_per_request) as avg_request_cost
FROM api_cost_tracking
GROUP BY task_name
ORDER BY total_cost DESC;
```

### 查看每日成本趋势
```sql
SELECT
    DATE(timestamp) as date,
    task_name,
    SUM(total_cost_usd) as daily_cost,
    SUM(total_requests) as daily_requests,
    SUM(tweets_fetched) as daily_tweets
FROM api_cost_tracking
WHERE timestamp >= DATE_SUB(NOW(), INTERVAL 30 DAY)
GROUP BY DATE(timestamp), task_name
ORDER BY date DESC, task_name;
```

### 查看某个任务的详细历史
```sql
SELECT
    timestamp,
    run_id,
    total_requests,
    total_cost_usd,
    tweets_fetched,
    success_rate,
    metadata
FROM api_cost_tracking
WHERE task_name = 'kol_following'
ORDER BY timestamp DESC
LIMIT 20;
```

---

## 功能特性

### ✅ 自动记录
- 每次运行 `monitor_daily_cost.sh` 时自动记录到数据库
- 不影响统计显示，即使数据库写入失败也会正常显示统计

### ✅ 自动计算
- `avg_cost_per_request`: 平均每次请求成本
- `cost_per_tweet`: 平均每条推文成本
- `success_rate`: 成功率百分比

### ✅ 元数据支持
- 使用 JSON 格式存储额外信息
- 支持灵活扩展

### ✅ 服务器追踪
- 自动记录服务器主机名
- 方便多服务器部署时的成本分析

---

## 故障排查

### 问题：数据库连接失败
**解决方法**:
1. 检查数据库凭证是否正确（在 `cost_db_logger.py` 中）
2. 检查网络连接
3. 确认数据库用户 `alarm_user` 有写入权限

### 问题：未找到 Python 记录器
**解决方法**:
1. 确认 `src/utils/cost_db_logger.py` 文件存在
2. 检查路径引用是否正确（相对于 monitor_daily_cost.sh 的位置）

### 问题：venv 找不到
**解决方法**:
1. 确保项目根目录下有 `venv` 虚拟环境
2. 如果使用其他 Python 环境，修改脚本中的 Python 路径

---

## 最佳实践

### 1. 定期清理旧数据
保留最近 90 天的数据，定期归档或删除旧记录：
```sql
DELETE FROM api_cost_tracking
WHERE timestamp < DATE_SUB(NOW(), INTERVAL 90 DAY);
```

### 2. 设置成本告警
基于每日成本设置告警阈值，及时发现异常：
```sql
SELECT
    DATE(timestamp) as date,
    SUM(total_cost_usd) as daily_cost
FROM api_cost_tracking
WHERE timestamp >= CURDATE()
GROUP BY DATE(timestamp)
HAVING daily_cost > 10.0;  -- 告警阈值：$10
```

### 3. 性能优化监控
定期检查平均成本，优化 API 使用效率：
```sql
SELECT
    task_name,
    AVG(cost_per_tweet) as avg_tweet_cost,
    AVG(avg_cost_per_request) as avg_request_cost
FROM api_cost_tracking
WHERE timestamp >= DATE_SUB(NOW(), INTERVAL 7 DAY)
GROUP BY task_name;
```

---

## 更新日志

### 2025-12-31
- ✅ 创建 `cost_db_logger.py` Python 模块
- ✅ 升级 `daily_kol_following_crawler/monitor_daily_cost.sh`
- ✅ 创建 `daily_kol_tweet_crawler/monitor_daily_cost.sh`
- ✅ 升级 `daily_tweet_crawler/monitor_daily_cost.sh`
- ✅ 添加数据库自动记录功能
- ✅ 支持元数据扩展
- ✅ 自动计算衍生指标
