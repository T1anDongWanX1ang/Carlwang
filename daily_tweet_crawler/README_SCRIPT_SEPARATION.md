# 推文爬虫脚本分离说明

## ✅ 任务完成状态

1. ✅ **已清理错误数据**: 删除了48条错误保存到 `twitter_tweet` 表的项目推文数据
2. ✅ **已修复字段映射**: TwitterAPI接口的 `author` 字段已正确映射
3. ✅ **已终止进程**: 所有正在运行的爬虫进程已终止

## 📊 两个独立的爬虫脚本

系统包含**两个完全独立**的爬虫脚本，它们使用不同的列表、存储到不同的数据表：

### 1️⃣ KOL推文爬虫（KOL Tweet Crawler）

**用途**: 爬取KOL用户的推文，用于话题分析和KOL影响力分析

**配置**:
- List ID: `1896516371435122886` (1个列表)
- 数据表: `twitter_tweet`
- 关键字段: `kol_id`, `entity_id`, `project_id`, `topic_id`

**运行命令**:
```bash
# 单次执行
python main.py --mode once --max-pages 3 --hours-limit 3

# 定时调度（每5分钟）
python main.py --mode schedule --interval 5 --max-pages 3 --hours-limit 3
```

**服务脚本**:
```bash
./start_service.sh start    # 启动KOL推文爬虫服务
./start_service.sh status   # 查看状态
./start_service.sh stop     # 停止服务
```

---

### 2️⃣ 项目推文爬虫（Project Tweet Crawler）

**用途**: 爬取加密项目官方推文，用于项目动态监控

**配置**:
- List IDs: `1996848536520897010`, `1996863048959820198`, `1996887049027440697` (3个列表)
- 数据表: `twitter_tweet_back_test_cmc300`
- 关键字段: `user_id`, `user_name`, `sentiment`, `isAnnounce`, `is_activity`

**运行命令**:
```bash
# 单次执行
python main.py --mode project-once --max-pages 1 --page-size 20 --hours-limit 1

# 定时调度
python main.py --mode project-schedule --interval 30 --max-pages 1 --hours-limit 1
```

**服务脚本**:
```bash
./start_service_project.sh start    # 启动项目推文爬虫服务
./start_service_project.sh status   # 查看状态
./start_service_project.sh stop     # 停止服务
```

---

## 🔧 技术实现细节

### 表名控制机制

两个爬虫使用相同的底层代码，但通过以下机制区分存储表：

**KOL爬虫** (`--mode once`/`schedule`):
- 使用配置文件默认表名: `twitter_tweet`
- 调用: `crawler.crawl_tweets()`

**项目爬虫** (`--mode project-once`/`project-schedule`):
- 在 `main.py` 中显式设置: `tweet_dao.table_name = 'twitter_tweet_back_test_cmc300'`
- 调用: `crawler.crawl_project_tweets()`

### 字段映射修复

修复了 TwitterAPI 接口的字段映射问题：
- **修改文件**: `src/utils/data_mapper.py`, `src/crawler.py`, `src/utils/simple_tweet_enricher.py`
- **修复内容**: 兼容 `user` 和 `author` 两种字段名（新接口使用 `author`）

---

## ⚠️ 重要注意事项

1. **不要混淆两个爬虫**: 确保使用正确的 `--mode` 参数
2. **独立运行**: 两个爬虫应该独立运行，不要在同一进程中混用
3. **表名验证**: 启动时会打印使用的表名，请注意确认

---

## 📋 数据表结构差异

| 字段 | twitter_tweet (KOL) | twitter_tweet_back_test_cmc300 (Project) |
|------|---------------------|-------------------------------------------|
| 用户ID | kol_id | user_id |
| 用户名 | - | user_name |
| 实体ID | entity_id | - |
| 项目ID | project_id | - |
| 话题ID | topic_id | - |
| 有效性 | is_valid | - |
| 情感 | sentiment | sentiment |
| 公告 | isAnnounce | isAnnounce |
| 活动 | - | is_activity |

---

## 🎯 下一步操作建议

1. **测试KOL爬虫**: 运行 `python main.py --mode once` 验证数据存入 `twitter_tweet` 表
2. **测试项目爬虫**: 运行 `python main.py --mode project-once` 验证数据存入 `twitter_tweet_back_test_cmc300` 表
3. **查看日志**: 确认字段 `user_id`, `user_name` 不再为空
4. **启动服务**: 根据需要启动对应的服务脚本
