# twitter_projects 数据停止更新问题 - 完整分析报告

## 问题描述
`public_data.twitter_projects` 表最新数据停留在10月20号，没有最新数据入库。

## 诊断结果

### 数据库现状
- **推文总数**: 37,656条
- **最新推文时间**: 2025年11月6日 08:26（今天上午，8小时前）
- **推文更新状态**: ✅ 正常更新
- **项目总数**: 1,881个
- **最新项目更新时间**: 2025年10月20日 23:32（16天前）
- **项目更新状态**: ❌ 已停止更新16天

### 服务运行状态
- **爬虫服务 (start_crawler_service.sh)**: ❌ 未运行
- **Marco服务 (crontab)**: ✅ 每30分钟运行一次
- **话题分析**: 上次执行10月21日
- **项目分析**: 上次执行9月26日（日志记录）

### 配置检查
- **enable_project_analysis**: ✅ 已启用 (config.json)
- **project_batch_size**: 5条/批次
- **ChatGPT API**: 已配置

## 问题根本原因

### 主要问题
1. **爬虫服务未以 schedule 模式运行**
   - 推文数据正在更新（可能通过其他途径，如N8N或其他服务）
   - 但项目分析功能只在 `main.py --mode schedule` 模式下执行
   - 当前没有进程在运行包含项目分析的爬虫服务

2. **项目分析功能未被触发**
   - 从代码 `main.py` 第143-165行可见，项目分析只在 schedule 模式的 `crawl_task()` 中执行
   - Once 模式不包含项目分析
   - Project 模式需要手动执行

### 代码逻辑
```python
# main.py line 143-165
def crawl_task():
    """定时爬取任务（包含项目分析）"""
    crawl_success = crawler.crawl_tweets(...)
    
    if crawl_success:
        logger.info("爬取完成，开始项目分析...")
        # 执行项目分析
        project_success = project_engine.analyze_recent_tweets(hours=24, max_tweets=max_tweets)
```

## 解决方案

### 方案1：启动包含项目分析的爬虫服务（推荐）

**优点**: 自动化、持续更新、无需人工干预
**缺点**: 需要常驻进程、消耗ChatGPT API配额

```bash
# 1. 启动服务
cd /Users/qmk/Documents/code/twitter-data-product/twitter-crawler
./start_crawler_service.sh start

# 2. 检查状态
./start_crawler_service.sh status

# 3. 查看日志
./start_crawler_service.sh logs 50
tail -f logs/crawler_service.log
```

服务将每5分钟执行：
- 爬取推文数据
- 自动执行项目分析
- 更新 twitter_projects 表

### 方案2：手动执行项目分析

**优点**: 不需要常驻服务、可控的API消耗
**缺点**: 需要手动或定时任务触发

```bash
cd /Users/qmk/Documents/code/twitter-data-product/twitter-crawler

# 执行项目分析（分析最近24小时的50条推文）
python3 main.py --mode project --max-pages 5 --page-size 10
```

### 方案3：添加crontab定时任务

**优点**: 定时自动执行、资源消耗可控
**缺点**: 需要配置crontab、错误处理较弱

```bash
# 编辑 crontab
crontab -e

# 添加以下行（每2小时执行一次项目分析）
0 */2 * * * cd /Users/qmk/Documents/code/twitter-data-product/twitter-crawler && python3 main.py --mode project --max-pages 5 --page-size 10 >> logs/project_analysis_cron.log 2>&1
```

### 方案4：修改现有爬虫流程

**如果你已经有其他服务在爬取推文**（比如通过N8N），可以在爬取后添加项目分析：

```python
# 在你的爬虫脚本中添加
from src.project_engine import project_engine

# 在推文爬取完成后
project_engine.analyze_recent_tweets(hours=24, max_tweets=50)
```

## 验证修复

执行诊断脚本验证项目数据是否恢复更新：

```bash
cd /Users/qmk/Documents/code/twitter-data-product/twitter-crawler
python3 diagnose_project_data.py
```

检查输出，确认：
1. 最近更新的项目时间是否接近当前时间
2. 项目数量是否在增加

## 注意事项

### 1. ChatGPT API 配额和费用
- 项目分析会调用 ChatGPT API
- 当前配置 `project_batch_size: 5`
- 每次分析会处理最多50条推文（可调整）
- 建议监控 API 使用情况和费用

### 2. 执行频率建议
- **推荐**: 每1-2小时执行一次
- **不推荐**: 过于频繁（如每5分钟），会导致：
  - 重复分析相同推文
  - API 费用快速增加
  - 数据质量未必更好

### 3. 日志监控
定期检查日志文件：
```bash
# 爬虫日志
tail -f logs/crawler_service.log

# 项目分析日志
tail -f logs/twitter_crawler.log | grep "项目分析"

# 错误日志
tail -f logs/twitter_crawler.log | grep "ERROR"
```

### 4. 性能优化
配置文件优化建议：
```json
{
  "chatgpt": {
    "batch_processing": {
      "project_batch_size": 10,  // 增加批量大小以提高效率
      "enable_intelligent_grouping": true,
      "enable_content_deduplication": true
    }
  }
}
```

## 后续监控

### 1. 设置自动监控
```bash
# 添加到 crontab，每天9点检查
0 9 * * * cd /Users/qmk/Documents/code/twitter-data-product/twitter-crawler && python3 diagnose_project_data.py >> logs/project_monitor.log 2>&1
```

### 2. 创建告警脚本
可以创建一个简单的告警脚本，当项目数据超过24小时未更新时发送通知。

### 3. 数据质量检查
定期检查：
- 项目数量增长趋势
- 热度和情绪数据是否合理
- ChatGPT API 错误率

## 快速修复命令

```bash
# 一键启动服务（方案1）
cd /Users/qmk/Documents/code/twitter-data-product/twitter-crawler && \
./start_crawler_service.sh start && \
sleep 5 && \
./start_crawler_service.sh status

# 或者，立即执行一次项目分析（方案2）
cd /Users/qmk/Documents/code/twitter-data-product/twitter-crawler && \
python3 main.py --mode project --max-pages 5 --page-size 10
```

## 相关文件

- **主程序**: `main.py`
- **项目引擎**: `src/project_engine.py`
- **项目分析器**: `src/utils/project_analyzer.py`
- **服务脚本**: `start_crawler_service.sh`
- **诊断脚本**: `diagnose_project_data.py`
- **配置文件**: `config/config.json`
- **日志目录**: `logs/`

## 总结

**问题**: 推文数据在更新，但项目分析功能未执行，导致 twitter_projects 表16天未更新。

**根因**: 爬虫服务没有以包含项目分析的 schedule 模式运行。

**推荐方案**: 启动 `start_crawler_service.sh` 服务，实现推文爬取和项目分析的自动化流程。

**预期效果**: 服务启动后，在下次爬取周期（5分钟）内，项目数据将开始更新。

