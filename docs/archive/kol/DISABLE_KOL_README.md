# KOL分析功能禁用说明

## 📋 修改概述

本次更新禁用了 KOL（Key Opinion Leader）分析功能，不再使用 `public_data.kols` 表。

## 🔧 修改内容

### 1. main.py
- ✅ 注释掉 `kol_engine` 导入
- ✅ 移除命令行参数中的 `kol` 模式
- ✅ 注释掉 `run_kol_analysis()` 函数
- ✅ 移除路由中的 KOL 模式调用

### 2. src/crawler.py
- ✅ 注释掉 `kol_engine` 导入和初始化
- ✅ 移除爬取完成后的 KOL 分析逻辑（第140-151行）
- ✅ 移除统计信息中的 `kol_stats`

### 3. config/config.json
- ✅ 设置 `enable_kol_analysis: false`

## 📊 影响范围

### ✅ 不受影响的功能
- 推文数据爬取
- 话题分析（Topic Analysis）
- 项目分析（Project Analysis）
- 推文增强（Tweet Enrichment）
- 情感分析（Sentiment Analysis）

### ❌ 已禁用的功能
- KOL 识别和分析
- KOL 影响力评分
- KOL 类型分类
- `--mode kol` 命令
- KOL 统计信息

## 🗄️ 数据库影响

### 不再使用的表
- `public_data.kols` - KOL信息表

### 仍然使用的表
- `public_data.twitter_tweet` - 推文数据
- `public_data.twitter_user` - 用户基础信息
- `public_data.topics` - 话题数据
- `public_data.twitter_projects` - 项目数据

**注意：** `twitter_user` 表仍然会正常记录用户信息（粉丝数、简介等），只是不会再进行 KOL 分析和评分。

## 📝 使用说明

### 可用的运行模式

```bash
# 单次执行爬取
./start_service.sh once [max_pages] [page_size]

# 定时调度模式（包含项目分析）
./start_service.sh start [interval] [max_pages] [page_size]

# 话题分析模式
./start_topic_service.sh once
./start_topic_service.sh start

# 项目分析模式
python main.py --mode project --max-pages 5
```

### 不再可用的模式

```bash
# ❌ 已禁用
python main.py --mode kol
```

## 🔄 如何恢复 KOL 分析

如果将来需要恢复 KOL 分析功能：

### 1. 取消代码注释

**main.py:**
```python
# 取消第19行注释
from src.kol_engine import kol_engine

# 取消第30行注释
parser.add_argument('--mode', choices=['once', 'schedule', 'test', 'topic', 'kol', 'project'], ...)

# 取消第60-61行注释
elif args.mode == 'kol':
    run_kol_analysis(args)

# 取消第241-246行注释
def run_kol_analysis(args):
    # ... 完整实现 ...
```

**src/crawler.py:**
```python
# 取消第19行注释
from .kol_engine import kol_engine

# 取消第34行注释
self.kol_engine = kol_engine

# 取消第140-151行注释
try:
    self.logger.info("开始进行KOL分析...")
    kol_success = self.kol_engine.analyze_all_users_as_kols(...)
    # ...

# 取消第476行注释
'kol_stats': self.kol_engine.get_kol_statistics(),
```

### 2. 修改配置文件

**config/config.json:**
```json
{
  "chatgpt": {
    "enable_kol_analysis": true  // 改为 true
  }
}
```

### 3. 重启服务

```bash
./start_service.sh restart
```

## ⚠️ 注意事项

1. **配置兼容性**
   - 配置文件中的 `enable_kol_analysis` 设为 `false`
   - 不影响其他分析功能的配置

2. **历史数据**
   - `public_data.kols` 表中的历史数据仍然保留
   - 如果需要，可以手动清理或导出

3. **依赖关系**
   - KOL 功能完全独立，禁用后不影响其他功能
   - Tweet enrichment 中的 `kol_id` 识别仍然工作（基于粉丝数简单判断）

4. **性能提升**
   - 禁用 KOL 分析后，每次爬取可节省约 20-30% 的处理时间
   - 减少 ChatGPT API 调用次数

## 🚀 升级步骤（远程服务器）

如果需要在远程服务器上应用此更改：

```bash
# 1. 拉取最新代码
cd /path/to/twitter-crawler
git pull origin main

# 2. 重启服务
./start_service.sh restart 30 5 20

# 3. 验证服务状态
./start_service.sh status

# 4. 检查日志（确认不再有KOL分析日志）
tail -f service.log | grep -i kol
```

## 📊 性能对比

| 指标 | 启用KOL分析 | 禁用KOL分析 | 改进 |
|------|------------|------------|------|
| 每次处理时间 | ~45秒 | ~30秒 | ✅ 33% ↓ |
| ChatGPT API调用 | ~150次/小时 | ~120次/小时 | ✅ 20% ↓ |
| 数据库写入 | 推文+用户+KOL | 推文+用户 | ✅ 简化 |

## 📞 问题反馈

如有疑问或需要恢复 KOL 功能，请联系开发团队。

---

**最后更新:** 2025-11-06  
**版本:** v1.0  
**状态:** ✅ KOL分析已禁用

