# Twitter List Members 获取工具使用文档

## 📋 功能概述

这个工具用于从 Twitter List 获取成员列表，并将数据入库到 `twitter_list_members_seed` 表，作为 KOL 扩充流程的**阶段1**。

**核心功能：**
- ✅ 调用 TwitterAPI.io 的 `/twitter/list/members` 接口
- ✅ 从指定的 List ID 获取所有成员信息
- ✅ 自动去重（基于 twitter_user_id）
- ✅ 支持单个List处理或批量处理
- ✅ 完善的错误处理和日志记录

## 🎯 使用场景

### 场景1: 处理单个List（推荐）

适用于：一个一个List地处理，便于控制和观察结果

```bash
# 第一步：测试模式（验证配置）
python fetch_list_members.py --test

# 第二步：模拟运行（调用API但不入库，查看返回数据）
python fetch_list_members.py \
    --list-id "1996467877948600431" \
    --list-name "KOL_CMC_top100" \
    --dry-run

# 第三步：正式运行（入库）
python fetch_list_members.py \
    --list-id "1996467877948600431" \
    --list-name "KOL_CMC_top100"
```

### 场景2: 批量处理所有List

适用于：一次性处理所有10个List（自动按优先级顺序执行）

```bash
# 批量处理（会自动处理脚本中配置的10个List）
python fetch_list_members.py --batch

# 批量模拟运行
python fetch_list_members.py --batch --dry-run
```

### 场景3: 查看统计信息

```bash
# 查看数据库中的统计信息
python fetch_list_members.py --stats
```

## 📖 详细使用说明

### 1️⃣ **首次使用 - 创建数据库表**

```bash
# 进入项目目录
cd /Users/qmk/Documents/QC/twitter/Carlwang

# 连接数据库，执行建表SQL
mysql -h 35.215.99.34 -P 13216 -u tele -p public_data < sql/create_list_members_seed_table.sql
# 密码: tele_sb268fg@cg5wH9dgW

# 或者使用你习惯的数据库工具执行 sql/create_list_members_seed_table.sql
```

### 2️⃣ **测试模式 - 验证脚本是否正常**

```bash
python fetch_list_members.py --test
```

**输出示例：**
```
============================================================
开始批量处理List Members
【测试模式 - 不调用API，不入库】
============================================================

▶ [1/10] 处理 KOL_CMC_top100 (1996467877948600431)
  [测试] 跳过API调用
...
处理完成！
```

### 3️⃣ **处理第一个List - KOL_CMC_top100**

```bash
# 先模拟运行，查看能获取多少成员
python fetch_list_members.py \
    --list-id "1996467877948600431" \
    --list-name "KOL_CMC_top100" \
    --dry-run
```

**输出示例：**
```
============================================================
开始处理List: 1996467877948600431
List名称: KOL_CMC_top100
============================================================
  API请求: https://api.twitterapi.io/twitter/list/members?list_id=1996467877948600431
  API请求成功，返回 1025 个成员
  获取到 1025 个成员
  成员示例 (前5个):
    1. @elonmusk - Elon Musk (粉丝: 170,234,567)
    2. @VitalikButerin - Vitalik Buterin (粉丝: 5,123,456)
    ...
  [模拟模式] 将入库 1025 个成员
```

如果看起来正常，执行正式入库：

```bash
python fetch_list_members.py \
    --list-id "1996467877948600431" \
    --list-name "KOL_CMC_top100"
```

**输出示例：**
```
============================================================
开始处理List: 1996467877948600431
List名称: KOL_CMC_top100
============================================================
  API请求成功，返回 1025 个成员
  开始入库...
  入库完成: 1025 条新增, 0 条已存在

============================================================
处理完成！
============================================================
总List数: 1
已处理: 1
成功: 1
失败: 0

API调用统计:
  API调用次数: 1
  总成员数: 1025

入库统计:
  新增入库: 1025
  已存在跳过: 0
============================================================

✓ 任务完成
```

### 4️⃣ **处理后续的List**

```bash
# 处理第2个List
python fetch_list_members.py \
    --list-id "1996305216485150751" \
    --list-name "List_02"

# 处理第3个List
python fetch_list_members.py \
    --list-id "1996038927162245632" \
    --list-name "List_03"

# ... 以此类推
```

### 5️⃣ **查看统计信息**

```bash
python fetch_list_members.py --stats
```

**输出示例：**
```
============================================================
数据库统计信息
============================================================

总用户数: 1,025

按List统计:
  KOL_CMC_top100: 1,025 个成员, 平均粉丝: 234,567, 最高粉丝: 170,234,567

处理状态:
  pending: 1,025

粉丝数Top 10:
  1. @elonmusk - Elon Musk: 170,234,567 粉丝 [KOL_CMC_top100]
  2. @VitalikButerin - Vitalik Buterin: 5,123,456 粉丝 [KOL_CMC_top100]
  ...
============================================================
```

## 🔧 参数说明

| 参数 | 说明 | 示例 |
|------|------|------|
| `--list-id` | 单个List ID | `--list-id "1996467877948600431"` |
| `--list-name` | List名称（可选，方便识别） | `--list-name "KOL_CMC_top100"` |
| `--batch` | 批量处理所有10个List | `--batch` |
| `--test` | 测试模式（不调用API，不入库） | `--test` |
| `--dry-run` | 模拟运行（调用API但不入库） | `--dry-run` |
| `--stats` | 查看数据库统计信息 | `--stats` |
| `--api-key` | 自定义API Key（可选） | `--api-key "your_key"` |

## 📊 数据字段说明

入库到 `twitter_list_members_seed` 表的字段：

| 字段 | 类型 | 说明 |
|------|------|------|
| `twitter_user_id` | VARCHAR(64) | Twitter用户ID（唯一） |
| `username` | VARCHAR(255) | 用户名（如 elonmusk） |
| `name` | VARCHAR(255) | 显示名称（如 Elon Musk） |
| `description` | TEXT | 用户简介 |
| `avatar` | TEXT | 头像URL |
| `source_list_id` | VARCHAR(64) | 来源List ID |
| `source_list_name` | VARCHAR(255) | 来源List名称 |
| `followers_count` | INT | 粉丝数 |
| `following_count` | INT | 关注数 |
| `statuses_count` | INT | 推文总数 |
| `status` | VARCHAR(20) | 处理状态（默认 pending） |
| `is_verified` | TINYINT | 是否认证账户 |
| `is_protected` | TINYINT | 是否私密账户 |

## 🔍 常用SQL查询

```sql
-- 查看所有List的成员数量
SELECT source_list_name, COUNT(*) as member_count
FROM public_data.twitter_list_members_seed
GROUP BY source_list_name
ORDER BY member_count DESC;

-- 查看粉丝数Top 20
SELECT username, name, followers_count, source_list_name
FROM public_data.twitter_list_members_seed
ORDER BY followers_count DESC
LIMIT 20;

-- 查看待处理的用户（用于阶段2）
SELECT COUNT(*) as pending_count
FROM public_data.twitter_list_members_seed
WHERE status = 'pending';

-- 查看认证用户
SELECT username, name, followers_count
FROM public_data.twitter_list_members_seed
WHERE is_verified = 1
ORDER BY followers_count DESC;

-- 按粉丝数分层统计
SELECT
    CASE
        WHEN followers_count >= 1000000 THEN '1M+ (顶级KOL)'
        WHEN followers_count >= 100000 THEN '100K-1M (头部KOL)'
        WHEN followers_count >= 10000 THEN '10K-100K (腰部KOL)'
        ELSE '<10K (长尾KOL)'
    END as tier,
    COUNT(*) as count
FROM public_data.twitter_list_members_seed
GROUP BY tier
ORDER BY MIN(followers_count) DESC;
```

## ⚠️ 注意事项

### 1. API 费用管理
- 每次调用 `/twitter/list/members` 接口会产生费用
- 建议先用 `--dry-run` 测试，确认返回数据正常再正式入库
- 10个List预估费用：10次API调用 × $0.01 = **$0.10**

### 2. 去重机制
- 表结构中 `twitter_user_id` 有 UNIQUE 约束
- 重复插入会被自动忽略，不会报错
- 如果多个List包含同一个用户，只保留第一次入库的记录

### 3. 数据质量
- API返回的数据可能包含已删除/封禁的账户
- `is_protected = 1` 的私密账户无法获取推文
- 建议在阶段2时过滤掉私密账户

### 4. 脚本配置
10个List ID已经硬编码在脚本中（第69-115行），如果需要修改：

```python
self.list_configs = [
    {
        "list_id": "你的List ID",
        "list_name": "自定义名称",
        "description": "描述",
        "priority": 1  # 优先级
    },
    ...
]
```

## 🔗 数据流向

```
阶段1 (本脚本):
Twitter List → API → twitter_list_members_seed 表

阶段2 (下一步):
twitter_list_members_seed → fetch_kol_followings.py → twitter_kol_all 表
```

## 📝 日志文件

日志默认输出到：
- 控制台（实时）
- `logs/twitter_crawler.log`（持久化）

## 🐛 故障排查

### 问题1: API请求失败 HTTP 401/403
**原因**: API Key无效或权限不足

**解决**:
```bash
# 检查API Key
python fetch_list_members.py --api-key "your_api_key" --dry-run --list-id "1996467877948600431"
```

### 问题2: 数据库连接失败
**原因**: 数据库配置错误

**解决**:
- 检查 `config/config.json` 中的数据库配置
- 确认数据库服务正常运行

### 问题3: 返回0个成员
**原因**: List ID错误或List为空

**解决**:
- 确认List ID是否正确
- 在Twitter网页端访问List确认是否有成员

### 问题4: 表不存在
**原因**: 未创建表

**解决**:
```bash
# 执行建表SQL
mysql -h 35.215.99.34 -P 13216 -u tele -p public_data < sql/create_list_members_seed_table.sql
```

## 📞 技术支持

如有问题，请查看：
1. 日志文件 `logs/twitter_crawler.log`
2. API文档：https://docs.twitterapi.io/api-reference/endpoint/get_list_members
3. 脚本源码注释

---

**Happy Coding!** 🚀
