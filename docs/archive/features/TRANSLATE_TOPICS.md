# Topics 中文翻译脚本使用指南

## 功能说明

`translate_topics.py` 脚本用于将 `public_data.topics` 表中的中文内容翻译为英文。

**工作原理：**
1. 查询过去48小时（可配置）内更新的 topics
2. 检测 `topic_name` 和 `brief` 字段是否为中文（中文字符占比 > 30%）
3. 使用 ChatGPT API 将中文内容翻译为英文
4. 更新数据库，保留原有记录的其他字段

## 使用方法

### 基本用法

```bash
# 翻译过去48小时的中文topics（默认）
python translate_topics.py

# 翻译过去24小时的中文topics
python translate_topics.py --hours 24

# 翻译过去7天的中文topics
python translate_topics.py --hours 168

# 试运行模式（查看有哪些需要翻译，但不实际更新）
python translate_topics.py --dry-run

# 调整批处理大小
python translate_topics.py --batch-size 20
```

### 参数说明

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--hours` | 回溯小时数 | 48 |
| `--batch-size` | 批处理大小（进度输出频率） | 10 |
| `--dry-run` | 试运行模式（不更新数据库） | False |

### 完整示例

```bash
# 测试运行：查看过去24小时有哪些中文topics
python translate_topics.py --hours 24 --dry-run

# 正式运行：翻译过去48小时的中文topics
python translate_topics.py --hours 48

# 大规模翻译：翻译过去7天的数据
python translate_topics.py --hours 168 --batch-size 20
```

## 翻译逻辑

### 1. 中文检测

使用正则表达式检测中文字符：
```python
chinese_chars = re.findall(r'[\u4e00-\u9fff]', text)
chinese_ratio = len(chinese_chars) / total_chars

# 如果中文字符占比 > 30%，视为中文内容
if chinese_ratio > 0.3:
    return True
```

### 2. 翻译提示词

**Topic Name 翻译**:
```
System: You are a professional translator specializing in cryptocurrency and blockchain content.

User: Please translate the following Chinese cryptocurrency topic name to English:

Chinese: {text}

Requirements:
1. Keep it concise and professional
2. Preserve technical terms in their common English forms (e.g., DeFi, NFT, Layer2)
3. Use standard cryptocurrency industry terminology
4. Return ONLY the translated text without any additional explanation
```

**Brief 翻译**:
```
System: You are a professional translator specializing in cryptocurrency and blockchain content.

User: Please translate the following Chinese cryptocurrency topic description to English:

Chinese: {text}

Requirements:
1. Keep it concise and clear
2. Preserve technical terms and project names in their common English forms
3. Use standard cryptocurrency industry terminology
4. Maintain the original meaning and tone
5. Return ONLY the translated text without any additional explanation
```

**参数设置**:
- temperature: `0.3`
- max_tokens: `200`

### 3. 更新策略

```sql
UPDATE public_data.topics
SET
    topic_name = %s,     -- 仅当 is_name_chinese = True 时更新
    brief = %s,          -- 仅当 is_brief_chinese = True 时更新
    update_time = NOW()
WHERE topic_id = %s
```

## 日志输出

脚本会生成两份日志：
- **控制台输出**：实时进度和关键信息
- **文件日志**：`translate_topics.log`（详细的处理日志）

**日志示例**:
```
2025-11-08 12:00:00 - INFO - 开始翻译topics中文内容为英文
2025-11-08 12:00:00 - INFO - 查询到 50 条topics（过去48小时）
2025-11-08 12:00:00 - INFO - 筛选出 25 条中文topics
2025-11-08 12:00:01 - INFO - 处理 1/25: topic_123
2025-11-08 12:00:01 - INFO -   翻译topic_name: 以太坊升级分析
2025-11-08 12:00:02 - INFO -   ✓ topic_name: 以太坊升级分析 -> Ethereum Upgrade Analysis
2025-11-08 12:00:02 - INFO -   翻译brief: 本话题讨论以太坊即将到来的技术升级...
2025-11-08 12:00:03 - INFO -   ✓ brief翻译完成
2025-11-08 12:00:03 - INFO -   ✓ 数据库更新成功
...
2025-11-08 12:05:00 - INFO - 翻译完成！
2025-11-08 12:05:00 - INFO - 总数: 25
2025-11-08 12:05:00 - INFO - topic_name翻译: 25
2025-11-08 12:05:00 - INFO - brief翻译: 25
2025-11-08 12:05:00 - INFO - 数据库更新成功: 25
2025-11-08 12:05:00 - INFO - 成功率: 100.00%
```

## 统计信息

脚本执行完成后会输出以下统计：
- **总数**：处理的 topics 总数
- **topic_name翻译**：成功翻译 topic_name 的数量
- **brief翻译**：成功翻译 brief 的数量
- **数据库更新成功**：成功更新数据库的数量
- **数据库更新失败**：更新失败的数量
- **跳过**：翻译失败而跳过的数量
- **成功率**：更新成功率百分比

## 注意事项

⚠️ **重要提示：**

1. **API 调用成本**：
   - 每条 topic 可能需要调用 1-2 次 ChatGPT API
   - 建议使用 `--dry-run` 先查看需要翻译的数量
   - 大规模翻译前确认 API 配额充足

2. **处理时间**：
   - 取决于 topics 数量和 API 响应速度
   - 25条 topics ≈ 2-3 分钟
   - 100条 topics ≈ 10-15 分钟

3. **数据备份**：
   - 建议在大规模翻译前备份 `public_data.topics` 表
   - 可以使用 `--dry-run` 模式先预览

4. **中文检测准确性**：
   - 基于字符占比 > 30% 判断
   - 混合中英文内容可能被识别为中文
   - 纯英文内容不会被翻译

5. **翻译质量**：
   - 使用 GPT-3.5-turbo 模型
   - temperature=0.3 保证相对一致的输出
   - 保留加密货币行业术语

## 故障排查

### 问题：翻译失败率高
**解决方案**:
- 检查 ChatGPT API 配置和额度
- 查看 `translate_topics.log` 中的详细错误信息
- 检查网络连接

### 问题：中文内容未被识别
**解决方案**:
- 检查日志中的中文检测结果
- 可能是中文字符占比 < 30%
- 调整 `is_chinese()` 函数的阈值

### 问题：数据库更新失败
**解决方案**:
- 检查数据库连接
- 确认 topic_id 存在
- 查看数据库错误日志

## 示例输出

### 试运行模式

```bash
$ python translate_topics.py --hours 24 --dry-run

开始翻译topics中文内容为英文
查询到 15 条topics（过去24小时）
筛选出 8 条中文topics

待翻译topics列表:
  1. topic_123
     topic_name: 比特币价格分析... (中文=True)
     brief: 本话题分析比特币近期价格走势... (中文=True)
  2. topic_124
     topic_name: DeFi 协议安全问题... (中文=True)
     brief: 讨论去中心化金融协议的安全性... (中文=True)
  ...

⚠️  试运行模式：不会实际更新数据库
共找到 8 条需要翻译的topics
```

### 正常运行

```bash
$ python translate_topics.py --hours 48

开始翻译topics中文内容为英文
查询到 30 条topics（过去48小时）
筛选出 12 条中文topics

处理 1/12: topic_123
  翻译topic_name: 比特币价格分析
  ✓ topic_name: 比特币价格分析 -> Bitcoin Price Analysis
  翻译brief: 本话题分析比特币近期价格走势，探讨影响因素...
  ✓ brief翻译完成
  ✓ 数据库更新成功
...
翻译完成！
总数: 12
topic_name翻译: 12
brief翻译: 12
数据库更新成功: 12
数据库更新失败: 0
跳过: 0
成功率: 100.00%
```

## 相关文件

- `translate_topics.py` - 翻译脚本
- `translate_topics.log` - 详细日志
- `src/api/chatgpt_client.py` - ChatGPT API 客户端
- `src/database/connection.py` - 数据库连接管理
- `config/config.json` - 配置文件

## 更新日志

| 日期 | 版本 | 更新内容 |
|------|------|----------|
| 2025-11-08 | 1.0 | 初始版本，支持批量翻译 topics |
