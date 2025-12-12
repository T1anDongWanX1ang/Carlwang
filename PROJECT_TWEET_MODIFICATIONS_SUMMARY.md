# 项目推文拉取流程修改完成

## 修改内容总结

根据您的需求，已完成以下修改：

### 1. 数据入库表名修改 ✅
- **修改位置**: `src/crawler.py:792`
- **原表名**: `twitter_tweet_project_new`
- **新表名**: `twitter_tweet_back_test_cmc300`

### 2. 字段名修改：kol_id → user_id ✅
- **修改位置**: 
  - `src/models/tweet.py`: 添加了 `user_id` 字段
  - `src/database/tweet_dao.py:214`: 字段列表中将 `kol_id` 改为 `user_id`
  - `src/models/tweet.py:197`: `to_dict()` 方法中优先使用 `user_id`，向后兼容 `kol_id`

### 3. 新增 is_retweet 字段 ✅
- **检测逻辑**: `src/models/tweet.py:139-145`
  - 当API返回的 `retweeted_status` 不为 `null` 时，`is_retweet` 设置为 1
  - 否则设置为 0
- **字段映射**: 已添加到数据库表字段列表

### 4. 保存 user.screen_name 到 user_name 字段 ✅
- **提取逻辑**: `src/models/tweet.py:147-152`
- **API路径**: `api_data.user.screen_name` → `tweet.user_name`
- **字段映射**: 已添加到数据库表字段列表

### 5. 其他逻辑保持不变 ✅
- 智能时间检测功能保留
- UTC时间转换功能保留
- 项目推文简化处理流程保留
- 所有现有的API调用逻辑保持不变

## 核心代码修改点

### Tweet模型 (`src/models/tweet.py`)
```python
# 新增字段
user_id: Optional[str] = None  # 用户ID
user_name: Optional[str] = None  # 用户名 (screen_name)
is_retweet: Optional[int] = 0  # 是否为转推（0=否，1=是）

# from_api_data方法中的检测逻辑
retweeted_status = api_data.get('retweeted_status')
if retweeted_status is not None:
    mapped_data['is_retweet'] = 1
    mapped_data['tweet_type'] = 'RETWEET'
else:
    mapped_data['is_retweet'] = 0
    mapped_data['tweet_type'] = 'ORIGINAL'

# 提取用户信息
user_info = api_data.get('user', {})
if isinstance(user_info, dict):
    user_screen_name = user_info.get('screen_name')
    if user_screen_name:
        mapped_data['user_name'] = user_screen_name
```

### TweetDAO (`src/database/tweet_dao.py`)
```python
# 支持新表名的字段列表
if target_table in ['twitter_tweet_project_new', 'twitter_tweet_back_test_cmc300']:
    fields = [
        'id_str', 'conversation_id_str', 'in_reply_to_status_id_str',
        'full_text', 'created_at', 'created_at_datetime',
        'bookmark_count', 'favorite_count', 'quote_count', 'reply_count',
        'retweet_count', 'view_count', 'engagement_total', 'update_time',
        'sentiment', 'user_id', 'tweet_url', 'link_url', 'isAnnounce', 
        'summary', 'is_activity', 'activity_detail', 'is_retweet', 'user_name'
    ]
```

### Crawler (`src/crawler.py`)
```python
# 指定新的项目推文表
project_table_name = 'twitter_tweet_back_test_cmc300'
tweet_saved_count = self.tweet_dao.batch_upsert_tweets(enriched_tweets, table_name=project_table_name)
```

## 测试验证

✅ 已通过 `test_project_tweet_modifications.py` 完成全面测试：
- 转发推文检测功能正常
- 普通推文处理功能正常  
- user_id 和 user_name 字段正确提取
- 表名和字段映射配置正确

## 使用说明

修改完成后，您可以通过以下命令启动项目推文爬取：

```bash
# 单次执行
./start_service_project.sh once

# 定时服务
./start_service_project.sh start

# 或者直接调用Python
python main.py --mode project-once
python main.py --mode project-schedule --interval 60
```

数据将自动保存到 `twitter_tweet_back_test_cmc300` 表中，包含所有新增字段：
- `user_id`: 用户ID（原kol_id）
- `user_name`: 用户名（来自screen_name） 
- `is_retweet`: 转发标记（0=否，1=是）

所有其他业务逻辑保持不变。