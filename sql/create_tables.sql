-- Twitter用户表
CREATE TABLE IF NOT EXISTS twitter_user (
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

-- Twitter推文表（已存在，这里提供完整结构供参考）
CREATE TABLE IF NOT EXISTS twitter_tweet (
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

-- Twitter Marco 数据表 - 存储基于推文生成的衍生数据
CREATE TABLE IF NOT EXISTS twitter_marco (
    `id` VARCHAR(50) NOT NULL COMMENT "主键，全局唯一标识符",
    `timestamp` DATETIME NOT NULL COMMENT "时间点，每30分钟记录一次",
    `sentiment_index` FLOAT NULL COMMENT "整个Crypto推特情绪得分[0,100]，基于KOL100指数推文计算",
    `summary` TEXT NULL COMMENT "AI总结，基于近4小时KOL推文的事件聚类和观点总结",
    
    `update_time` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT "记录更新时间"
)
ENGINE=OLAP
UNIQUE KEY(`id`, `timestamp`)
COMMENT "推特Marco衍生数据表"
DISTRIBUTED BY HASH(`id`) BUCKETS 10
PROPERTIES (
    "replication_allocation" = "tag.location.default: 1"
); 