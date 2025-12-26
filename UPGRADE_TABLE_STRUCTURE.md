# Twitter List Members 表结构升级指南

## 概述

本次升级将 `twitter_list_members_seed` 表结构调整为完全匹配 Twitter API 返回的字段结构。

**API文档**: https://docs.twitterapi.io/api-reference/endpoint/get_list_members

---

## 升级步骤

### 1. 执行表结构修改

运行 Python 脚本来添加新字段：

```bash
cd /Users/qmk/Documents/QC/twitter/Carlwang
python3 alter_list_members_table.py
```

或者直接执行 SQL 文件：

```bash
mysql -h 35.215.99.34 -P 13216 -u tele -p public_data < sql/alter_list_members_seed_table.sql
```

### 2. 验证表结构

检查表结构是否已更新：

```sql
DESCRIBE public_data.twitter_list_members_seed;
```

### 3. 测试数据抓取

使用更新后的 `fetch_list_members.py` 脚本测试：

```bash
# 干运行模式（调用API但不入库）
python3 fetch_list_members.py --list-id "1996467877948600431" --dry-run

# 正式运行（单个List）
python3 fetch_list_members.py --list-id "1996467877948600431" --list-name "KOL_CMC_top100"
```

---

## 新增字段说明

### 基础身份字段
- `type` - API返回类型（通常为 "user"）
- `url` - x.com个人主页URL

### 认证相关
- `is_blue_verified` - 是否Twitter Blue认证
- `verified_type` - 认证类型（如: government）

### 个人资料媒体
- `profile_picture` - 个人头像URL（高质量）
- `cover_picture` - 封面图片URL
- `location` - 用户位置

### 互动指标
- `favourites_count` - 喜欢数量
- `media_count` - 媒体数量

### 账户属性
- `can_dm` - 是否可以发送私信
- `has_custom_timelines` - 是否有自定义时间线
- `is_translator` - 是否为翻译者
- `is_automated` - 是否为自动化账户
- `automated_by` - 自动化账户的操作者

### JSON字段
- `profile_bio` - 个人简介详细信息（JSON格式）
- `withheld_in_countries` - 受限国家列表（JSON数组）
- `pinned_tweet_ids` - 置顶推文ID列表（JSON数组）

### 可用性状态
- `unavailable` - 账户是否不可用
- `unavailable_reason` - 不可用原因
- `message` - 相关消息

---

## API字段映射表

| API字段名 | 数据库字段名 | 类型 | 说明 |
|----------|-------------|------|------|
| `id` | `twitter_user_id` | VARCHAR(64) | 用户唯一ID |
| `userName` | `username` | VARCHAR(255) | 用户名 |
| `name` | `name` | VARCHAR(255) | 显示名称 |
| `type` | `type` | VARCHAR(20) | 类型 |
| `url` | `url` | TEXT | 主页URL |
| `description` | `description` | TEXT | 简介 |
| `profilePicture` | `profile_picture` | TEXT | 头像URL |
| `coverPicture` | `cover_picture` | TEXT | 封面URL |
| `location` | `location` | VARCHAR(255) | 位置 |
| `followers` | `followers_count` | INT | 粉丝数 |
| `following` | `following_count` | INT | 关注数 |
| `statusesCount` | `statuses_count` | INT | 推文数 |
| `favouritesCount` | `favourites_count` | INT | 喜欢数 |
| `mediaCount` | `media_count` | INT | 媒体数 |
| `createdAt` | `account_created_at` | VARCHAR(50) | 创建时间 |
| `isBlueVerified` | `is_blue_verified` | TINYINT | Blue认证 |
| `verifiedType` | `verified_type` | VARCHAR(50) | 认证类型 |
| `canDm` | `can_dm` | TINYINT | 可私信 |
| `hasCustomTimelines` | `has_custom_timelines` | TINYINT | 自定义时间线 |
| `isTranslator` | `is_translator` | TINYINT | 翻译者 |
| `isAutomated` | `is_automated` | TINYINT | 自动化账户 |
| `automatedBy` | `automated_by` | VARCHAR(255) | 操作者 |
| `profile_bio` | `profile_bio` | JSON | 简介详情 |
| `unavailable` | `unavailable` | TINYINT | 不可用 |
| `unavailableReason` | `unavailable_reason` | VARCHAR(255) | 不可用原因 |
| `message` | `message` | TEXT | 消息 |
| `withheldInCountries` | `withheld_in_countries` | JSON | 受限国家 |
| `pinnedTweetIds` | `pinned_tweet_ids` | JSON | 置顶推文 |

---

## 文件清单

### 新创建的文件
1. [alter_list_members_table.py](alter_list_members_table.py) - Python脚本执行表结构修改
2. [sql/alter_list_members_seed_table.sql](sql/alter_list_members_seed_table.sql) - SQL脚本

### 修改的文件
1. [fetch_list_members.py](fetch_list_members.py) - 更新了字段映射逻辑
   - `_map_member_data()` 方法 - 映射所有API字段
   - `_insert_member()` 方法 - 插入所有字段

---

## 注意事项

1. **JSON字段存储**: `profile_bio`、`withheld_in_countries`、`pinned_tweet_ids` 使用JSON格式存储
2. **向后兼容**: 保留了旧字段映射逻辑，兼容旧版API
3. **索引优化**: 为常用查询字段添加了索引
4. **UNIQUE约束**: `twitter_user_id` 保持唯一性，避免重复数据

---

## 查询示例

### 查询所有Blue认证用户
```sql
SELECT username, name, followers_count, verified_type
FROM public_data.twitter_list_members_seed
WHERE is_blue_verified = 1
ORDER BY followers_count DESC
LIMIT 20;
```

### 查询包含JSON数据的用户
```sql
SELECT username, profile_bio, pinned_tweet_ids
FROM public_data.twitter_list_members_seed
WHERE profile_bio IS NOT NULL
LIMIT 10;
```

### 统计各认证类型数量
```sql
SELECT
    verified_type,
    COUNT(*) as count,
    AVG(followers_count) as avg_followers
FROM public_data.twitter_list_members_seed
WHERE verified_type IS NOT NULL
GROUP BY verified_type;
```

---

## 数据库连接脚本

数据库连接配置位于：[src/database/connection.py](src/database/connection.py:54-78)

连接池管理类：`DatabaseConnectionPool`
数据库管理器：`DatabaseManager`

---

## 联系方式

如有问题，请参考：
- Twitter API文档: https://docs.twitterapi.io/
- 项目README: [README_FETCH_LIST_MEMBERS.md](README_FETCH_LIST_MEMBERS.md)
