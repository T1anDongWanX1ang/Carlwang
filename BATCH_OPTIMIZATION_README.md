# 批处理优化 - Token节省方案

## 🎯 优化目标
通过智能批处理、内容预筛选和响应缓存来显著减少OpenAI API token消耗。

## 📊 优化策略

### 1. 配置优化
**文件**: `config/config.json.template`

新增的批处理配置：
```json
"batch_processing": {
  "topic_batch_size": 20,     // 话题分析批次大小 (从10提升到20)
  "kol_batch_size": 8,        // KOL分析批次大小 (从5提升到8)
  "project_batch_size": 25,   // 项目分析批次大小 (从20提升到25)
  "content_merge_threshold": 2000,    // 内容合并阈值
  "enable_intelligent_grouping": true, // 启用智能分组
  "enable_content_deduplication": true, // 启用内容去重
  "similarity_threshold": 0.75         // 相似度阈值
},
"optimization": {
  "enable_content_filtering": true,     // 启用内容预筛选
  "min_engagement_threshold": 5,       // 最小互动数阈值
  "enable_response_caching": true,     // 启用响应缓存
  "cache_ttl_hours": 24,              // 缓存过期时间
  "max_prompt_tokens": 3000,          // 最大提示词长度
  "enable_batch_consolidation": true   // 启用批量合并
}
```

### 2. 智能批处理
**文件**: `src/api/chatgpt_client.py`

**新增功能**:
- `batch_extract_topics_from_tweets()` - 智能批量话题提取
- `_group_similar_content()` - 基于相似度的内容分组
- `_extract_topics_from_merged_content()` - 合并内容批量分析
- `_get_cached_response()` / `_cache_response()` - 响应缓存机制

**优化效果**:
- 相似内容合并处理，减少重复API调用
- 24小时响应缓存，避免重复分析
- 智能分组，提高批处理效率

### 3. 内容预筛选
**文件**: `src/topic_engine.py`

**新增功能**:
- `_filter_high_quality_tweets()` - 高质量推文筛选

**筛选标准**:
- 最小互动数阈值 (favorite + retweet*2 >= 5)
- 内容长度筛选 (>= 20字符)
- 垃圾内容过滤 (spam, bot, 广告等)
- 纯转发过滤 (RT @ 且内容<50字符)
- 加密货币相关关键词优先

**预期效果**: 过滤掉15-30%的低质量推文

### 4. 优化话题分析
**文件**: `src/utils/topic_analyzer.py`

**新增功能**:
- `_calculate_topic_quality_score()` - 话题质量评分
- 改进的 `_extract_topic_from_tweet_group()` - 使用新批处理方法

**优化点**:
- 智能选择最佳话题结果
- 考虑推文互动质量
- 避免通用话题泛滥

## 🧪 测试脚本

运行批处理优化测试：
```bash
python3 test_batch_optimization.py
```

**测试内容**:
1. **批量话题提取对比**: 传统逐个处理 vs 智能批处理
2. **内容预筛选效果**: 筛选率和潜在API节省
3. **响应缓存效果**: 缓存命中率和API节省

## 📈 预期优化效果

| 优化策略 | 预期节省比例 | 说明 |
|---------|-------------|------|
| 批处理大小优化 | 30-40% | 提高批次大小，减少API调用次数 |
| 智能内容合并 | 20-30% | 相似内容合并处理 |
| 响应缓存 | 20-25% | 24小时内重复内容复用 |
| 内容预筛选 | 15-30% | 过滤低质量推文 |
| **总计预期节省** | **50-70%** | 多策略叠加效果 |

## 🚀 部署说明

### 1. 更新配置文件
复制 `config.json.template` 到 `config.json` 并更新API密钥。

### 2. 重启服务
```bash
# 重启话题分析服务
./start_topic_service.sh restart

# 重启Marco服务 (如果使用)
./start_marco_service.sh restart
```

### 3. 监控效果
- 查看日志中的API调用统计
- 运行测试脚本验证效果
- 监控OpenAI API使用量

## 💡 进一步优化建议

### 短期优化
1. **调整时间间隔**: 你已经将topics间隔调整为15分钟，效果很好
2. **启用Marco优化**: Marco总结频率从4小时调整为6-8小时
3. **细化功能开关**: 关闭单推文分析，只保留批量分析

### 长期优化
1. **本地模型预筛选**: 使用开源模型做初步分类
2. **历史数据分析**: 基于历史数据优化筛选阈值
3. **动态调度**: 根据市场活跃度动态调整间隔

## 📋 配置检查清单

- [ ] 更新 `config.json` 中的批处理配置
- [ ] 启用内容预筛选功能
- [ ] 配置合适的互动阈值
- [ ] 启用响应缓存
- [ ] 运行测试脚本验证效果
- [ ] 重启相关服务
- [ ] 监控API使用量变化

## 🔧 故障排除

**如果批处理效果不明显**:
1. 检查 `enable_batch_consolidation` 是否为 true
2. 调整 `similarity_threshold` (0.3-0.8之间)
3. 查看日志中的分组和合并信息

**如果筛选过于严格**:
1. 降低 `min_engagement_threshold` (2-10之间)
2. 调整加密货币关键词列表
3. 查看筛选日志统计

**如果缓存命中率低**:
1. 检查内容是否有微小差异
2. 调整缓存TTL时间
3. 查看缓存日志信息

## 📝 更新日志

**2024-10-21**: 
- 实施智能批处理优化
- 添加内容预筛选功能  
- 实现响应缓存机制
- 创建测试脚本和文档

---

通过这些优化，预计可以实现50-70%的token节省，同时保持分析质量。建议先运行测试脚本验证效果，然后逐步部署到生产环境。
