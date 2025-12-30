# 修复 twitter_projects 数据更新问题

## 问题诊断

**问题**: `twitter_projects` 表数据停留在10月20日，没有最新数据入库

**根本原因**: 
1. 爬虫服务没有以 `schedule` 模式运行
2. 项目分析只在 `schedule` 模式下自动执行
3. 推文数据正常更新，但项目分析功能未被触发

## 解决方案

### 方案1：启动包含项目分析的爬虫服务（推荐）

```bash
# 进入项目目录
cd /Users/qmk/Documents/code/twitter-data-product/twitter-crawler

# 启动爬虫服务（包含项目分析）
./start_crawler_service.sh start

# 检查服务状态
./start_crawler_service.sh status

# 查看服务日志
./start_crawler_service.sh logs 50
```

服务会每5分钟执行一次：
- 爬取推文数据
- 自动执行项目分析
- 更新 twitter_projects 表

### 方案2：手动执行项目分析

如果不想启动服务，可以手动执行项目分析：

```bash
cd /Users/qmk/Documents/code/twitter-data-product/twitter-crawler

# 执行项目分析（分析最近24小时的50条推文）
python3 main.py --mode project --max-pages 5 --page-size 10
```

### 方案3：添加项目分析到现有的爬虫流程

如果你已经有其他方式在爬取推文，需要在爬取后添加项目分析。

编辑你的爬虫脚本，在爬取完成后添加：

```python
from src.project_engine import project_engine

# 在爬取完成后执行项目分析
project_engine.analyze_recent_tweets(hours=24, max_tweets=50)
```

## 验证修复

执行以下命令验证项目数据是否更新：

```bash
cd /Users/qmk/Documents/code/twitter-data-product/twitter-crawler

# 运行诊断脚本
python3 diagnose_project_data.py
```

检查输出中的 "最近更新的项目" 是否有新数据。

## 定期执行项目分析（可选）

如果想定期执行项目分析但不想运行常驻服务，可以添加到 crontab：

```bash
# 编辑 crontab
crontab -e

# 添加以下行（每小时执行一次项目分析）
0 * * * * cd /Users/qmk/Documents/code/twitter-data-product/twitter-crawler && python3 main.py --mode project --max-pages 5 --page-size 10 >> logs/project_analysis_cron.log 2>&1
```

## 监控项目数据更新

创建监控脚本，定期检查项目数据是否正常更新：

```bash
# 每天检查一次项目数据更新情况
0 9 * * * cd /Users/qmk/Documents/code/twitter-data-product/twitter-crawler && python3 diagnose_project_data.py >> logs/project_monitor.log 2>&1
```

## 注意事项

1. **ChatGPT API配额**: 项目分析会调用 ChatGPT API，注意配额和费用
2. **批量大小**: 配置文件中的 `project_batch_size` 设置为 5，可以根据需要调整
3. **执行频率**: 建议不要过于频繁执行，避免API费用过高和重复分析
4. **日志监控**: 定期查看日志文件，确保项目分析正常执行

## 快速修复命令

```bash
# 一键修复：启动服务并查看状态
cd /Users/qmk/Documents/code/twitter-data-product/twitter-crawler && \
./start_crawler_service.sh start && \
sleep 5 && \
./start_crawler_service.sh status && \
echo "服务已启动，项目数据将在下次爬取后更新"
```

