# KOL Following 日常爬取脚本集合

这个文件夹包含了日常 KOL Following 数据爬取所需的所有脚本。

## ⚠️ 重要：分层爬取策略（节省80%+成本）

为了控制 API 成本，脚本采用**智能分层爬取策略**：
- **following < 1000**: 采集 200 条（1页）→ 成本低，质量高
- **1000 ≤ following ≤ 2000**: 采集 300 条（2页）→ 适中
- **following > 2000**: **跳过不采集** → 避免高成本，质量不高

**API 定价说明**：
- Following 端点返回完整用户资料（User Profiles）
- 定价：**$0.18 per 1,000 user profiles**
- 每次 API 调用返回 200 个用户资料
- 单次调用成本：$0.18 × (200/1000) = **$0.036 per request**

**成本对比示例（50个KOL）**：
- ❌ 无分层策略：约 **$14.40**（400次API调用 × $0.036）
- ✅ 有分层策略：约 **$2.52**（70次API调用 × $0.036）
- 💰 **节省 82% 成本**！

---

## 📁 脚本说明

### 1. fetch_kol_followings_new.py
**KOL Following 爬取核心脚本** - 从 twitter_list_members_seed 表读取 KOL，获取他们的 following 列表

#### 功能
- 从 `twitter_list_members_seed` 表读取 seed KOL
- 调用 TwitterAPI 获取每个 KOL 的 following 列表
- 将 following 数据存入 `twitter_kol_all` 表
- **🎯 智能分层爬取**：根据 following 数量自动调整采集策略
- 支持缓存和断点续传，防止重复 API 调用
- 支持分页获取完整数据

#### 数据流向
```
twitter_list_members_seed (seed 表)
    ↓
fetch_kol_followings_new.py
    ↓
TwitterAPI (获取 following 列表)
    ↓
twitter_kol_all (全量 KOL 表)
```

#### API 配置
- **API Key**: `new1_038536908c7f4960812ee7d601f620a1`
- **Header**: `X-API-Key`
- **Endpoint**: `https://api.twitterapi.io/twitter/user/followings`

---

### 2. start_service_kol_following.sh
**主服务管理脚本** - 用于启动、停止、重启 KOL Following 爬取服务

#### 功能
- 启动/停止/重启服务
- 查看服务状态
- 执行单次爬取
- 查看日志
- 查看监控状态

#### 使用方法

```bash
# 启动服务（使用默认配置：每天运行一次）
./start_service_kol_following.sh start

# 停止服务
./start_service_kol_following.sh stop

# 重启服务
./start_service_kol_following.sh restart

# 查看服务状态
./start_service_kol_following.sh status

# 执行单次爬取
./start_service_kol_following.sh once

# 查看最新 100 行日志
./start_service_kol_following.sh logs 100

# 查看监控状态
./start_service_kol_following.sh monitor

# 自定义配置启动（间隔分钟 KOL数量 API间隔）
./start_service_kol_following.sh start 720 20 1.0  # 每12小时，处理20个KOL，API间隔1秒
```

#### 默认配置
- **运行间隔**: 1440 分钟（24 小时，每天1次）
- **每次处理**: 10 个 KOL
- **API 间隔**: 0.5 秒
- **数据源**: twitter_list_members_seed 表
- **目标表**: twitter_kol_all 表
- **缓存目录**: .kol_cache_new

---

### 3. check_status.sh
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
   命令: python fetch_kol_followings_new.py...
```

---

### 4. monitor_daily_cost.sh
**成本统计脚本** - 监控 API 调用成本和 KOL 处理统计

#### 功能
- 显示总运行次数、成功/失败次数
- 显示 API 调用次数和缓存命中次数
- 显示累计处理 KOL 数量
- 显示累计获取 Following 数据量
- 预估月成本

#### 使用方法

```bash
# 查看成本统计
./monitor_daily_cost.sh
```

#### 输出示例

```
==================================================
📊 KOL Following 爬取服务 - 成本统计
==================================================

总运行次数: 10 次
  - 成功: 9 次
  - 失败: 1 次

==================================================
💰 API 调用统计
==================================================

API 调用次数: 100 次
缓存命中次数: 50 次
预估总成本: $0.100000 USD (按 $0.001/次)

平均每次运行成本: $0.010000 USD

==================================================
👥 KOL 处理统计
==================================================

累计处理 KOL: 100 个
  - 成功: 95 个
  - 失败: 5 个

成功率: 95.00%

==================================================
📋 Following 数据统计
==================================================

累计获取 Following: 50000 条
累计新增入库: 45000 条
累计已存在跳过: 5000 条

平均每个 KOL Following 数: 526.32 个
平均每条 Following 成本: $0.000002 USD
```

---

### 5. service_kol_following_monitor.sh
**服务监控脚本** - 自动监控服务状态并重启

#### 功能
- 检查服务是否运行
- 如果服务停止，自动重启
- 记录监控日志

#### 使用方法

**由 cron 定时任务自动运行**（每 5 分钟检查一次）

```bash
# 手动执行监控检查
./service_kol_following_monitor.sh
```

#### Cron 配置
当你启动服务时，会自动添加以下 cron 任务：
```bash
*/5 * * * * /path/to/service_kol_following_monitor.sh >/dev/null 2>&1
```

---

## 🚀 快速开始

### 第一次使用

1. **启动服务**
```bash
cd /Users/qmk/Documents/QC/twitter/Carlwang/daily_kol_following_crawler
./start_service_kol_following.sh start
```

2. **查看服务状态**
```bash
./start_service_kol_following.sh status
```

3. **实时监控日志**
```bash
tail -f service_kol_following.log
```

4. **查看成本统计**
```bash
./monitor_daily_cost.sh
```

---

## 📊 服务工作流程

```
每隔 24 小时自动运行（默认配置）
    ↓
从 twitter_list_members_seed 表读取 seed KOL
    ↓
调用 TwitterAPI 获取每个 KOL 的 following 列表
    ↓
支持断点续传：自动跳过已处理的 KOL
    ↓
支持缓存：避免重复 API 调用
    ↓
数据去重入库到 twitter_kol_all 表
    ↓
记录成本和统计信息
```

---

## 📂 相关文件位置

| 文件 | 位置 | 说明 |
|------|------|------|
| 核心脚本 | `fetch_kol_followings_new.py` | KOL Following 爬取脚本 |
| 服务日志 | `service_kol_following.log` | 运行日志 |
| PID 文件 | `twitter-crawler-kol-following.pid` | 进程 ID |
| 监控日志 | `monitor_kol_following.log` | 监控记录 |
| 缓存目录 | `.kol_cache_new/` | API 响应缓存 |
| 进度文件 | `.kol_cache_new/progress.json` | 断点续传进度 |

---

## 🔧 常见问题

### Q: 如何修改运行间隔？
A: 编辑 `start_service_kol_following.sh`，修改 `DEFAULT_INTERVAL` 变量，或启动时指定参数

```bash
# 每12小时运行一次
./start_service_kol_following.sh start 720
```

### Q: 如何修改每次处理的 KOL 数量？
A: 启动时指定第二个参数

```bash
# 每次处理 20 个 KOL
./start_service_kol_following.sh start 1440 20
```

### Q: 服务会自动重启吗？
A: 是的，监控脚本每 5 分钟检查一次，如果服务停止会自动重启

### Q: 如何查看实时日志？
A: 运行 `tail -f service_kol_following.log`

### Q: 如何清理缓存？
A: 运行 `python fetch_kol_followings_new.py --clear-cache`

### Q: 如何查看缓存状态？
A: 运行 `python fetch_kol_followings_new.py --cache-status`

### Q: 如何恢复中断的任务？
A: 脚本支持自动断点续传，已处理的 KOL 会自动跳过。如果需要从缓存恢复：
```bash
python fetch_kol_followings_new.py --resume
```

---

## 📝 注意事项

1. **防止重复运行**: 启动前请先检查服务状态，避免重复启动
2. **Mac 防休眠**: macOS 使用 `caffeinate` 防止系统休眠影响服务
3. **数据库去重**: 系统会自动去重，重复数据不会重复入库
4. **缓存机制**:
   - 已获取的 following 数据会缓存在 `.kol_cache_new/` 目录
   - 已入库的 KOL 会记录在 `progress.json`，避免重复处理
5. **成本控制**:
   - 使用缓存减少 API 调用
   - 自动跳过已处理的 KOL
   - 支持限制每次处理的 KOL 数量
6. **数据完整性**:
   - 支持分页获取完整 following 列表
   - 每个 following 记录会保存 follower_id（即哪个 KOL 关注了这个用户）

---

## 🔍 数据表结构

### 输入表：twitter_list_members_seed
```sql
- id: KOL ID
- user_name: KOL 用户名
- name: KOL 显示名称
- followers: 粉丝数
```

### 输出表：twitter_kol_all
```sql
- id: 用户 ID（主键）
- name: 显示名称
- user_name: 用户名
- avatar: 头像 URL
- description: 简介
- created_at: 创建时间字符串
- created_at_time: 创建时间（datetime）
- account_age_days: 账户年龄（天）
- followers: 粉丝数
- following: 关注数
- statuses_count: 推文数
- follower_id: 关注者的 user_name（哪个 KOL 关注了这个用户）
- update_time: 更新时间
```

---

## 🆘 支持

如有问题，请查看日志文件或联系开发团队。

### 快速诊断命令

```bash
# 1. 查看服务状态
./check_status.sh

# 2. 查看最新日志
./start_service_kol_following.sh logs 100

# 3. 查看成本统计
./monitor_daily_cost.sh

# 4. 查看缓存状态
cd /Users/qmk/Documents/QC/twitter/Carlwang
python daily_kol_following_crawler/fetch_kol_followings_new.py --cache-status
```
