# 推文拉取接口优化说明

## 📋 更新概述

本次更新优化了推文拉取接口的逻辑，添加了两个重要的限制条件，以提高数据质量和减少不必要的API调用。

## 🎯 主要改动

### 1. 分页限制：最多15页

**修改位置：** `src/api/twitter_api.py` - `fetch_tweets_with_pagination()`

**实现逻辑：**
```python
# 设置最大页数为15
if max_pages is None:
    max_pages = 15  # 强制最多15页
else:
    max_pages = min(max_pages, 15)  # 不超过15页
```

**说明：**
- 不论配置中设置多少页，实际最多只拉取15页
- 即使传入更大的 `max_pages` 值，也会自动限制在15页
- 默认情况下（不传参数），也是15页

### 2. 时间过滤：只拉取过去8小时的推文

**修改位置：** `src/api/twitter_api.py` - `fetch_tweets_with_pagination()`

**实现逻辑：**
```python
# 计算时间截止点（过去8小时）
time_cutoff = datetime.now() - timedelta(hours=hours_limit)

# 对每条推文进行时间检查
for tweet in tweets:
    created_at_str = tweet.get('created_at', '')
    if created_at_str:
        tweet_time = date_parser.parse(created_at_str)
        
        # 检查是否在时间范围内
        if tweet_time >= time_cutoff:
            valid_tweets.append(tweet)
        else:
            # 推文太旧，停止拉取
            stopped_by_time = True
            break
```

**说明：**
- 使用推文的 `created_at` 字段进行时间判断
- 只保留过去8小时内发布的推文
- 一旦遇到超过8小时的推文，立即停止拉取（不继续后续页）
- 使用 `dateutil.parser` 智能解析各种时间格式

## 📊 优化效果

### API调用优化

| 场景 | 优化前 | 优化后 | 改进 |
|------|--------|--------|------|
| 最大请求页数 | 100页 | 15页 | ✅ 85% ↓ |
| 推文时间范围 | 无限制 | 8小时 | ✅ 精准 |
| 无效数据过滤 | 事后过滤 | 实时过滤 | ✅ 及时 |

### 性能提升

**假设场景：** 每页100条推文，API间隔1秒

| 指标 | 优化前 | 优化后 | 改进 |
|------|--------|--------|------|
| 最大拉取时间 | ~100秒 | ~15秒 | ✅ 85% ↓ |
| 最大推文数 | 10000条 | 1500条 | ✅ 精简 |
| 有效数据率 | 不确定 | ~100% | ✅ 提高 |

## 🔧 代码修改详情

### 1. src/api/twitter_api.py

**新增导入：**
```python
from datetime import datetime, timedelta
from dateutil import parser as date_parser
```

**修改方法签名：**
```python
def fetch_tweets_with_pagination(
    self, 
    list_id: str = None, 
    max_pages: int = None, 
    page_size: int = None,
    hours_limit: int = 8  # 新增参数
) -> Generator[List[Dict[str, Any]], None, None]:
```

**关键改动：**
- 添加分页数量限制（最多15页）
- 添加时间过滤逻辑（默认8小时）
- 增加详细的日志记录
- 统计过滤掉的推文数量

### 2. src/crawler.py

**修改方法签名：**
```python
def crawl_tweets(
    self, 
    list_id: str = None, 
    max_pages: int = None, 
    page_size: int = None, 
    hours_limit: int = 8  # 新增参数
) -> bool:
```

**参数传递链：**
```
crawl_tweets() 
  → _fetch_api_data()
    → api_client.fetch_all_tweets()
      → api_client.fetch_tweets_with_pagination()
```

## 📝 使用示例

### 命令行使用

```bash
# 使用默认配置（15页，8小时限制）
./start_service.sh once

# 指定页数（会被限制在15页以内）
./start_service.sh once 20 100  # 实际只拉取15页

# 定时模式（每30分钟执行一次）
./start_service.sh start 30 5 20
```

### 代码调用

```python
from src.crawler import crawler

# 使用默认配置
crawler.crawl_tweets()

# 自定义配置
crawler.crawl_tweets(
    list_id='1896516371435122886',
    max_pages=10,      # 实际不超过15页
    page_size=100,
    hours_limit=8      # 只拉取过去8小时
)
```

## 🔍 日志示例

优化后的日志输出：

```
2025-11-06 20:30:00 - INFO - 开始爬取推文数据 (第 1 次，时间限制: 8小时)
2025-11-06 20:30:00 - INFO - 正在从API获取数据，list_id: 1896516371435122886, 时间限制: 8小时
2025-11-06 20:30:00 - INFO - 时间过滤: 只拉取 2025-11-06 12:30:00 之后的推文
2025-11-06 20:30:01 - INFO - 获取第 1 页数据（最多15页），每页 100 条
2025-11-06 20:30:02 - INFO - 第 1 页获取到 100 条推文，过滤后 95 条，累计 95 条有效推文
2025-11-06 20:30:03 - INFO - 获取第 2 页数据（最多15页），每页 100 条
2025-11-06 20:30:04 - INFO - 第 2 页获取到 100 条推文，过滤后 80 条，累计 175 条有效推文
2025-11-06 20:30:05 - INFO - 推文时间 2025-11-06 11:00:00 超过8小时限制，停止拉取
2025-11-06 20:30:05 - INFO - 已到达时间边界（8小时前），停止拉取
2025-11-06 20:30:05 - INFO - 分页获取完成，总共获取 175 条有效推文（过滤 25 条），共 2 页
```

## ⚠️ 注意事项

### 1. 时间格式兼容性

使用 `dateutil.parser` 可以解析多种时间格式：
- Twitter标准格式：`Wed Nov 06 20:30:00 +0000 2025`
- ISO格式：`2025-11-06T20:30:00Z`
- 简单格式：`2025-11-06 20:30:00`

### 2. 时区处理

- 所有时间比较都转换为本地时间（无时区）
- 如果推文时间带时区信息，会自动移除以便比较

### 3. 异常处理

- 如果推文缺少 `created_at` 字段，会保留该推文（并记录警告）
- 如果时间解析失败，会保留该推文（并记录警告）
- 确保不会因为个别推文的问题影响整体爬取

### 4. 性能考虑

- 一旦遇到超过时间限制的推文，立即停止拉取
- 不会浪费时间和资源拉取更多无效数据
- 对于高频更新的列表，可能只需要1-2页就足够

## 🔄 配置参数

虽然代码中有硬编码的限制，但可以通过参数调整：

```python
# 修改时间限制（小时）
crawler.crawl_tweets(hours_limit=12)  # 拉取过去12小时的推文

# 修改页数限制（但不会超过15页）
crawler.crawl_tweets(max_pages=10)    # 拉取10页

# 修改每页大小
crawler.crawl_tweets(page_size=50)    # 每页50条
```

## 📈 监控建议

### 关键指标

监控以下日志信息：

1. **时间过滤效果：**
   ```bash
   grep "已到达时间边界" service.log
   ```

2. **实际拉取页数：**
   ```bash
   grep "分页获取完成" service.log | tail -1
   ```

3. **过滤统计：**
   ```bash
   grep "过滤后" service.log | tail -10
   ```

### 优化建议

如果发现：
- **过滤数量很少：** 说明数据更新频率低，可以减少 `hours_limit`
- **经常到达15页限制：** 说明数据量大，可以增加每页大小
- **很少超过2-3页：** 说明时间过滤有效，配置合理

## 🚀 升级步骤

### 本地环境

```bash
# 1. 拉取最新代码
git pull origin main

# 2. 测试单次执行
./start_service.sh once 5 100

# 3. 查看日志确认
tail -100 service.log | grep "时间过滤"

# 4. 重启定时服务
./start_service.sh restart 30 5 20
```

### 远程服务器

```bash
# 1. SSH到服务器
ssh your-server

# 2. 进入项目目录
cd /path/to/twitter-crawler

# 3. 拉取最新代码
git pull origin main

# 4. 重启服务
./start_service.sh restart 30 5 20

# 5. 验证日志
tail -f service.log | grep -E "(时间限制|时间过滤|时间边界)"
```

## ❓ FAQ

### Q1: 为什么是8小时而不是24小时？

A: 8小时是基于以下考虑：
- 每30分钟执行一次，8小时内有16次机会捕获数据
- 加密货币话题变化快，8小时的数据已经足够分析
- 减少无效数据的处理，提高效率

### Q2: 如果需要更长的时间范围怎么办？

A: 可以通过参数调整：
```python
crawler.crawl_tweets(hours_limit=24)  # 24小时
```

### Q3: 15页是否足够？

A: 对于8小时的时间窗口：
- 15页 × 100条 = 1500条推文
- 平均每小时187条推文
- 通常在到达15页前就会因时间过滤停止

### Q4: 会不会漏掉重要数据？

A: 不会，因为：
- 定时执行（每30分钟）确保及时捕获
- 8小时窗口有足够的重叠
- 数据库会自动去重

## 📞 问题反馈

如有疑问或需要调整参数，请联系开发团队。

---

**最后更新:** 2025-11-06  
**版本:** v1.0  
**状态:** ✅ 已上线

