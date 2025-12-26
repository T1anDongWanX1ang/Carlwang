# KOL 推文配置修复总结

## 📋 修改内容

### 1. 配置文件修改 (`config/config.json`)

#### ✅ 恢复 KOL 推文配置
```json
{
  "api": {
    "default_params": {
      "list_id": "1896516371435122886",           // ✅ 恢复原始 KOL List ID
      "list_ids": ["1896516371435122886"],        // ✅ KOL 推文 List
      "list_ids_kol": ["1896516371435122886"],    // ✅ 新增：明确的 KOL 配置
      "list_ids_project": [                        // ✅ 保留项目推文配置
        "1996848536520897010",
        "1996863048959820198",
        "1996887049027440697"
      ]
    }
  },

  "api_twitterapi": {
    "default_params": {
      "list_id": "1896516371435122886",           // ✅ 同步 KOL 配置
      "list_ids": ["1896516371435122886"],
      "list_ids_kol": ["1896516371435122886"],
      "list_ids_project": [
        "1996848536520897010",
        "1996863048959820198",
        "1996887049027440697"
      ]
    }
  },

  "database": {
    "tables": {
      "tweet": "twitter_tweet",                      // ✅ 恢复原始表名
      "tweet_kol": "twitter_tweet",                  // ✅ KOL 推文表
      "tweet_project": "twitter_tweet_back_test_cmc300", // ✅ 项目推文表
      "user": "twitter_user"
    }
  }
}
```

---

### 2. API 切换 (`src/crawler.py`)

#### ✅ 默认使用 Twitter API
```python
# 修改前：默认使用 TweetScout
if os.getenv("TWITTER_API_BACKEND", "").lower() == "twitterapi":
    from .api.twitter_api_twitterapi import twitter_api as selected_api_client
else:
    from .api.twitter_api import twitter_api as selected_api_client

# 修改后：默认使用 Twitter API
if os.getenv("TWITTER_API_BACKEND", "twitterapi").lower() == "tweetscout":
    from .api.twitter_api import twitter_api as selected_api_client
else:
    from .api.twitter_api_twitterapi import twitter_api as selected_api_client
```

---

### 3. 服务脚本更新 (`daily_kol_tweet_crawler/start_service_kol_tweet.sh`)

#### ✅ 添加环境变量设置
```bash
# macOS
caffeinate -i nohup bash -c "cd '$PROJECT_ROOT' && \
  export TWITTER_API_BACKEND=twitterapi && \
  '$PROJECT_ROOT/venv/bin/python' '$PROJECT_ROOT/main.py' --mode schedule" > "$LOG_FILE" 2>&1 &

# Linux
nohup nice -n -5 bash -c "cd '$PROJECT_ROOT' && \
  export TWITTER_API_BACKEND=twitterapi && \
  '$PROJECT_ROOT/venv/bin/python' '$PROJECT_ROOT/main.py' --mode schedule" > "$LOG_FILE" 2>&1 &

# 单次执行
cd "$PROJECT_ROOT" && \
  export TWITTER_API_BACKEND=twitterapi && \
  "$PROJECT_ROOT/venv/bin/python" "$PROJECT_ROOT/main.py" --mode once
```

---

## 🔍 字段映射说明

### Twitter API → 系统内部格式

字段映射已在 `src/api/twitter_api_twitterapi.py:_convert_twitterapi_format()` 中处理：

| Twitter API 字段 | 系统字段 | 说明 |
|-----------------|---------|------|
| `id` | `id_str` | 推文ID |
| `text` | `full_text` | 推文内容 |
| `createdAt` | `created_at` | 创建时间 |
| `likeCount` | `favorite_count` | 点赞数 |
| `retweetCount` | `retweet_count` | 转发数 |
| `replyCount` | `reply_count` | 回复数 |
| `quoteCount` | `quote_count` | 引用数 |
| `bookmarkCount` | `bookmark_count` | 书签数 |
| `viewCount` | `view_count` | 浏览数 |
| `conversationId` | `conversation_id_str` | 对话ID |
| `inReplyToId` | `in_reply_to_status_id_str` | 回复推文ID |
| `author.id` | `kol_id` | 用户ID |
| `author.userName` | `screen_name` | 用户名 |
| `author.name` | `name` | 显示名称 |
| `author.profilePicture` | `avatar` | 头像 |
| `author.followers` | `followers_count` | 关注者数 |

**✅ 字段映射自动完成，无需手动配置！**

---

## 📊 验证结果

运行 `python test_kol_config.py` 的测试结果：

```
【1. API 配置】
  ✅ 基础 URL: https://api.twitterapi.io
  ✅ Endpoint: /twitter/list/tweets
  ✅ KOL List IDs: ['1896516371435122886']
  ✅ 项目 List IDs: ['1996848536520897010', '1996863048959820198', '1996887049027440697']

【2. 数据库配置】
  ✅ 推文表: twitter_tweet
  ✅ KOL 推文表: twitter_tweet
  ✅ 项目推文表: twitter_tweet_back_test_cmc300

【3. 环境变量】
  ✅ TWITTER_API_BACKEND: twitterapi

【4. API 客户端】
  ✅ API 客户端类型: TwitterAPITwitterAPIClient

【✅ 所有配置检查通过】
```

---

## 🚀 使用方法

### 方式1：使用服务脚本（推荐）

```bash
cd /Users/qmk/Documents/QC/twitter/Carlwang/daily_kol_tweet_crawler

# 单次执行（测试）
./start_service_kol_tweet.sh once

# 定时服务
./start_service_kol_tweet.sh start

# 查看状态
./start_service_kol_tweet.sh status

# 查看日志
./start_service_kol_tweet.sh logs 50
```

### 方式2：直接使用 Python

```bash
cd /Users/qmk/Documents/QC/twitter/Carlwang

# 设置环境变量
export TWITTER_API_BACKEND=twitterapi

# 单次执行
python main.py --mode once --max-pages 5 --hours-limit 3

# 定时调度
python main.py --mode schedule --interval 60 --max-pages 50
```

---

## 📁 数据流向

```
┌─────────────────────────────────────────┐
│  Twitter List: 1896516371435122886     │
│  (KOL 推文 List)                        │
└─────────────┬───────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────┐
│  Twitter API                            │
│  https://api.twitterapi.io              │
│  /twitter/list/tweets                   │
└─────────────┬───────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────┐
│  字段映射转换                            │
│  _convert_twitterapi_format()          │
│  (自动处理)                              │
└─────────────┬───────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────┐
│  数据库存储                              │
│  表名: twitter_tweet                    │
│  (KOL 推文数据)                         │
└─────────────────────────────────────────┘
```

---

## ⚠️ 重要说明

### 区分不同的爬取服务

| 服务类型 | List IDs | 表名 | 用途 |
|---------|----------|------|------|
| **KOL 推文** | `1896516371435122886` | `twitter_tweet` | 爬取 KOL 的推文 |
| **项目推文** | `1996848536520897010`<br>`1996863048959820198`<br>`1996887049027440697` | `twitter_tweet_back_test_cmc300` | 爬取项目官方推文 |

### 环境变量说明

- `TWITTER_API_BACKEND=twitterapi`: 使用 Twitter API (新接口)
- `TWITTER_API_BACKEND=tweetscout`: 使用 TweetScout API (旧接口)

**默认值**: `twitterapi` ✅

---

## 🔧 故障排查

### 问题1: 数据存储到错误的表

**检查**:
```bash
python test_kol_config.py
```

**验证数据库**:
```sql
-- 应该在这个表中找到 KOL 推文数据
SELECT COUNT(*) FROM twitter_tweet;
SELECT * FROM twitter_tweet ORDER BY created_at DESC LIMIT 5;
```

### 问题2: API 调用失败

**检查日志**:
```bash
tail -100 daily_kol_tweet_crawler/service_kol_tweet.log
```

**常见错误**:
- API Key 无效: 检查 `config.json` 中的 `api_twitterapi.headers.X-API-Key`
- List ID 不存在: 确认 `1896516371435122886` 在 Twitter API 中有效

### 问题3: 字段映射错误

**验证字段**:
```sql
-- 检查推文数据结构
DESCRIBE twitter_tweet;

-- 查看实际数据
SELECT id_str, full_text, created_at, favorite_count, kol_id
FROM twitter_tweet
LIMIT 5;
```

---

## ✅ 验证清单

- [x] 配置文件已修改 (`config/config.json`)
- [x] API 切换已完成 (`src/crawler.py`)
- [x] 服务脚本已更新 (`daily_kol_tweet_crawler/start_service_kol_tweet.sh`)
- [x] 字段映射已确认
- [x] 测试配置已通过 (`test_kol_config.py`)
- [x] KOL List ID: `1896516371435122886` ✅
- [x] 数据库表名: `twitter_tweet` ✅
- [x] 使用 Twitter API: `twitterapi` ✅

---

## 📞 下一步

1. **测试单次爬取**:
   ```bash
   cd daily_kol_tweet_crawler
   ./start_service_kol_tweet.sh once
   ```

2. **验证数据**:
   ```sql
   SELECT COUNT(*) FROM twitter_tweet WHERE created_at > DATE_SUB(NOW(), INTERVAL 1 DAY);
   ```

3. **启动定时服务**:
   ```bash
   ./start_service_kol_tweet.sh start
   ```

4. **监控运行**:
   ```bash
   ./start_service_kol_tweet.sh logs 50
   ```

---

**修复完成时间**: 2025-12-26
**版本**: v1.0
