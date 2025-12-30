# Project Tag 回填脚本使用指南

## 功能说明

`backfill_project_tags.py` 脚本用于对历史推文数据重新提取和回填 `project_tag` 字段。

**工作原理：**
1. 从数据库读取指定时间范围内的推文
2. 使用 `SmartClassifier` 重新分类每条推文
3. 如果分类结果是"项目"，通过 RootData 匹配器提取 `project_tag`
4. 使用 DELETE + INSERT 策略更新推文数据（适配 Doris 数据库）

## 使用方法

### 基本用法

```bash
# 回填过去7天的推文（默认）
python backfill_project_tags.py

# 回填过去30天的推文
python backfill_project_tags.py --days 30

# 限制处理1000条推文（用于测试）
python backfill_project_tags.py --limit 1000

# 调整批处理大小
python backfill_project_tags.py --batch-size 100
```

### 参数说明

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--days` | 回填最近N天的数据 | 7 |
| `--limit` | 限制处理的推文数量 | None（不限制） |
| `--batch-size` | 批处理大小（进度输出频率） | 50 |

### 完整示例

```bash
# 测试运行：处理最近3天的100条推文
python backfill_project_tags.py --days 3 --limit 100

# 生产运行：回填最近一周的所有推文
python backfill_project_tags.py --days 7

# 大规模回填：最近30天的数据
python backfill_project_tags.py --days 30 --batch-size 100
```

## 日志输出

脚本会生成两份日志：
- **控制台输出**：实时进度和关键信息
- **文件日志**：`backfill_project_tags.log`（详细的处理日志）

## 处理逻辑

### 1. 项目类型推文
- 如果 AI 识别的项目名称能匹配到 RootData 数据库，设置 `project_tag` 为匹配的项目名
- 如果无法匹配，`project_tag` 设置为 `NULL`

### 2. 非项目类型推文
- 如果推文被分类为"话题"或"其他"，清空其 `project_tag` 字段

### 3. 跳过条件
- `is_valid = 0` 的无效推文
- `full_text` 为空或长度小于10的推文
- `project_tag` 没有变化的推文

## 统计信息

脚本执行完成后会输出以下统计：
- **总数**：处理的推文总数
- **更新成功**：成功更新 `project_tag` 的数量
- **更新失败**：更新失败的数量
- **跳过**：未发生变化而跳过的数量
- **匹配到 RootData**：成功匹配到 RootData 项目的数量
- **非项目类型**：分类为话题/其他的数量
- **成功率**：更新成功率百分比

## 注意事项

⚠️ **重要提示：**

1. **数据库更新策略**：由于 Doris 数据库不支持更新主键字段，脚本使用 DELETE + INSERT 策略。请确保：
   - 数据库有足够的写入权限
   - 在低峰期运行（避免影响线上服务）

2. **API 调用成本**：脚本会调用 ChatGPT API 进行内容分类，请注意：
   - 每条推文需要调用 AI 分类接口
   - 建议使用 `--limit` 参数先测试少量数据
   - 大规模回填前确认 API 配额充足

3. **处理时间**：取决于推文数量和 API 响应速度：
   - 100条推文 ≈ 3-5分钟
   - 1000条推文 ≈ 30-50分钟
   - 10000条推文 ≈ 5-8小时

4. **重复运行**：脚本可以安全地重复运行，会跳过 `project_tag` 未变化的推文

## 故障排查

### 问题：更新失败率高
- 检查数据库连接是否正常
- 查看日志文件中的详细错误信息
- 确认数据库表结构是否完整

### 问题：AI 分类失败
- 检查 ChatGPT API 配置和额度
- 查看 `config/config.json` 中的 API 密钥是否正确
- 检查网络连接

### 问题：RootData 匹配率低
- 确认 RootData 项目数据已导入数据库
- 检查 `public_data.rootdata_projects` 表是否有数据
- 查看日志中的具体匹配情况

## 后续优化建议

1. **增量更新**：添加 `--incremental` 参数，只处理 `project_tag` 为空的推文
2. **并行处理**：使用多进程/多线程加速处理
3. **断点续传**：保存处理进度，支持中断后继续
4. **批量 API 调用**：减少 API 调用次数，降低成本

## 相关文件

- `src/utils/smart_classifier.py` - 智能分类器
- `src/utils/rootdata_project_matcher.py` - RootData 项目匹配器
- `src/api/chatgpt_client.py` - ChatGPT API 客户端
- `src/database/tweet_dao.py` - 推文数据访问对象
