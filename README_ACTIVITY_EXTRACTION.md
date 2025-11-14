# 活动数据提取功能说明

## 概述

本系统已成功集成活动数据检测和结构化提取功能。活动数据将以JSON格式存储在数据库的`activity_detail`字段中。

## JSON数据结构

活动数据采用以下JSON格式（英文输出）：

```json
{
  "title": "Activity title (max 5 words)",
  "status": "Active",
  "summary": "Activity summary (max 20 words)",
  "time": "Tweet timestamp",
  "url": "Tweet URL"
}
```

### 字段说明

- **title**: 活动标题，5个词以内，简洁描述活动类型和项目
- **status**: 活动状态，默认为"Active"（当前进行中的活动）
- **summary**: 活动摘要，20个词以内，包含关键参与信息
- **time**: 推文发布时间
- **url**: 推文链接

## 功能特性

### 1. 自动集成到主爬虫流程

活动检测已集成到主爬虫流程（`src/crawler.py`），每次爬取新推文时会自动：
- 检测包含活动关键词的推文
- 使用AI判断是否为真正的活动
- 提取结构化JSON数据
- 更新数据库的`is_activity`和`activity_detail`字段

### 2. 支持的活动类型

系统可以识别以下活动类型：
- **campaign** - 营销活动
- **airdrop** - 空投
- **quest** - 任务活动
- **reward** - 奖励计划
- **giveaway** - 赠品活动
- **bounty** - 赏金计划
- **contest** - 竞赛

也支持中文关键词：空投、活动、奖励、赠送

### 3. 数据库字段

- `is_activity` (TINYINT): 0=普通推文, 1=活动推文
- `activity_detail` (JSON): 存储JSON格式的结构化活动数据

## 使用方法

### 方法1: 主爬虫自动处理（推荐）

活动检测已集成到主爬虫流程，启动爬虫即可自动检测新推文中的活动：

```bash
# 单次执行（包含活动检测）
python main.py --mode once

# 定时调度（每5分钟自动检测）
python main.py --mode schedule --interval 5
```

### 方法2: 回填历史数据

使用回填脚本处理历史推文：

```bash
# 回填最近48小时的数据
python backfill_activities_48h.py

# 回填最近24小时的数据
python backfill_activities_48h.py --hours 24

# 回填最近7天的数据
python backfill_activities_48h.py --hours 168

# 模拟运行（不修改数据库）
python backfill_activities_48h.py --dry-run

# 调整批处理大小
python backfill_activities_48h.py --batch-size 10
```

### 方法3: 测试功能

使用测试脚本验证活动提取功能：

```bash
# 运行测试（会调用OpenAI API）
python test_activity_extraction.py
```

## 数据查询示例

### 查询所有活动推文

```sql
SELECT id_str, full_text, activity_detail, created_at
FROM twitter_tweet
WHERE is_activity = 1
ORDER BY created_at DESC
LIMIT 100;
```

### 查询并解析JSON数据

```python
import json
from src.database.tweet_dao import tweet_dao
from datetime import datetime, timedelta

# 获取最近24小时的活动推文
cutoff_time = datetime.now() - timedelta(hours=24)
tweets = tweet_dao.get_recent_tweets(since_time=cutoff_time)

# 筛选活动推文并解析JSON
for tweet in tweets:
    if tweet.is_activity == 1 and tweet.activity_detail:
        try:
            activity_data = json.loads(tweet.activity_detail)
            print(f"标题: {activity_data['title']}")
            print(f"摘要: {activity_data['summary']}")
            print(f"链接: {activity_data['url']}")
            print()
        except json.JSONDecodeError:
            print(f"无法解析JSON: {tweet.id_str}")
```

## 工作流程

1. **关键词过滤**: 使用关键词快速过滤候选推文
2. **AI检测**: ChatGPT判断是否为真正的活动推文
3. **数据提取**: 提取结构化JSON数据（title, status, summary等）
4. **数据库更新**: 更新`is_activity=1`和`activity_detail`字段

## 性能和成本考虑

### API调用次数
每条活动推文需要 **2次 ChatGPT API调用**：
1. 活动检测（`detect_campaign_announcement`）
2. 数据提取（`extract_activity_structured_data`）

### 处理速度
- 脚本自动控制处理速度，批次之间休眠2秒
- 默认每批处理5条推文
- 100条推文预计需要3-5分钟

### 成本优化建议
1. 关键词过滤可以显著减少API调用
2. 合理设置时间范围，避免重复处理
3. 使用`--dry-run`先预览结果

## 新旧格式对比

### 旧格式（纯文本摘要）
```
Campaign Type: Staking Universe launch with DeAgentAI offering innovative staking solutions in the Sui ecosystem...
```

### 新格式（结构化JSON）
```json
{
  "title": "DeAgentAI Staking Launch",
  "status": "Active",
  "summary": "Staking Universe launch with rewards in Sui ecosystem",
  "time": "2024-12-01 10:00:00",
  "url": "https://twitter.com/projectx/status/123"
}
```

新格式的优势：
- 结构化，易于程序处理
- 字段明确，便于数据分析
- 包含推文链接，方便追溯
- 简洁明了，减少存储空间

## 故障排除

### 问题1: 脚本运行失败

检查以下配置：
- OpenAI API密钥是否正确（`config/config.json`）
- 数据库连接是否正常
- 是否有足够的API配额

### 问题2: 未检测到活动

可能原因：
- 推文不包含活动关键词
- AI判断该推文不是真正的活动
- 推文时间超出指定范围

### 问题3: JSON解析错误

如果遇到JSON解析错误，检查：
- ChatGPT返回的格式是否正确
- 数据库中的activity_detail字段是否完整
- 是否混合了新旧格式的数据

## 代码位置

- **ChatGPT方法**: `src/api/chatgpt_client.py:2014` - `extract_activity_structured_data()`
- **爬虫集成**: `src/crawler.py:425` - `_detect_and_structure_activities()`
- **回填脚本**: `backfill_activities_48h.py`
- **测试脚本**: `test_activity_extraction.py`

## 更新日志

### 2024-12-01
- ✅ 添加新的活动JSON结构化方法
- ✅ 集成活动检测到主爬虫流程
- ✅ 创建48小时数据回填脚本
- ✅ 创建测试脚本
- ✅ 完整文档和使用说明

## 技术支持

如有问题，请查看日志文件：
- 主爬虫日志: `logs/twitter_crawler.log`
- 回填脚本日志: 输出到控制台

或联系开发团队。
