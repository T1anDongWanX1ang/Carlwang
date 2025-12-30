# KOL 关注列表获取工具

## 功能概述

这个工具用于批量获取 Twitter KOL 的关注列表，并将数据入库到 `twitter_kol_all` 表。

**核心功能：**
- ✓ 从 `twitter_kol` 表读取所有 KOL 数据
- ✓ 调用第三方 API 获取每个 KOL 的关注列表
- ✓ 将关注用户数据入库到 `twitter_kol_all` 表
- ✓ **智能缓存机制** - API 数据自动缓存，避免重复调用浪费费用
- ✓ **断点续传** - 自动记录进度，支持中断后继续运行
- ✓ **错误恢复** - 入库失败时保留缓存，可随时重试

## 缓存机制说明

### 为什么需要缓存？

由于第三方 API 费用较高，如果因为入库失败、网络中断等原因导致进程中断，重新运行时会再次调用 API，造成费用浪费。

### 缓存工作原理

```
第一次运行:
  1. 从数据库读取 KOL 列表
  2. 调用 API 获取关注列表 → 立即保存到缓存文件 (.kol_cache/)
  3. 将数据入库
  4. 入库成功 → 记录进度 + 删除缓存
  5. 入库失败 → 保留缓存，记录错误

再次运行:
  1. 加载进度文件，跳过已完成的 KOL
  2. 检查是否有缓存
     - 有缓存 → 从缓存读取（不调用 API）
     - 无缓存 → 调用 API + 保存缓存
  3. 将数据入库
  4. 入库成功 → 清理缓存
```

### 缓存目录结构

```
.kol_cache/
├── progress.json          # 进度记录（已完成的 KOL）
├── BTC.json              # 用户 BTC 的关注列表缓存
├── ethereum.json         # 用户 ethereum 的关注列表缓存
└── ...
```

## 使用指南

### 第1步：测试模式（推荐先运行）

```bash
# 测试基本功能，不调用 API，不消耗费用
python fetch_kol_followings.py --test
```

**说明：** 只处理前3个 KOL，验证数据库连接和脚本逻辑

### 第2步：API 连接测试

```bash
# 调用1次真实 API，验证接口正常
python fetch_kol_followings.py --dry-run --limit 1
```

**说明：** 真实调用 API 但不入库，验证 API key 和返回数据格式

### 第3步：小批量测试

```bash
# 正式处理5个 KOL，验证完整流程
python fetch_kol_followings.py --limit 5
```

**说明：** 完整测试 API 调用 + 缓存 + 入库流程

### 第4步：正式运行

```bash
# 处理所有 KOL（自动跳过已完成的）
python fetch_kol_followings.py

# 或者分批处理（推荐）
python fetch_kol_followings.py --limit 50
```

## 常用命令

### 正常运行

```bash
# 处理所有剩余的 KOL
python fetch_kol_followings.py

# 限制处理数量
python fetch_kol_followings.py --limit 20

# 使用自定义 API 密钥
python fetch_kol_followings.py --api-key "your_api_key"
```

### 错误恢复

```bash
# 从缓存恢复（只处理已缓存的数据，不调用 API）
python fetch_kol_followings.py --resume
```

**使用场景：**
- API 调用成功但入库失败
- 进程意外中断
- 数据库临时不可用

### 缓存管理

```bash
# 查看缓存状态
python fetch_kol_followings.py --cache-status

# 清理所有缓存和进度（需要确认）
python fetch_kol_followings.py --clear-cache
```

### 帮助信息

```bash
# 查看所有参数说明
python fetch_kol_followings.py --help
```

## 典型使用场景

### 场景1：正常运行被中断

```bash
# 第一次运行（处理了10个 KOL 后网络中断）
python fetch_kol_followings.py --limit 50

# 直接重新运行，会自动跳过已完成的10个，从第11个继续
python fetch_kol_followings.py --limit 50
```

### 场景2：API 成功但入库失败

```bash
# 运行时数据库出现问题，API 已调用但入库失败
python fetch_kol_followings.py --limit 10

# 修复数据库后，使用 resume 模式从缓存恢复（不再调用 API）
python fetch_kol_followings.py --resume
```

### 场景3：分批处理大量 KOL

```bash
# 第一批
python fetch_kol_followings.py --limit 100

# 第二批（自动跳过前100个已完成的）
python fetch_kol_followings.py --limit 100

# 第三批
python fetch_kol_followings.py --limit 100
```

## 数据映射

| API 字段 | 数据库字段 | 说明 |
|---------|-----------|------|
| id | id | 用户唯一 ID |
| name | name | 用户昵称 |
| screen_name | user_name | 用户显示名称 |
| profile_image_url_https | avatar | 头像 URL |
| description | description | 个人简介 |
| created_at | created_at / created_at_time | 账户创建时间 |
| followers_count | followers | 粉丝数 |
| following_count | following | 关注数 |
| statuses_count | statuses_count | 推文数 |

## 性能优化

### API 限流保护

- 每次 API 请求间隔 2 秒，避免触发限流
- 缓存机制减少重复 API 调用
- 支持断点续传，避免重复处理

### 内存优化

- 逐个处理 KOL，避免一次性加载所有数据
- 入库成功后立即清理缓存文件

### 错误处理

- 单个 KOL 失败不影响后续处理
- 详细的日志记录，便于排查问题
- 进度自动保存，支持随时中断

## 注意事项

1. **API 费用管理**
   - 每次 API 调用都会产生费用
   - 使用 `--test` 和 `--dry-run` 充分测试后再正式运行
   - 缓存机制可避免重复调用节省费用

2. **数据库去重**
   - 使用 Doris Unique Key 自动去重
   - 重复数据会自动覆盖更新

3. **缓存清理**
   - 入库成功后缓存会自动清理
   - 长期运行可定期检查缓存状态
   - 不要手动删除 `progress.json`，否则会重新处理已完成的 KOL

4. **中断恢复**
   - 可随时 Ctrl+C 中断，不会丢失进度
   - 重新运行会自动继续未完成的任务

## 监控和调试

### 查看运行日志

```bash
# 脚本会输出详细的处理日志，包括：
# - 处理进度
# - API 调用次数
# - 缓存命中次数
# - 入库统计
```

### 查看缓存状态

```bash
python fetch_kol_followings.py --cache-status

# 输出示例：
# 缓存目录: /path/to/.kol_cache
# 缓存文件数: 15
# 缓存总大小: 245.67 KB
# 已完成入库: 50 个KOL
```

## 故障排查

### 问题：缓存文件很多但没有清理

**原因：** 可能是入库一直失败

**解决：**
```bash
# 1. 检查缓存状态
python fetch_kol_followings.py --cache-status

# 2. 使用 resume 模式重试入库
python fetch_kol_followings.py --resume
```

### 问题：重复处理相同的 KOL

**原因：** 进度文件丢失或损坏

**解决：**
```bash
# 检查 .kol_cache/progress.json 是否存在
# 如果不存在，会重新开始处理
```

### 问题：API 调用失败

**原因：** API key 无效或网络问题

**解决：**
```bash
# 1. 使用 --dry-run 测试 API
python fetch_kol_followings.py --dry-run --limit 1

# 2. 检查 API key 是否正确
python fetch_kol_followings.py --api-key "your_key" --dry-run --limit 1
```

## 技术架构

```python
KOLFollowingsFetcher
├── 缓存管理
│   ├── _get_cache_file()      # 获取缓存文件路径
│   ├── _save_to_cache()       # 保存到缓存
│   ├── _clear_cache_for_kol() # 清理单个缓存
│   └── clear_all_cache()      # 清理所有缓存
├── 进度管理
│   ├── _load_progress()       # 加载进度
│   └── _mark_completed()      # 标记完成
├── 数据获取
│   ├── _fetch_followings()           # API 调用
│   └── _get_followings_with_cache()  # 带缓存的获取
└── 数据入库
    ├── _save_followings()     # 批量入库
    └── _insert_or_update_user() # 单条入库
```

## 版本历史

- v2.0 (2025-01-11): 添加缓存机制和断点续传
- v1.0 (2025-01-11): 初始版本

## 联系支持

如有问题，请查看日志文件或联系技术支持。
