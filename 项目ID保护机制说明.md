# 项目ID保护机制说明

## 📋 问题背景

**问题**: 推文的 `project_id` 字段大量为 NULL
**原因分析**: 话题分析和项目分析是互斥的，可能存在话题覆盖项目ID的情况

## 🔍 数据现状

```
总推文数: 37,679
- 有 project_id: 7,403  (19.6%)
- 有 topic_id:  19,691 (52.3%)
- 两者都有:     0      (0% - 互斥正常)
- 两者都无:     10,585 (28.1%)
```

## 🎯 核心逻辑

### 1. 项目ID和话题ID是互斥的

推文的分类规则：
- **Project（项目）**: 讨论具体的加密货币项目（如 Bitcoin、Ethereum、Solana）
- **Topic（话题）**: 讨论一般性概念话题（如 DeFi、NFT、技术分析）
- **互斥关系**: 一条推文只能归属于项目或话题其中之一

### 2. 分类和更新的两个路径

#### 路径1：爬取时分类（SmartClassifier）
```
推文爬取 → SmartClassifier.classify_tweet()
         → 使用 ChatGPT 判断类型
         → 设置 project_id 或 topic_id
```

**文件**: `src/utils/smart_classifier.py`
**触发**: 每次爬取推文时

#### 路径2：话题分析后期关联（TopicEngine）
```
话题分析 → 生成话题
        → 查找相关推文
        → 更新推文的 topic_id
```

**文件**: `src/topic_engine.py`
**触发**: 话题分析服务（每15分钟）

## ⚠️ 潜在风险

**风险**: 话题分析可能后期更新推文的 topic_id，覆盖掉已有的 project_id

**场景**:
1. 推文爬取时被分类为 project，设置了 project_id
2. 话题分析服务运行，识别该推文与某个话题相关
3. 如果保护不当，可能清空 project_id 并设置 topic_id

## ✅ 已实施的保护机制

### 修改1: 增强 TopicEngine 保护逻辑

**文件**: `src/topic_engine.py` 第 289-315 行

**原逻辑**:
```python
if not tweet.topic_id and not tweet.project_id:
    update_sql = """
    UPDATE twitter_tweet 
    SET topic_id = %s, update_time = %s 
    WHERE id_str = %s AND (topic_id IS NULL OR topic_id = '') AND (project_id IS NULL OR project_id = '')
    """
```

**改进后**:
```python
if not tweet.topic_id and not tweet.project_id:
    # 更新推文的topic_id，使用双重保护确保不覆盖project_id
    update_sql = """
    UPDATE twitter_tweet 
    SET topic_id = %s, update_time = %s 
    WHERE id_str = %s 
      AND (topic_id IS NULL OR topic_id = '') 
      AND (project_id IS NULL OR project_id = '')
    """
    
    affected_rows = self.tweet_dao.db_manager.execute_update(...)
    
    if affected_rows > 0:
        self.logger.debug(f"推文 {tweet.id_str} 已关联到话题 {topic.topic_id}")
    else:
        self.logger.debug(f"推文 {tweet.id_str} 未更新（可能已有project_id或topic_id）")
else:
    if tweet.project_id:
        self.logger.debug(f"推文 {tweet.id_str} 已有project_id={tweet.project_id}，跳过话题关联")
    if tweet.topic_id:
        self.logger.debug(f"推文 {tweet.id_str} 已有topic_id={tweet.topic_id}，跳过话题关联")
```

### 保护层级

1. **Python 层保护**: 
   ```python
   if not tweet.topic_id and not tweet.project_id:
   ```
   只处理两个ID都为空的推文

2. **SQL 层保护**:
   ```sql
   WHERE id_str = %s 
     AND (topic_id IS NULL OR topic_id = '') 
     AND (project_id IS NULL OR project_id = '')
   ```
   数据库层面确保不覆盖已有值

3. **日志增强**:
   ```python
   if tweet.project_id:
       self.logger.debug(f"推文 {tweet.id_str} 已有project_id={tweet.project_id}，跳过话题关联")
   ```
   记录跳过的原因，便于调试

## 📊 验证方法

### 1. 检查数据完整性
```bash
cd /Users/qmk/Documents/code/twitter-data-product/twitter-crawler
python3 -c "
from src.database.connection import db_manager

sql = '''
    SELECT 
        COUNT(*) as total,
        SUM(CASE WHEN project_id IS NOT NULL THEN 1 ELSE 0 END) as has_project,
        SUM(CASE WHEN topic_id IS NOT NULL THEN 1 ELSE 0 END) as has_topic,
        SUM(CASE WHEN project_id IS NOT NULL AND topic_id IS NOT NULL THEN 1 ELSE 0 END) as both
    FROM twitter_tweet
'''
result = db_manager.execute_query(sql)
print('互斥性检查:')
print(f'  有project_id: {result[0][\"has_project\"]}')
print(f'  有topic_id: {result[0][\"has_topic\"]}')
print(f'  两者都有: {result[0][\"both\"]} (应该为0)')
"
```

### 2. 监控话题更新日志
```bash
# 查看话题服务日志
tail -f logs/topic_service.log | grep -E "已有project_id|跳过话题关联"
```

### 3. 检查话题服务运行状态
```bash
# 检查话题服务是否在运行
./start_topic_service.sh status

# 查看最近的话题分析日志
./start_topic_service.sh logs 50
```

## 🔄 服务管理

### 话题分析服务

```bash
# 启动话题服务（每15分钟运行一次）
./start_topic_service.sh start

# 停止话题服务
./start_topic_service.sh stop

# 查看状态
./start_topic_service.sh status

# 手动执行一次
./start_topic_service.sh once
```

### 爬虫服务（包含项目分析）

```bash
# 启动爬虫服务（每5分钟运行一次）
./start_service.sh start

# 查看状态
./start_service.sh status
```

## 📝 最佳实践

### 1. 优先级规则
- **Project > Topic**: 如果推文提到具体项目，优先归类为 project
- **一次分类**: 推文一旦被分类，后续不应该被覆盖
- **互斥保护**: 任何时候都要确保 project_id 和 topic_id 不同时存在

### 2. 监控建议
- 定期检查 `both_not_null` 的数量（应始终为0）
- 监控日志中的跳过记录
- 定期验证分类准确性

### 3. 问题排查
如果发现 project_id 仍然被覆盖：
1. 检查是否有其他服务在修改推文
2. 查看话题服务日志，确认保护机制生效
3. 检查 SmartClassifier 的分类逻辑是否正确

## 🎯 总结

**问题**: 推文的 project_id 大量为 NULL
**根本原因**: 
1. SmartClassifier 分类不准确（AI识别失败）
2. 话题分析可能有覆盖风险（已修复）

**解决方案**:
1. ✅ 增强 TopicEngine 保护逻辑（已完成）
2. ⏳ 需要优化 SmartClassifier 的分类准确性
3. ⏳ 需要检查 ChatGPT API 调用是否正常

**下一步**:
- 重启服务使新逻辑生效
- 监控日志验证保护机制
- 优化 SmartClassifier 提高分类准确性

