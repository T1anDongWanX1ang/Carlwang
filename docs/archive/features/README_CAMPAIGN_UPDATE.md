# 推文活动检测和数据库更新脚本

## 功能说明

自动扫描 `twitter_tweet` 表中的推文，检测包含活动信息（campaign, airdrop, quest, reward, giveaway）的推文，并更新数据库字段：
- `is_activity`: 标记为活动推文（设置为 1）
- `summary`: 存储AI生成的活动摘要（英文）

## 快速开始

### 基本用法

```bash
# 更新过去48小时的推文（默认）
python update_campaign_tweets.py
```

### 其他常用命令

```bash
# 更新过去24小时的推文
python update_campaign_tweets.py --hours 24

# 更新过去7天的推文
python update_campaign_tweets.py --hours 168

# 先模拟运行，查看会更新哪些推文（不会真正修改数据库）
python update_campaign_tweets.py --dry-run

# 调整处理批次大小（默认5条一批）
python update_campaign_tweets.py --batch-size 10
```

## 工作流程

1. **数据获取**: 从 `twitter_tweet` 表获取指定时间范围内的推文
2. **关键词过滤**: 筛选包含活动关键词的推文
3. **AI检测**: 使用 ChatGPT 精确判断是否为真正的活动推文
4. **生成摘要**: 为活动推文生成详细的英文摘要
5. **更新数据库**: 更新 `is_announce` 和 `summary` 字段

## 活动检测关键词

**英文关键词**：
- campaign, airdrop, quest, reward, giveaway
- bounty, contest, prize, distribution, incentive

**中文关键词**：
- 空投, 活动, 奖励, 赠送

## 参数说明

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--hours` | 扫描最近多少小时的推文 | 48 |
| `--batch-size` | 每批处理的推文数量 | 5 |
| `--dry-run` | 模拟运行，不修改数据库 | False |

## 输出示例

```
============================================================
开始更新活动推文数据 (过去 48 小时)
============================================================
获取到 1523 条推文
关键词过滤后剩余 87 条推文

处理批次 1/18
✓ 发现活动推文: 1234567890
  摘要: XYZ Protocol announces an airdrop campaign distributing...
  数据库更新成功: 1234567890

✓ 发现活动推文: 1234567891
  摘要: ABC DeFi launches quest program with 100K token rewards...
  数据库更新成功: 1234567891

✗ 非活动推文: 1234567892

============================================================
更新完成！
检查的推文数: 87
发现的活动推文: 23
成功更新: 23
失败: 0
============================================================
```

## 注意事项

### ⚠️ 首次使用建议

1. **先模拟运行**：
   ```bash
   python update_campaign_tweets.py --hours 1 --dry-run
   ```
   查看会检测到哪些活动推文，确认无误后再正式运行。

2. **从少量数据开始**：
   ```bash
   python update_campaign_tweets.py --hours 1
   ```
   先处理1小时的数据，确认效果后再扩大范围。

### 💰 成本考虑

- 每条推文需要调用 **2次 ChatGPT API**（检测 + 摘要生成）
- 如果有100条包含关键词的推文，将产生约200次API调用
- 建议合理设置时间范围，避免不必要的成本

### ⏱️ 处理时间

脚本会自动控制处理速度，避免API限流：
- 批次之间自动休眠2秒
- 每批处理5条推文（默认）
- 100条推文预计需要 3-5 分钟

### 🔄 定期执行建议

可以设置定时任务，定期更新数据库：

```bash
# 使用 cron 每天凌晨2点更新过去24小时的推文
0 2 * * * cd /path/to/twitter-crawler && python update_campaign_tweets.py --hours 24
```

## 数据库字段说明

更新后的字段：

- **`is_announce`** (TINYINT):
  - `0`: 普通推文
  - `1`: 活动推文

- **`summary`** (TEXT):
  - 活动摘要（英文，100-150词）
  - 包含：活动类型、参与要求、时间线、奖励详情等
  - 仅当 `is_announce=1` 时有内容

## 常见问题

**Q: 为什么有些包含关键词的推文没有被标记为活动？**
A: AI会进行精确判断，只有真正的活动公告才会被标记。单纯提到关键词但不是活动的推文会被排除。

**Q: 可以重复运行脚本吗？**
A: 可以。脚本会覆盖之前的标记和摘要。如果AI判断结果变化，字段会被更新。

**Q: 脚本运行失败了怎么办？**
A: 查看日志文件获取详细错误信息。常见原因：
- ChatGPT API密钥配置错误
- 数据库连接失败
- API限流（降低batch-size或稍后重试）

**Q: 如何查看哪些推文被标记为活动？**
A: 执行SQL查询：
```sql
SELECT * FROM twitter_tweet
WHERE is_announce = 1
ORDER BY created_at DESC
LIMIT 100;
```

## 技术支持

如有问题，请查看日志文件或联系开发团队。
