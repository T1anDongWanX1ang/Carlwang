# Twitter Marco 数据生成系统

基于推文数据生成衍生指标（情感分析和AI总结）的系统。

## 功能概述

该系统可以：
- 分析 KOL 推文的情感倾向，计算 0-100 的情感指数
- 基于最近4小时KOL推文数据生成AI总结
- 每30分钟自动生成一次Marco数据点
- 支持历史数据回填和实时数据生成
- 使用时间衰减权重，越新的推文权重越高

## 数据表结构

```sql
CREATE TABLE twitter_marco (
    `id` VARCHAR(50) NOT NULL COMMENT "主键，全局唯一标识符",
    `timestamp` DATETIME NOT NULL COMMENT "时间点，每30分钟记录一次",
    `sentiment_index` FLOAT NULL COMMENT "整个Crypto推特情绪得分[0,100]，基于KOL100指数推文计算",
    `summary` TEXT NULL COMMENT "AI总结，基于近4小时KOL推文的事件聚类和观点总结",
    `update_time` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT "记录更新时间"
)
ENGINE=OLAP
UNIQUE KEY(`id`, `timestamp`)
DISTRIBUTED BY HASH(`id`) BUCKETS 10
PROPERTIES (
    "replication_allocation" = "tag.location.default: 1"
);
```

## 算法说明

### 情感指数计算 (sentiment_index)

基于最近4小时KOL推文数据计算：

1. **时间窗口**：获取最近4小时内的有效推文（is_valid=1）
2. **推文级别情感分析**：使用ChatGPT分析每条推文的情感（bullish/bearish/neutral）
3. **权重系统**：
   - 影响力权重：基于KOL的真实粉丝数
   - 时间衰减权重：0-0.5小时(1.0) > 0.5-1小时(0.95) > 1-2小时(0.85) > 2-3小时(0.75) > 3-4小时(0.6)
   - 互动权重：基于推文的转发、点赞、评论数
4. **情感指数公式**：50 + (Bullish权重总和 - Bearish权重总和) / 总权重 × 50

### AI总结生成 (summary)

1. **数据来源**：基于最近4小时内的重要推文
2. **重要推文筛选**：根据影响力权重、互动量和内容质量评分选择前30条
3. **智能总结**：使用ChatGPT分析KOL观点，生成市场总结
4. **结构化输出**：包含热点话题、市场态度、技术观点、风险提醒等

## 安装和配置

### 1. 依赖安装

```bash
pip install -r requirements.txt
```

### 2. 配置检查

确认 `config/config.json` 中的 ChatGPT API 配置：

```json
{
  "chatgpt": {
    "api_key": "your-openai-api-key-here",
    "model": "gpt-3.5-turbo",
    "timeout": 30,
    "max_retries": 3
  }
}
```

## 使用指南

### 1. 创建数据表

```bash
python create_marco_table.py
```

### 2. 测试连接

```bash
python generate_marco_data.py --mode test
```

### 3. 生成最新数据

```bash
# 生成当前30分钟对齐时间点的Marco数据
python generate_marco_data.py --mode latest
```

### 4. 回填历史数据

```bash
# 回填最近7天的数据
python generate_marco_data.py --mode backfill --days 7

# 回填最近30天的数据
python generate_marco_data.py --mode backfill --days 30
```

### 5. 指定时间段生成

```bash
# 生成特定时间段的数据
python generate_marco_data.py --mode period \
  --start "2024-01-01 00:00" \
  --end "2024-01-07 23:59"

# 强制重新生成（覆盖已存在的数据）
python generate_marco_data.py --mode period \
  --start "2024-01-01 00:00" \
  --end "2024-01-07 23:59" \
  --force
```

### 6. 查看统计信息

```bash
python generate_marco_data.py --mode stats
```

## 命令行参数

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--mode` | 运行模式：latest/backfill/period/stats/test | latest |
| `--days` | 回填天数 | 7 |
| `--start` | 开始日期 (YYYY-MM-DD HH:MM) | - |
| `--end` | 结束日期 (YYYY-MM-DD HH:MM) | - |
| `--force` | 强制重新生成已存在的数据 | false |
| `--log-level` | 日志级别：DEBUG/INFO/WARNING/ERROR | INFO |

## 运行示例

### 推荐的定时任务配置

```bash
# 生产环境：每30分钟生成一次最新Marco数据（基于最近4小时推文）
*/30 * * * * cd /path/to/twitter-crawler && python run_marco.py

# 备用：每天凌晨回填昨天的数据（防止遗漏）
0 1 * * * cd /path/to/twitter-crawler && python run_marco.py today

# 或者使用原始脚本（更多参数控制）
*/30 * * * * cd /path/to/twitter-crawler && python generate_marco_data.py --mode latest
0 1 * * * cd /path/to/twitter-crawler && python generate_marco_data.py --mode backfill --days 1
```

### 手动生成示例

```bash
# 生成2024年1月1日全天的Marco数据
python generate_marco_data.py --mode period \
  --start "2024-01-01 00:00" \
  --end "2024-01-01 23:59"

# 查看生成结果
python generate_marco_data.py --mode stats
```

## 监控和维护

### 日志文件

- 日志文件：`logs/twitter_crawler.log`
- 日志级别：INFO（可通过 `--log-level` 调整）

### 性能优化

- 每次处理最多50条推文进行情感分析（避免API过度使用）
- 请求间隔2秒（避免触发API限制）
- 筛选重要推文进行总结（提高质量）

### 错误处理

- 自动跳过无效推文
- 重试机制（API失败时）
- 详细的错误日志记录

## API 使用说明

### Marco数据模型

```python
from src.models.marco import MarcoData

# 创建Marco数据
marco_data = MarcoData.create_for_timestamp(
    timestamp=datetime.now(),
    sentiment_index=75.5,
    summary="市场总结文本..."
)
```

### Marco数据访问

```python
from src.database.marco_dao import marco_dao

# 插入数据
success = marco_dao.insert(marco_data)

# 查询最新数据
latest_records = marco_dao.get_latest(10)

# 按时间范围查询
records = marco_dao.get_by_timestamp_range(start_time, end_time)
```

### Marco数据处理

```python
from src.utils.marco_processor import marco_processor

# 生成Marco数据
marco_data = marco_processor.process_tweets_to_marco(timestamp)
```

## 故障排除

### 常见问题

1. **ChatGPT API 配额不足**
   - 检查API key是否有效
   - 调整处理频率
   - 检查账户余额

2. **数据库连接失败**
   - 确认数据库配置正确
   - 检查网络连接
   - 验证用户权限

3. **没有找到KOL数据**
   - 确认 kols 表中有数据
   - 检查KOL的影响力评分
   - 验证推文数据的时间范围

### 调试模式

```bash
# 开启详细日志
python generate_marco_data.py --mode latest --log-level DEBUG
```

## 注意事项

1. **API 限制**：ChatGPT API 有请求限制，避免过于频繁的调用
2. **数据质量**：情感分析依赖于推文内容质量和KOL数据准确性
3. **时间对齐**：所有时间戳都按30分钟对齐（00:00, 00:30, 01:00...）
4. **去重保护**：系统会自动跳过已存在的时间戳，使用 `--force` 可覆盖

## 技术架构

```
推文数据 (twitter_tweet)
    ↓
KOL筛选 (kols表)
    ↓
Marco处理器 (marco_processor)
    ├── 情感分析 (ChatGPT API)
    └── AI总结 (ChatGPT API)
    ↓
Marco数据 (twitter_marco)
```

## 更新日志

- **v1.0.0** - 初始版本，支持情感分析和AI总结生成
- 基于 derived-metrics-calculation-details.md 中的算法实现
- 支持多种运行模式和时间范围处理 