# Twitter API 调用监控和成本控制指南

## 概述

本指南说明如何精确监控和控制 Twitter API 调用成本，特别是针对 `start_service_project_twitterapi.sh` 脚本。

## 重要发现

### 1. 为什么会有 KOL/项目数据查询？

即使 `start_service_project_twitterapi.sh` 只是爬取特定 list 的推文，启动时仍会看到以下数据库查询：

```
- 加载RootData项目名称失败
- 加载token symbol失败
- 获取所有KOL失败
- 刷新项目KOL缓存失败
```

**原因：** 这是代码架构导致的。在 `src/crawler.py` 中导入了多个 enricher 模块，这些模块在**导入时就会初始化**并尝试从数据库加载数据，即使项目推文爬取不使用这些数据。

**影响：**
- ✅ **不会产生额外的 Twitter API 成本**（这些只是数据库查询）
- ⚠️ 会增加启动时间（约3-4分钟等待数据库超时）
- ⚠️ 如果数据库连接有问题，会看到大量错误日志（但不影响 API 爬取功能）

**优化建议：** 未来可以考虑延迟加载（lazy loading）这些数据，但目前对 API 成本无影响。

---

## API 调用监控工具

### 已创建的监控工具

#### 1. **api_cost_monitor.py** - 核心监控工具

精确追踪 API 调用次数、推文数量和成本。

**功能：**
- 记录每次 Twitter API 和 ChatGPT API 调用
- 计算实时成本（可自定义定价）
- 生成日报表、月报表和累计报表
- 支持实时监控模式

**使用方法：**

```bash
# 查看今日统计
python3 api_cost_monitor.py --mode report --report-type today

# 查看本月统计
python3 api_cost_monitor.py --mode report --report-type month

# 查看累计统计
python3 api_cost_monitor.py --mode report --report-type total

# 完整报告（今日+本月+累计）
python3 api_cost_monitor.py --mode report --report-type all

# 实时监控（每5秒刷新）
python3 api_cost_monitor.py --mode watch --interval 5

# 重置统计数据
python3 api_cost_monitor.py --mode reset
```

#### 2. **api_stats.sh** - 快速查看工具

便捷的命令行工具，快速查看 API 调用统计。

**使用方法：**

```bash
# 快速查看调用次数
./api_stats.sh count

# 查看完整统计报告（推荐）
./api_stats.sh stats

# 查看今日统计
./api_stats.sh today

# 查看本月统计
./api_stats.sh month

# 查看累计统计
./api_stats.sh total

# 查看最近的 API 调用日志（默认20条）
./api_stats.sh log

# 查看最近50条调用日志
./api_stats.sh log 50

# 实时监控（每3秒刷新）
./api_stats.sh watch 3

# 重置统计数据
./api_stats.sh reset
```

---

## 增强的日志功能

### 代码改进

已在 `src/api/twitter_api_twitterapi.py` 中增加以下功能：

1. **实时请求计数：** 每次 API 调用都会记录请求编号
   ```
   [API调用] 请求 #1 | URL: https://... | 状态码: 200
   ```

2. **累计推文统计：** 实时显示已获取的推文总数
   ```
   获取 50 条推文 (累计: 150)
   ```

3. **爬取完成统计：** 在爬取结束时自动显示汇总
   ```
   ==========================================
   📊 API 调用统计
   ==========================================
   总请求次数: 5
   获取推文数: 234
   错误次数: 0
   成功率: 100.00%
   平均每次请求获取推文数: 46.8
   ==========================================
   ```

---

## 成本配置

在 `api_cost_monitor.py` 中可自定义成本定价（第14-27行）：

```python
COST_CONFIG = {
    'twitterapi': {
        'per_request': 0.001,        # 每次请求成本（美元）
        'per_100_tweets': 0.01,      # 每100条推文成本（美元）
        'daily_free_requests': 0,    # 每日免费请求数
        'monthly_quota': 10000,      # 月度配额（请求数）
    },
    'chatgpt': {
        'per_1k_tokens_input': 0.003,   # GPT-4 输入成本
        'per_1k_tokens_output': 0.006,  # GPT-4 输出成本
    }
}
```

**根据你的实际 API 定价调整这些值！**

---

## 测试脚本

### 配置问题

当前测试发现 `config/config.json` 中**缺少 `api_twitterapi` 配置**，导致：
```
请求失败 401: {"message":"ApiKey required"}
```

### 需要添加的配置

在 `config/config.json` 中添加以下配置（参考现有的 `api` 配置结构）：

```json
{
  "api_twitterapi": {
    "base_url": "https://api.tweetscout.io/v2",
    "headers": {
      "X-API-Key": "YOUR_API_KEY_HERE"
    },
    "default_params": {
      "list_ids_project": ["1896516371435122886"]
    },
    "pagination": {
      "page_size": 100
    },
    "timeout": 30,
    "retry_attempts": 3,
    "retry_delay": 5,
    "endpoints": {
      "list_tweets": "/list-tweets"
    }
  }
}
```

或者如果使用不同的 API 端点：

```json
{
  "api_twitterapi": {
    "base_url": "https://api.twitterapi.io",
    "headers": {
      "X-API-Key": "YOUR_TWITTERAPI_KEY"
    },
    "default_params": {
      "list_ids_project": ["1896516371435122886"]
    },
    "pagination": {
      "page_size": 100
    },
    "timeout": 30,
    "retry_attempts": 3,
    "retry_delay": 5,
    "endpoints": {
      "list_tweets": "/lists/{list_id}/tweets"
    }
  }
}
```

---

## 实际使用流程

### 1. 配置 API

确保 `config/config.json` 中有正确的 `api_twitterapi` 配置。

### 2. 小规模测试（推荐）

先用小参数测试，精确控制成本：

```bash
# 只抓取 2 页，每页 50 条，过去 20 分钟的数据
./service_scripts/start_service_project_twitterapi.sh once 2 50 0.34
```

**预期 API 调用：** 最多 2 次请求（如果 20 分钟内有数据的话）

### 3. 实时监控

在另一个终端窗口运行监控：

```bash
# 方式1：实时监控模式
./api_stats.sh watch 3

# 方式2：查看日志
./service_scripts/start_service_project_twitterapi.sh logs 50
```

### 4. 查看统计

测试完成后查看详细统计：

```bash
./api_stats.sh stats
```

输出示例：
```
======================================================================
Twitter API 成本监控报告
======================================================================

📅 今日统计 (2025-12-25)
----------------------------------------------------------------------
Twitter API:
  请求次数: 2
  推文数量: 87
  错误次数: 0
  成本: $0.0109

💰 今日总成本: $0.0109
```

### 5. 生产环境运行

确认成本可控后，启动定时服务：

```bash
# 每 15 分钟运行一次
./service_scripts/start_service_project_twitterapi.sh start 15 50 100 0.34

# 查看服务状态
./service_scripts/start_service_project_twitterapi.sh status

# 查看监控
./service_scripts/start_service_project_twitterapi.sh monitor
```

---

## 成本控制建议

### 参数说明

```bash
./service_scripts/start_service_project_twitterapi.sh once [页数] [每页条数] [小时限制]
```

- **页数**：最多抓取多少页（1页 = 1次 API 请求，最大 15）
- **每页条数**：每页多少条推文（最大 100，受 API 限制）
- **小时限制**：只抓取过去N小时的数据（默认 0.34 = 20分钟）

### 成本优化策略

1. **调整时间窗口：** 减少 `hours_limit` 可以减少重复数据
   ```bash
   # 只抓取过去 15 分钟的数据
   ./service_scripts/start_service_project_twitterapi.sh start 15 50 100 0.25
   ```

2. **限制页数：** 设置合理的 `max_pages`
   ```bash
   # 最多 3 页，即使有更多数据也停止
   ./service_scripts/start_service_project_twitterapi.sh once 3 100 0.34
   ```

3. **监控配额：** 定期检查月度配额使用率
   ```bash
   ./api_stats.sh month
   # 查看 "配额使用: X.XX%"
   ```

---

## 日志位置

- **服务日志：** `service_scripts/service_project_twitterapi.log`
- **API 统计：** `logs/api_stats.json`
- **监控日志：** `service_scripts/monitor_project.log`

---

## 常见问题

### Q: 为什么看到数据库连接错误？

**A:** 这些是 enricher 初始化时尝试加载辅助数据导致的。**不影响 API 爬取功能**，也不产生 API 成本。如果数据库正常，这些错误会消失。

### Q: 如何知道调用了几次 API？

**A:** 三种方式：
1. 查看日志中的 `[API调用] 请求 #N`
2. 运行 `./api_stats.sh count`
3. 运行 `./api_stats.sh stats`

### Q: 成本计算准确吗？

**A:** 需要在 `api_cost_monitor.py` 中配置你的实际 API 定价。默认值仅供参考。

### Q: 如何重置统计？

**A:** 运行 `./api_stats.sh reset` 或 `python3 api_cost_monitor.py --mode reset`

---

## 总结

✅ **已完成：**
1. 创建 API 成本监控工具（`api_cost_monitor.py`）
2. 创建快速查看脚本（`api_stats.sh`）
3. 增强日志输出，显示详细的 API 调用信息
4. 在爬取完成时自动显示统计摘要

⚠️ **待配置：**
1. 在 `config/config.json` 中添加 `api_twitterapi` 配置
2. 根据实际定价调整 `api_cost_monitor.py` 中的成本配置

🎯 **使用建议：**
1. 先用小参数测试（2页，50条）
2. 实时监控运行情况
3. 确认成本可控后再启动定时服务
4. 定期检查月度配额使用情况
