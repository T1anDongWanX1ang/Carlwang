# 数据库表字段问题修复方案

## 问题分析

错误信息显示：
```
Unknown column 'conversation_id_str' in target table.
```

说明 `twitter_tweet_back_test_cmc300` 表中缺少 `conversation_id_str` 字段。

## 解决方案

### 方案1: 代码适配现有表结构 ✅ (已实施)

已修改 `src/database/tweet_dao.py` 中的字段映射，针对 `twitter_tweet_back_test_cmc300` 表使用精简字段列表，排除不存在的字段：

```python
if target_table == 'twitter_tweet_back_test_cmc300':
    # 排除 conversation_id_str 和 in_reply_to_status_id_str 等不存在的字段
    fields = [
        'id_str', 'full_text', 'created_at', 'created_at_datetime',
        'bookmark_count', 'favorite_count', 'quote_count', 'reply_count',
        'retweet_count', 'view_count', 'engagement_total', 'update_time',
        'sentiment', 'user_id', 'tweet_url', 'link_url', 'isAnnounce', 'summary', 
        'is_activity', 'activity_detail', 'is_retweet', 'user_name'
    ]
```

### 方案2: 建表SQL（如果需要创建完整表）

如果您希望创建一个包含所有字段的完整表，可以使用以下SQL：

```sql
CREATE TABLE twitter_tweet_back_test_cmc300 (
    id_str VARCHAR(50) NOT NULL,
    conversation_id_str VARCHAR(50),
    in_reply_to_status_id_str VARCHAR(50),
    full_text TEXT,
    created_at VARCHAR(100),
    created_at_datetime DATETIME,
    bookmark_count INT DEFAULT 0,
    favorite_count INT DEFAULT 0,
    quote_count INT DEFAULT 0,
    reply_count INT DEFAULT 0,
    retweet_count INT DEFAULT 0,
    view_count INT DEFAULT 0,
    engagement_total INT DEFAULT 0,
    update_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    sentiment VARCHAR(20),
    user_id VARCHAR(50),
    tweet_url VARCHAR(500),
    link_url VARCHAR(500),
    isAnnounce TINYINT DEFAULT 0,
    summary TEXT,
    is_activity TINYINT DEFAULT 0,
    activity_detail TEXT,
    is_retweet TINYINT DEFAULT 0,
    user_name VARCHAR(100),
    PRIMARY KEY (id_str)
) ENGINE=OLAP
UNIQUE KEY (id_str)
DISTRIBUTED BY HASH(id_str) BUCKETS 10;
```

### 方案3: 添加缺失字段（如果需要保持字段完整）

如果您希望在现有表中添加缺失的字段：

```sql
-- 添加缺失的字段
ALTER TABLE twitter_tweet_back_test_cmc300 
ADD COLUMN conversation_id_str VARCHAR(50) AFTER id_str;

ALTER TABLE twitter_tweet_back_test_cmc300 
ADD COLUMN in_reply_to_status_id_str VARCHAR(50) AFTER conversation_id_str;
```

## 当前状态

✅ **已修复**: 代码已自动适配现有表结构，将跳过不存在的字段
✅ **向后兼容**: 其他表的处理逻辑保持不变
✅ **数据完整性**: 关键业务字段（user_id, user_name, is_retweet等）都已包含

## 测试建议

修改后的代码现在应该可以正常工作。您可以通过以下方式测试：

```bash
# 测试单次项目推文拉取
./start_service_project.sh once

# 查看日志确认无报错
tail -f service_project.log
```

预期日志应该显示成功的插入操作，而不是字段错误。

## 字段映射对比

| 原始字段 | twitter_tweet_back_test_cmc300 | 说明 |
|---------|-------------------------------|------|
| id_str | ✅ 包含 | 主键 |
| conversation_id_str | ❌ 跳过 | 不存在，已排除 |
| in_reply_to_status_id_str | ❌ 跳过 | 不存在，已排除 |
| full_text | ✅ 包含 | 推文内容 |
| user_id | ✅ 包含 | 用户ID（原kol_id） |
| user_name | ✅ 包含 | 用户名（screen_name） |
| is_retweet | ✅ 包含 | 转发标记 |
| ... | ... | 其他业务字段正常包含 |

修复完成！数据现在应该能够正常入库到 `twitter_tweet_back_test_cmc300` 表。