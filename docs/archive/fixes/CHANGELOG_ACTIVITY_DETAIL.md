# 活动数据字段更新说明

## 更新日期
2024-11-14

## 更新内容

**将活动JSON数据从 `summary` 字段迁移到 `activity_detail` 字段**

## 数据库字段

### 使用的字段
- `is_activity` (INT): 0=普通推文, 1=活动推文
- `activity_detail` (JSON): 存储JSON格式的结构化活动数据

### ~~不再使用的字段~~
- ~~`summary` (TEXT)~~: 此字段保留用于其他用途，不再存储活动数据

## JSON数据格式

活动数据以JSON格式存储在`activity_detail`字段中：

```json
{
  "title": "活动标题（5个词以内）",
  "status": "Active",
  "summary": "活动摘要（20个词以内）",
  "time": "推文时间",
  "url": "推文链接"
}
```

## 代码修改清单

### 1. `src/crawler.py`
- **行 481-489**: 修改 `_detect_and_structure_activities()` 方法，将JSON数据存储到 `activity_detail` 字段
- **行 508-538**: 修改 `_update_tweet_activity_status()` 方法签名和SQL语句，使用 `activity_detail` 字段

### 2. `backfill_activities_48h.py`
- **行 180-195**: 修改推文处理逻辑，使用 `activity_detail` 字段
- **行 206-238**: 修改 `_update_tweet_in_db()` 方法签名和SQL语句，使用 `activity_detail` 字段

### 3. `README_ACTIVITY_EXTRACTION.md`
- 更新所有文档说明，将 `summary` 字段改为 `activity_detail` 字段
- 更新SQL查询示例
- 更新Python代码示例

## 使用示例

### 查询活动推文

```sql
SELECT id_str, full_text, activity_detail, created_at
FROM twitter_tweet
WHERE is_activity = 1
ORDER BY created_at DESC
LIMIT 100;
```

### 解析活动数据

```python
import json

# 假设从数据库查询得到推文记录
if tweet.activity_detail:
    activity_data = json.loads(tweet.activity_detail)
    print(f"标题: {activity_data['title']}")
    print(f"状态: {activity_data['status']}")
    print(f"摘要: {activity_data['summary']}")
    print(f"链接: {activity_data['url']}")
```

### 回填历史数据

```bash
# 使用更新后的脚本回填数据
python backfill_activities_48h.py --hours 48

# 模拟运行查看效果
python backfill_activities_48h.py --dry-run
```

## 兼容性说明

- ✅ **向前兼容**: `activity_detail` 字段已经存在于数据库中（类型为JSON）
- ✅ **数据迁移**: 旧数据的 `summary` 字段保持不变，新检测的活动将写入 `activity_detail`
- ✅ **独立运行**: 主爬虫和回填脚本都已更新，可以独立使用

## 测试验证

所有修改已通过以下测试：
- ✅ 模块导入测试
- ✅ 方法存在性验证
- ✅ 数据库字段类型验证
- ✅ 脚本语法检查

## 后续步骤

1. **运行回填脚本**处理历史数据（可选）：
   ```bash
   python backfill_activities_48h.py --hours 168  # 回填最近7天
   ```

2. **启动主爬虫**，新推文将自动检测活动并存储到 `activity_detail`：
   ```bash
   python main.py --mode schedule --interval 5
   ```

3. **验证数据**：
   ```sql
   SELECT COUNT(*) as total,
          SUM(CASE WHEN activity_detail IS NOT NULL THEN 1 ELSE 0 END) as with_detail
   FROM twitter_tweet
   WHERE is_activity = 1;
   ```

## 注意事项

⚠️ `activity_detail` 字段类型为 JSON，某些数据库客户端可能直接返回解析后的对象（dict），而不是JSON字符串。处理时请注意判断类型。

## 技术支持

如有问题，请查看：
- 主文档: `README_ACTIVITY_EXTRACTION.md`
- 日志文件: `logs/twitter_crawler.log`
