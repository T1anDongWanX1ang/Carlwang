# 日常推文爬取脚本集合

这个文件夹包含了日常项目推文爬取所需的所有脚本。

## 📁 脚本说明

### 1. start_service_project_twitterapi.sh
**主服务管理脚本** - 用于启动、停止、重启项目推文爬取服务

#### 功能
- 启动/停止/重启服务
- 查看服务状态
- 执行单次爬取
- 查看日志
- 查看监控状态

#### 使用方法

```bash
# 启动服务（使用默认配置）
./start_service_project_twitterapi.sh start

# 停止服务
./start_service_project_twitterapi.sh stop

# 重启服务
./start_service_project_twitterapi.sh restart

# 查看服务状态
./start_service_project_twitterapi.sh status

# 执行单次爬取
./start_service_project_twitterapi.sh once

# 查看最新 100 行日志
./start_service_project_twitterapi.sh logs 100

# 查看监控状态
./start_service_project_twitterapi.sh monitor

# 自定义配置启动（间隔 时长 每页条数 时间窗口）
./start_service_project_twitterapi.sh start 15 50 100 0.25
```

#### 默认配置
- **运行间隔**: 15 分钟
- **最大页数**: 2 页（实际按时间智能停止）
- **每页条数**: 约 20 条（API固定返回）
- **时间窗口**: 0.25 小时（15 分钟）
- **⏱️ 智能早停**: 检测到超时间窗口自动停止翻页 ✅
- **目标表**: twitter_tweet_back_test_cmc300
- **数据源**: config.json 中的 list_ids_project 列表

---

### 2. check_status.sh
**详细状态监控脚本** - 一眼看清所有运行中的服务和进程

#### 功能
- 显示 PID 文件记录的服务（PID、CPU、内存、运行时长）
- 搜索所有相关的 Python 进程
- 显示防休眠进程（caffeinate）
- 显示 Cron 自动监控任务状态
- 显示最近运行日志

#### 使用方法

```bash
# 查看详细状态
./check_status.sh
```

#### 输出示例

```
【1】PID 文件记录的服务：
✅ 服务正在运行
   PID:      12345
   CPU:      2.5%
   内存:     1.2%
   运行时长: 1:30:45

【2】所有相关的 Python 进程：
🟢 PID: 12345
   CPU: 2.5% | 内存: 1.2%
   命令: python main.py --mode project-schedule...
```

---

### 3. monitor_daily_cost.sh
**成本统计脚本** - 监控 API 调用成本和推文统计

#### 功能
- 显示累计总成本
- 显示累计获取推文数
- 显示累计入库推文数
- 显示今日已消费
- 预估月成本

#### 使用方法

```bash
# 查看成本统计
./monitor_daily_cost.sh
```

#### 输出示例

```
==================================================
📊 项目推文爬取服务 - 成本统计
==================================================

总运行次数: 10 次
累计总成本: $0.500000 USD
累计获取推文: 5000 条
累计入库推文: 1200 条
平均每条推文成本: $0.000416 USD

==================================================
💡 今日预估
==================================================
今日已消费: $0.500000 USD
预估月成本: $150.00 USD (按每15分钟运行)
```

---

### 4. service_project_monitor.sh
**服务监控脚本** - 自动监控服务状态并重启

#### 功能
- 检查服务是否运行
- 如果服务停止，自动重启
- 记录监控日志

#### 使用方法

**由 cron 定时任务自动运行**（每 5 分钟检查一次）

```bash
# 手动执行监控检查
./service_project_monitor.sh
```

#### Cron 配置
当你启动服务时，会自动添加以下 cron 任务：
```bash
*/5 * * * * /path/to/service_project_monitor.sh >/dev/null 2>&1
```

---

## 🚀 快速开始

### 第一次使用

1. **启动服务**
```bash
cd /Users/qmk/Documents/QC/twitter/Carlwang/daily_tweet_crawler
./start_service_project_twitterapi.sh start
```

2. **查看服务状态**
```bash
./start_service_project_twitterapi.sh status
```

3. **实时监控日志**
```bash
tail -f ../service_scripts/service_project_twitterapi.log
```

4. **查看成本统计**
```bash
./monitor_daily_cost.sh
```

---

## 📊 服务工作流程

```
每隔 15 分钟自动运行
    ↓
拉取 3 个 Twitter List 的推文
    ↓
时间过滤：只保留过去 15 分钟的推文
    ↓
早停机制：连续 3 页无有效推文时自动停止
    ↓
数据去重入库到 twitter_tweet_back_test_cmc300 表
    ↓
记录成本和统计信息
```

---

## 📂 相关文件位置

| 文件 | 位置 | 说明 |
|------|------|------|
| 服务日志 | `../service_scripts/service_project_twitterapi.log` | 运行日志 |
| PID 文件 | `../service_scripts/twitter-crawler-project-twitterapi.pid` | 进程 ID |
| 监控日志 | `../service_scripts/monitor_project.log` | 监控记录 |
| 配置文件 | `../config/config.json` | API 和数据库配置 |

---

## 🔧 常见问题

### Q: 如何修改运行间隔？
A: 编辑 `start_service_project_twitterapi.sh`，修改 `DEFAULT_INTERVAL` 变量

### Q: 如何修改时间窗口？
A: 编辑 `start_service_project_twitterapi.sh`，修改 `DEFAULT_HOURS_LIMIT` 变量

### Q: 服务会自动重启吗？
A: 是的，监控脚本每 5 分钟检查一次，如果服务停止会自动重启

### Q: 如何查看实时日志？
A: 运行 `tail -f ../service_scripts/service_project_twitterapi.log`

### Q: 如何估算成本？
A: 运行 `./monitor_daily_cost.sh` 查看实时成本统计

---

## 📝 注意事项

1. **防止重复运行**: 启动前请先检查服务状态，避免重复启动
2. **Mac 防休眠**: macOS 使用 `caffeinate` 防止系统休眠影响服务
3. **数据库去重**: 系统会自动去重，重复推文不会重复入库
4. **成本控制**: 早停机制会在连续 3 页无效数据时自动停止，节省 API 成本

---

## 🆘 支持

如有问题，请查看日志文件或联系开发团队。
