# Twitter数据爬虫

一个通用化的Twitter数据爬虫项目，用于从TweetScout API获取推文数据并存储到Doris数据库中。

## 功能特性

- **API数据获取**: 支持从TweetScout API获取推文数据，包含分页处理和重试机制
- **用户数据提取**: 自动从推文数据中提取用户信息并存储到用户表
- **话题分析**: 集成ChatGPT API，自动从推文中提取话题、分析情感和生成总结
- **衍生指标计算**: 实现热度、传播速度等衍生指标的自动计算
- **数据映射**: 灵活的字段映射配置，支持推文和用户数据到数据库字段的转换
- **数据库存储**: 支持批量插入/更新到Doris数据库，包含连接池管理
- **定时调度**: 支持每5分钟自动执行数据抓取任务
- **通用化配置**: 所有参数都可通过JSON配置文件进行配置
- **完善的日志**: 支持文件和控制台日志输出，包含日志轮转
- **错误处理**: 完善的异常处理和重试机制

## 项目结构

```
twitter-crawler/
├── config/
│   └── config.json          # 配置文件
├── src/
│   ├── api/
│   │   └── twitter_api.py    # API客户端
│   ├── database/
│   │   ├── connection.py     # 数据库连接管理
│   │   ├── tweet_dao.py      # 推文数据访问对象
│   │   └── user_dao.py       # 用户数据访问对象
│   ├── models/
│   │   ├── tweet.py          # 推文数据模型
│   │   └── user.py           # 用户数据模型
│   └── utils/
│       ├── config_manager.py # 配置管理器
│       ├── data_mapper.py    # 数据映射工具
│       ├── logger.py         # 日志配置
│       └── scheduler.py      # 定时调度器
├── sql/
│   └── create_tables.sql     # 数据库表创建脚本
├── logs/                     # 日志文件目录
├── main.py                   # 主程序入口
├── example.py                # 使用示例
├── requirements.txt          # 依赖包列表
├── QUICKSTART.md            # 快速开始指南
└── README.md                # 项目说明
```

## 安装和配置

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置设置 ⚠️ **必须步骤**

**重要：**项目为了安全考虑，不包含实际的API密钥和数据库凭据。首次使用前必须进行配置：

#### 方法一：使用配置脚本（推荐）
```bash
python setup_config.py
```

按照提示输入您的：
- TweetScout API Key
- OpenAI API Key (sk-...)
- 数据库连接信息

#### 方法二：手动配置
```bash
# 复制配置模板
cp config/config.json.template config/config.json

# 编辑配置文件，替换占位符为实际值
# YOUR_TWEETSCOUT_API_KEY → 您的TweetScout API密钥
# YOUR_OPENAI_API_KEY → 您的OpenAI API密钥
# YOUR_DATABASE_* → 您的数据库连接信息
```

配置项说明：
- **API配置**: TweetScout API的URL、密钥和参数
- **ChatGPT配置**: OpenAI API密钥和模型设置
- **数据库配置**: MySQL/Doris数据库连接信息
- **调度配置**: 定时任务间隔和并发数
- **字段映射**: API字段到数据库字段的映射关系
- **日志配置**: 日志级别和输出设置

### 3. 数据库表结构

确保Doris数据库中已创建相应的表：

**推文表：**
```sql
CREATE TABLE twitter_tweet (
    `id_str` VARCHAR(50) NOT NULL COMMENT "推文唯一ID字符串",
    `conversation_id_str` VARCHAR(50) NULL COMMENT "会话ID字符串",
    `in_reply_to_status_id_str` VARCHAR(50) NULL COMMENT "回复的目标推文ID",
    
    `full_text` TEXT NULL COMMENT "推文完整文本内容",
    `is_quote_status` BOOLEAN NULL DEFAULT false COMMENT "是否为引用推文",
    
    `created_at` VARCHAR(30) NULL COMMENT "创建时间字符串(原始格式)",
    `created_at_datetime` DATETIME NULL COMMENT "解析后的创建时间",
    
    `bookmark_count` INT NULL DEFAULT 0 COMMENT "书签收藏数",
    `favorite_count` INT NULL DEFAULT 0 COMMENT "喜欢数",
    `quote_count` INT NULL DEFAULT 0 COMMENT "引用数",
    `reply_count` INT NULL DEFAULT 0 COMMENT "回复数",
    `retweet_count` INT NULL DEFAULT 0 COMMENT "转发数",
    `view_count` BIGINT NULL DEFAULT 0 COMMENT "浏览数",
    
    `engagement_total` INT NULL COMMENT "互动总量(计算字段)",
    `update_time` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT "记录更新时间"
)
ENGINE=olap
UNIQUE KEY(`id_str`)
COMMENT "推特推文数据表"
DISTRIBUTED BY HASH(`id_str`) BUCKETS 10
PROPERTIES (
    "replication_num" = "3"
);
```

**用户表：**
```sql
CREATE TABLE twitter_user (
    `id_str` VARCHAR(50) NOT NULL COMMENT "用户唯一ID字符串",
    `screen_name` VARCHAR(100) NULL COMMENT "用户名（@后的名称）",
    `name` VARCHAR(200) NULL COMMENT "用户显示名称",
    `description` TEXT NULL COMMENT "用户简介描述",
    `avatar` VARCHAR(500) NULL COMMENT "用户头像URL",
    
    `created_at` VARCHAR(30) NULL COMMENT "用户创建时间字符串(原始格式)",
    `created_at_datetime` DATETIME NULL COMMENT "解析后的用户创建时间",
    
    `followers_count` INT NULL DEFAULT 0 COMMENT "粉丝数量",
    `friends_count` INT NULL DEFAULT 0 COMMENT "关注数量",
    `statuses_count` INT NULL DEFAULT 0 COMMENT "推文数量",
    `can_dm` BOOLEAN NULL DEFAULT false COMMENT "是否可以发送私信",
    
    `update_time` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT "记录更新时间"
)
ENGINE=olap
UNIQUE KEY(`id_str`)
COMMENT "推特用户数据表"
DISTRIBUTED BY HASH(`id_str`) BUCKETS 10
PROPERTIES (
    "replication_num" = "3"
);
```

您可以运行 `sql/create_tables.sql` 脚本来创建这些表。

## 使用方法

### 1. 测试连接

```bash
python main.py --mode test
```

### 2. 单次执行

```bash
# 使用默认配置
python main.py --mode once

# 指定参数
python main.py --mode once --list-id 1896516371435122886 --max-pages 5 --page-size 50
```

### 3. 定时调度

```bash
# 使用配置文件中的间隔（默认5分钟）
python main.py --mode schedule

# 指定调度间隔（10分钟）
python main.py --mode schedule --interval 10
```

### 4. 话题分析

```bash
# 分析现有推文并生成话题
python main.py --mode topic

# 指定分析的推文数量
python main.py --mode topic --max-pages 2 --page-size 10
```

### 4. 使用自定义配置文件

```bash
python main.py --config /path/to/custom/config.json --mode once
```

## 命令行参数

- `--mode`: 运行模式
  - `test`: 测试数据库和API连接
  - `once`: 单次执行数据爬取
  - `schedule`: 定时调度模式
  - `topic`: 话题分析模式
- `--list-id`: Twitter列表ID（覆盖配置文件中的默认值）
- `--max-pages`: 最大抓取页数
- `--page-size`: 每页数据量
- `--interval`: 定时调度间隔（分钟）
- `--config`: 自定义配置文件路径

## 配置说明

### API配置

```json
{
  "api": {
    "base_url": "https://api.tweetscout.io/v2",
    "endpoints": {
      "list_tweets": "/list-tweets"
    },
    "headers": {
      "Accept": "application/json",
      "ApiKey": "your-api-key"
    },
    "default_params": {
      "list_id": "1896516371435122886"
    },
    "pagination": {
      "page_size": 100,
      "max_pages": 10
    },
    "timeout": 30,
    "retry_attempts": 3,
    "retry_delay": 5
  }
}
```

### 数据库配置

```json
{
  "database": {
    "type": "mysql",
    "host": "34.46.218.219",
    "port": 9030,
    "database": "public_data",
    "username": "transaction",
    "password": "your-password",
    "tables": {
      "tweet": "twitter_tweet",
      "user": "twitter_user"
    },
    "connection_pool": {
      "max_connections": 10,
      "min_connections": 1,
      "connection_timeout": 30,
      "idle_timeout": 600
    }
  }
}
```

### 字段映射配置

```json
{
  "field_mapping": {
    "tweet": {
      "id_str": "id_str",
      "conversation_id_str": "conversation_id_str",
      "in_reply_to_status_id_str": "in_reply_to_status_id_str",
      "full_text": "full_text",
      "is_quote_status": "is_quote_status",
      "created_at": "created_at",
      "bookmark_count": "bookmark_count",
      "favorite_count": "favorite_count",
      "quote_count": "quote_count",
      "reply_count": "reply_count",
      "retweet_count": "retweet_count",
      "view_count": "view_count"
    },
    "user": {
      "id_str": "id_str",
      "screen_name": "screen_name",
      "name": "name",
      "description": "description",
      "avatar": "avatar",
      "created_at": "created_at",
      "followers_count": "followers_count",
      "friends_count": "friends_count",
      "statuses_count": "statuses_count",
      "can_dm": "can_dm"
    }
  }
}
```

## 日志

日志文件默认保存在 `logs/twitter_crawler.log`，支持自动轮转。日志级别和格式可以在配置文件中调整。

## 错误处理

- API请求失败时会自动重试（可配置重试次数和延迟）
- 数据库连接异常时会自动重连
- 数据验证失败的记录会被跳过并记录日志
- 程序异常时会优雅退出并清理资源

## 监控和统计

程序运行时会输出详细的统计信息，包括：

- 爬取任务执行次数和成功率
- API请求统计
- 数据库操作统计
- 数据处理统计

## 注意事项

1. 请确保API密钥有效且有足够的调用额度
2. 数据库连接信息需要正确配置
3. 建议在生产环境中使用systemd或其他进程管理工具来管理定时调度
4. 定期检查日志文件，监控程序运行状态
5. 根据实际需要调整分页大小和调度间隔

## 技术栈

- **Python 3.7+**
- **requests**: HTTP请求库
- **pymysql**: MySQL数据库连接器
- **python-dateutil**: 日期时间解析库

## 许可证

本项目采用MIT许可证。
