# Twitter KOL推文数据爬取服务

## 概述

这是 Twitter 数据采集系统的 **KOL推文爬取服务**，负责从 TweetScout API 爬取 KOL（Key Opinion Leaders）的推文数据，包括推文内容、用户信息、互动数据等。

## 快速开始

### 1. 启动服务（默认配置）
```bash
./quick_start.sh
```

### 2. 检查服务状态
```bash
./check_status.sh
```

### 3. 停止服务
```bash
./start_service_kol_tweet.sh stop
```

## 服务管理

### 启动服务
```bash
# 使用默认配置启动（60分钟间隔，50页，100条/页，3小时时间限制）
./start_service_kol_tweet.sh start

# 自定义配置启动
./start_service_kol_tweet.sh start [间隔分钟] [最大页数] [每页条数] [小时限制]

# 示例：10分钟间隔，30页，100条/页，6小时时间限制
./start_service_kol_tweet.sh start 10 30 100 6
```

### 停止服务
```bash
./start_service_kol_tweet.sh stop
```

### 重启服务
```bash
./start_service_kol_tweet.sh restart
```

### 查看服务状态
```bash
./start_service_kol_tweet.sh status
```

### 执行单次爬取
```bash
# 使用默认配置
./start_service_kol_tweet.sh once

# 自定义配置
./start_service_kol_tweet.sh once [最大页数] [每页条数] [小时限制]
```

### 查看日志
```bash
# 查看最新50行日志
./start_service_kol_tweet.sh logs

# 查看最新100行日志
./start_service_kol_tweet.sh logs 100
```

### 查看监控状态
```bash
./start_service_kol_tweet.sh monitor
```

## 配置说明

### 默认配置
- **间隔时间**: 60分钟（每小时运行一次）
- **最大页数**: 50页（实际会智能停止，最多15页）
- **每页条数**: 100条（实际由API决定）
- **时间限制**: 3小时（只爬取过去3小时的数据）

### 配置参数说明

| 参数 | 说明 | 默认值 | 推荐范围 |
|------|------|--------|----------|
| 间隔分钟 | 爬取任务执行间隔 | 60 | 5-1440 |
| 最大页数 | 每次爬取的最大页数 | 50 | 10-100 |
| 每页条数 | 每页返回的推文数量 | 100 | 20-100 |
| 小时限制 | 只爬取N小时内的数据 | 3 | 1-24 |

## 智能特性

### 1. 智能时间检测
- **独立时间线跟踪**: 为每个 KOL 维护独立的时间线
- **智能停止**: 只有当所有 KOL 都超过时间限制时才停止拉取
- **UTC时间转换**: 自动处理时区转换，确保时间窗口准确
- **资源优化**: 自动优化API请求次数，避免浪费

### 2. 防休眠保护
- **macOS**: 使用 `caffeinate` 防止系统休眠影响服务
- **Linux**: 使用 `nice -n -5` 设置高优先级
- **自动监控**: 每5分钟自动检查服务状态并重启

### 3. 自动监控
- **定时检查**: 每5分钟通过 cron 检查服务状态
- **自动重启**: 服务停止时自动重启
- **日志记录**: 所有监控活动记录在 `monitor_kol_tweet.log`

## 文件说明

```
daily_kol_tweet_crawler/
├── start_service_kol_tweet.sh   # 主服务管理脚本
├── service_kol_tweet_monitor.sh # 自动监控脚本（由cron调用）
├── check_status.sh              # 快速检查状态
├── quick_start.sh               # 快速启动脚本
├── README.md                    # 本文档
├── QUICK_REFERENCE.txt          # 快速参考卡片
├── service_kol_tweet.log        # 服务运行日志
├── monitor_kol_tweet.log        # 监控日志
├── twitter-crawler-kol-tweet.pid # 进程PID文件
└── logs/                        # 日志目录
```

## 日志位置

- **服务日志**: `./service_kol_tweet.log`
- **监控日志**: `./monitor_kol_tweet.log`
- **系统日志**: `./logs/twitter_crawler.log`（如果存在）

## 监控与告警

### 手动检查监控
```bash
./start_service_kol_tweet.sh monitor
```

### 查看cron任务
```bash
crontab -l | grep kol_tweet
```

### 移除监控任务
```bash
# 停止服务会自动移除监控任务
./start_service_kol_tweet.sh stop
```

## 常见问题

### Q: 如何确认服务正在运行？
```bash
./check_status.sh
```

### Q: 服务启动失败怎么办？
1. 检查日志: `./start_service_kol_tweet.sh logs`
2. 检查Python环境: `ls ../venv/bin/python`
3. 检查配置文件: `cat ../config/config.json`

### Q: 如何修改爬取间隔？
```bash
# 重启服务并指定新的间隔（例如：30分钟）
./start_service_kol_tweet.sh restart 30
```

### Q: 如何清理旧进程？
```bash
# 停止所有相关进程
pkill -f "python.*main.py.*schedule"

# 清理PID文件
rm -f twitter-crawler-kol-tweet.pid
```

### Q: 监控日志太大怎么办？
监控脚本会自动清理，保留最近1000行。手动清理：
```bash
echo "" > monitor_kol_tweet.log
```

## 性能优化建议

### 高频爬取（数据实时性要求高）
```bash
./start_service_kol_tweet.sh start 5 20 100 1
# 每5分钟，20页，过去1小时数据
```

### 低频爬取（节省API成本）
```bash
./start_service_kol_tweet.sh start 120 30 100 6
# 每2小时，30页，过去6小时数据
```

### 深度爬取（历史数据回填）
```bash
./start_service_kol_tweet.sh once 100 100 24
# 单次执行，100页，过去24小时数据
```

## 与其他服务的关系

本服务是 KOL 推文爬取服务，与以下服务协同工作：

- **daily_tweet_crawler**: 项目推文爬取服务（专注于特定项目）
- **daily_kol_following_crawler**: KOL关注数据爬取服务
- **main.py --mode topic**: Topic分析服务（独立运行）
- **main.py --mode kol**: KOL分析服务（独立运行）

## 技术细节

### 进程识别
服务通过以下特征识别进程：
```bash
ps -ef | grep "[P]ython.*main.py.*schedule"
```

### 防止重复启动
- 检查PID文件
- 检查实际运行进程
- 清理孤儿进程

### 日志轮转
- 监控日志: 自动保留最近1000行
- 服务日志: 需要手动管理

## 支持与维护

遇到问题请检查：
1. 服务状态: `./check_status.sh`
2. 服务日志: `./start_service_kol_tweet.sh logs 100`
3. 监控日志: `tail -50 monitor_kol_tweet.log`
4. 系统日志: `tail -50 ../logs/twitter_crawler.log`
