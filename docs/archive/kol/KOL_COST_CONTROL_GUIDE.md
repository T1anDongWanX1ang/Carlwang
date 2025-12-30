# KOL 推文爬取成本控制指南

## 📊 关键参数说明

### 1️⃣ 默认配置（`daily_kol_tweet_crawler/start_service_kol_tweet.sh`）

```bash
DEFAULT_INTERVAL=60         # 定时服务：每60分钟运行一次
DEFAULT_MAX_PAGES=50        # ⚠️ 请求50页，但实际最多只会拉15页（硬限制）
DEFAULT_PAGE_SIZE=100       # 每页最多100条（API限制）
DEFAULT_HOURS_LIMIT=3       # 只拉取过去3小时的推文
```

---

## ⚠️ 重要：硬编码限制（防止溢出）

### 代码中的保护机制（`src/api/twitter_api_twitterapi.py:330`）

```python
def fetch_tweets_with_pagination(self, max_pages=None, page_size=None, hours_limit=2):
    if max_pages is None:
        max_pages = 15
    else:
        max_pages = min(max_pages, 15)  # ✅ 硬限制：最多15页

    if page_size is None:
        page_size = 100
    page_size = min(page_size or 100, 100)  # ✅ 硬限制：最多100条/页
```

**✅ 安全保障**：
- 即使你设置 `--max-pages 50`，实际也只会拉取 **最多15页**
- 每页最多 100 条推文
- **绝对最大值**: 15 页 × 100 条/页 = 1,500 条推文/次

---

## 💰 成本计算

### Twitter API 计费规则
- **定价**: $0.15 per 1,000 tweets
- **最低收费**: 15 credits (即使0或1条推文)
- **示例**:
  - 4条推文 = 60 credits
  - 2条推文 = 30 credits
  - 1条推文 = 15 credits (最低)

### 成本估算

#### 单次执行成本
```
场景1: 拉取1,500条推文（15页 × 100条）
成本 = 1,500 / 1,000 × $0.15 = $0.225 (约0.23美元)

场景2: 拉取500条推文（5页 × 100条）
成本 = 500 / 1,000 × $0.15 = $0.075 (约0.08美元)

场景3: 拉取100条推文（1页 × 100条）
成本 = 100 / 1,000 × $0.15 = $0.015 (约0.02美元)
```

#### 定时服务成本（每60分钟运行一次）
```
假设每次拉取500条推文：
- 每小时: $0.075
- 每天 (24次): $0.075 × 24 = $1.80
- 每月 (30天): $1.80 × 30 = $54.00
```

---

## 🎯 你的问题答案

### Q1: 测试单次是一次性运行三个小时吗？
**A**: ❌ **不是运行三个小时**，而是：
- 拉取**过去3小时内发布的推文**
- 然后程序就**立即结束**
- 运行时间取决于数据量和网络速度，通常**几分钟内完成**

### Q2: 改到哪里了？
**A**: ✅ 是的，主要修改在：
```
/Users/qmk/Documents/QC/twitter/Carlwang/daily_kol_tweet_crawler/
├── start_service_kol_tweet.sh  ← 已添加环境变量设置
└── (使用主项目的 config.json 和 Python 代码)
```

### Q3: 会抓取多少页？
**A**: 这取决于以下因素：
1. **你的设置**: 默认 `DEFAULT_MAX_PAGES=50`
2. **硬限制**: 代码强制最多 **15 页**
3. **时间过滤**: 只拉取过去 **3 小时**的推文
4. **智能停止**: 如果3小时内推文少于15页，会**提前停止**

**实际场景**:
- 如果 KOL List（`1896516371435122886`）在过去3小时内只有200条推文
  → 实际只拉取 **2页** (200条)
- 如果过去3小时内有2000条推文
  → 实际拉取 **15页** (1500条，剩余500条被丢弃)

### Q4: 最多抓取多少页？
**A**: ✅ **硬限制：15页**
- 即使你设置 `--max-pages 1000`，代码也会限制为15页
- 这是在 `src/api/twitter_api_twitterapi.py:338` 强制执行的

### Q5: 会不会溢出？
**A**: ✅ **不会溢出**，有多重保护：

1. **硬编码限制**: 最多15页
2. **时间过滤**: 自动过滤超过3小时的推文
3. **智能停止**: 如果没有更多数据，自动停止

### Q6: 有没有检测功能？
**A**: ✅ **有完整的成本追踪和监控**

#### 实时成本追踪
代码中有成本计算功能：
```python
self.total_cost = 0.0  # 累计成本（美元）
self.cost_per_1000_tweets = 0.15

def _calculate_request_cost(self, tweet_count):
    return (tweet_count / 1000) * 0.15
```

#### 获取统计信息
```python
stats = api_client.get_request_stats()
# 返回:
# {
#     'total_requests': 15,           # 总请求数
#     'tweets_fetched': 1500,         # 拉取的推文数
#     'total_cost_usd': 0.225,        # 总成本（美元）
#     'avg_cost_per_request': 0.015   # 平均每次请求成本
# }
```

---

## 🛡️ 成本控制建议

### 推荐配置（低成本模式）

#### 方案1: 保守模式（适合测试）
```bash
./start_service_kol_tweet.sh once 5 100 1
# 参数: 最大5页, 每页100条, 过去1小时
# 预计成本: ~$0.05 (约500条)
```

#### 方案2: 标准模式（日常使用）
```bash
./start_service_kol_tweet.sh once 10 100 3
# 参数: 最大10页, 每页100条, 过去3小时
# 预计成本: ~$0.10 (约1000条)
```

#### 方案3: 激进模式（数据完整性优先）
```bash
./start_service_kol_tweet.sh once 15 100 6
# 参数: 最大15页, 每页100条, 过去6小时
# 预计成本: ~$0.15-0.23 (约1000-1500条)
```

### 定时服务成本估算

#### 低频模式（推荐新手）
```bash
./start_service_kol_tweet.sh start 120 5 100 1
# 每2小时运行一次, 最多5页, 过去1小时
# 每天成本: $0.05 × 12 = $0.60
# 每月成本: $0.60 × 30 = $18.00
```

#### 标准模式（平衡）
```bash
./start_service_kol_tweet.sh start 60 10 100 3
# 每1小时运行一次, 最多10页, 过去3小时
# 每天成本: $0.10 × 24 = $2.40
# 每月成本: $2.40 × 30 = $72.00
```

#### 高频模式（数据实时性要求高）
```bash
./start_service_kol_tweet.sh start 30 5 100 1
# 每30分钟运行一次, 最多5页, 过去1小时
# 每天成本: $0.05 × 48 = $2.40
# 每月成本: $2.40 × 30 = $72.00
```

---

## 📈 成本监控工具

### 1. 查看实时成本
在日志中查看成本统计：
```bash
tail -100 daily_kol_tweet_crawler/service_kol_tweet.log | grep "成本\|cost\|tweets"
```

### 2. 使用成本监控脚本
如果你的项目中有 `monitor_daily_cost.sh`，可以使用：
```bash
cd daily_kol_tweet_crawler
./monitor_daily_cost.sh
```

### 3. 手动计算成本
创建一个简单的脚本：
```python
# 在日志中找到 "tweets_fetched" 的数量
tweets_fetched = 1500  # 示例
cost = (tweets_fetched / 1000) * 0.15
print(f"本次成本: ${cost:.4f}")
```

---

## 🚨 成本警告阈值

建议设置以下阈值：

| 警告级别 | 单次成本 | 每日成本 | 每月成本 | 建议操作 |
|---------|---------|---------|---------|---------|
| 🟢 正常 | < $0.10 | < $2.00 | < $60 | 继续运行 |
| 🟡 警告 | $0.10-0.20 | $2.00-5.00 | $60-150 | 监控并优化 |
| 🔴 超标 | > $0.20 | > $5.00 | > $150 | 立即调整参数 |

---

## 🔧 实际测试建议

### 第一步：小规模测试
```bash
cd /Users/qmk/Documents/QC/twitter/Carlwang/daily_kol_tweet_crawler

# 测试1: 最小成本测试（拉取1页）
./start_service_kol_tweet.sh once 1 100 1
# 预计成本: ~$0.002 (约15 credits，最低收费)
```

### 第二步：查看拉取数据
```sql
SELECT COUNT(*) as total_tweets,
       MIN(created_at) as oldest_tweet,
       MAX(created_at) as newest_tweet
FROM twitter_tweet
WHERE created_at > DATE_SUB(NOW(), INTERVAL 1 HOUR);
```

### 第三步：根据数据量调整参数
```bash
# 如果上述测试拉取了100条推文，说明1小时内数据很多
# 可以降低频率或减少页数

# 如果只拉取了10条推文，说明数据量小
# 可以增加时间范围
./start_service_kol_tweet.sh once 5 100 6
```

---

## ✅ 检查清单

在启动定时服务前，请确认：

- [ ] 已进行小规模测试（1-2页）
- [ ] 已验证数据正确存入 `twitter_tweet` 表
- [ ] 已计算预期每日成本
- [ ] 已设置成本警告阈值
- [ ] 已确认定时间隔合理
- [ ] 已了解硬限制（最多15页）
- [ ] 已配置日志监控

---

## 📞 成本优化技巧

1. **按需调整时间窗口**:
   - 如果 List 活跃度低 → 增加 `hours_limit` 到 6-12 小时
   - 如果 List 活跃度高 → 减少 `hours_limit` 到 1-2 小时

2. **动态调整频率**:
   - 高峰时段（白天）→ 每30分钟
   - 低峰时段（夜晚）→ 每2小时

3. **监控重复数据**:
   - 如果发现大量重复推文 → 减少运行频率
   - 如果发现数据断层 → 增加运行频率

4. **使用智能时间检测**:
   - 系统会自动过滤超时推文，避免浪费

---

**总结**：
✅ 单次测试成本: **$0.002 - $0.23** (取决于数据量)
✅ 硬限制保护: **最多15页 (1500条)**
✅ 完整成本追踪: **实时监控每次请求成本**
✅ 智能过滤: **自动停止拉取超时数据**

建议先用 `once 1` 测试，确认成本后再启动定时服务！
