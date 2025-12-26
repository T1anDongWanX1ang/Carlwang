# 重新爬取历史数据计划

## 背景

由于之前的代码存在以下问题，需要删除并重新爬取2025-12-25 00:00:00以后的所有数据：
1. ❌ user_id 和 user_name 字段为空（76%的数据）
2. ❌ is_retweet 字段可能不准确（全部为0）
3. ❌ summary 字段为空（Gemini API未正确安装）

## 问题修复情况

### ✅ 已修复的问题

1. **user_id 和 user_name 字段映射问题**
   - 修改了 `data_mapper.py` 和 `crawler.py`，同时支持 'user' 和 'author' 字段
   - 在 Tweet 模型中添加了 user_name 字段
   - 在 simple_tweet_enricher.py 中正确设置 user_name

2. **is_retweet 字段处理**
   - `twitter_api_twitterapi.py` 已正确处理 'retweeted_tweet' 字段
   - 新数据会正确标记转发状态

3. **Gemini API 问题**
   - 已安装 `google-genai` 包
   - summary 生成现在应该可以正常工作

### ✅ 验证结果

最新测试数据（2025-12-26 22:26之后）显示：
- ✅ user_id 正确填充
- ✅ user_name 正确填充
- ✅ is_retweet 字段正常
- ✅ sentiment 正常工作
- ⚠️ summary 为 NULL（因为那时 Gemini 还未安装，现在已安装）

## 执行计划

### 步骤1：删除历史错误数据

```bash
cd /Users/qmk/Documents/QC/twitter/Carlwang/daily_tweet_crawler
python delete_historical_data.py
```

此脚本会：
1. 检查要删除的数据量（预计 1109 条）
2. 要求确认（输入 'YES'）
3. 删除 2025-12-25 00:00:00 之后的所有数据
4. 验证删除结果

**数据范围**:
- 时间范围: 2025-12-25 03:34:56 到 2025-12-26 22:33:22
- 总记录数: 1109 条

### 步骤2：重新爬取数据

有两种方式重新爬取：

#### 方式A：按天回填（推荐，更可控）

```bash
cd /Users/qmk/Documents/QC/twitter/Carlwang

# 爬取 2025-12-25 的数据
python main.py --mode project-once --hours 24

# 等待完成后，爬取 2025-12-26 的数据
python main.py --mode project-once --hours 24
```

**说明**:
- `--mode project-once`: 使用项目推文爬取模式，单次执行
- `--hours 24`: 设置时间窗口为24小时
- 每次执行会爬取最近24小时的数据

#### 方式B：一次性爬取（快速）

```bash
cd /Users/qmk/Documents/QC/twitter/Carlwang

# 爬取最近48小时的数据
python main.py --mode project-once --hours 48
```

**注意事项**:
- TwitterAPI 的分页限制可能无法获取全部历史数据
- 推荐使用方式A，分天爬取，确保数据完整性
- 每次爬取后检查日志，确认API调用成功

### 步骤3：验证新数据质量

运行验证脚本：

```bash
cd /Users/qmk/Documents/QC/twitter/Carlwang/daily_tweet_crawler

# 检查今天的数据
python check_today_data.py

# 检查所有最近数据
python check_all_recent_data.py

# 检查 is_retweet 字段
python check_is_retweet.py
```

**验证要点**:
1. ✅ user_id 不为空
2. ✅ user_name 不为空
3. ✅ is_retweet 有转发和原创的区分
4. ✅ sentiment 字段正确
5. ✅ summary 字段有内容（对于公告类推文）
6. ✅ isAnnounce 和 is_activity 正确识别

### 步骤4：数据质量检查SQL

手动检查数据质量：

```sql
-- 检查最近入库的数据
SELECT
    DATE_FORMAT(update_time, '%Y-%m-%d %H:00') as hour_group,
    COUNT(*) as total,
    SUM(CASE WHEN user_name IS NULL THEN 1 ELSE 0 END) as null_user_name,
    SUM(CASE WHEN user_id IS NULL THEN 1 ELSE 0 END) as null_user_id,
    SUM(CASE WHEN is_retweet = 1 THEN 1 ELSE 0 END) as retweet_count,
    SUM(CASE WHEN summary IS NOT NULL THEN 1 ELSE 0 END) as has_summary
FROM twitter_tweet_back_test_cmc300
WHERE update_time >= '2025-12-25 00:00:00'
GROUP BY hour_group
ORDER BY hour_group;

-- 检查转发推文示例
SELECT id_str, user_name, is_retweet, created_at_datetime
FROM twitter_tweet_back_test_cmc300
WHERE is_retweet = 1
LIMIT 10;
```

## 预期结果

重新爬取后的数据应该：
1. ✅ 所有推文都有 user_id 和 user_name
2. ✅ is_retweet 字段正确标记转发/原创状态
3. ✅ sentiment 字段准确反映情感倾向
4. ✅ 公告类推文有 AI 生成的 summary
5. ✅ isAnnounce 和 is_activity 正确识别

## API 成本估算

- 每次 API 调用: $0.003 USD
- 每页推文: 20条
- 预计需要爬取: ~1200条推文
- 预计API调用次数: ~60次
- **预计总成本**: ~$0.18 USD

## 时间估算

- 删除数据: <1分钟
- 重新爬取 (方式A): 每天约3-5分钟，总计约10分钟
- 重新爬取 (方式B): 约5-8分钟
- 验证: <2分钟
- **总时间**: 约15-20分钟

## 注意事项

1. **Gemini API 已修复**: 现在已安装 `google-genai` 包，summary 生成应该正常工作
2. **监控日志**: 重新爬取时注意观察日志，确保没有 "name 'genai' is not defined" 错误
3. **数据去重**: 系统会自动处理重复数据（基于 id_str 主键）
4. **保持进程单一**: 确保没有其他爬虫进程在运行

## 回滚方案

如果重新爬取出现问题，可以：
1. 停止爬取进程
2. 删除新爬取的数据（使用相同的 delete 脚本）
3. 检查错误日志
4. 修复问题后重新执行

## 完成检查清单

- [ ] 删除历史错误数据 (1109条)
- [ ] 重新爬取 2025-12-25 数据
- [ ] 重新爬取 2025-12-26 数据
- [ ] 验证 user_id/user_name 字段
- [ ] 验证 is_retweet 字段
- [ ] 验证 summary 字段
- [ ] 验证 sentiment/isAnnounce/is_activity 字段
- [ ] 检查 API 成本和日志

---

**创建时间**: 2025-12-26 23:22
**创建原因**: 修复 user_id/user_name/is_retweet/summary 字段问题
**影响范围**: 2025-12-25 00:00:00 至今的所有项目推文数据
