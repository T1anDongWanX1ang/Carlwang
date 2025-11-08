-- 为 twitter_tweet 表添加缺失的字段
-- 执行此脚本前请备份数据库

-- 添加 kol_id 字段
ALTER TABLE twitter_tweet
ADD COLUMN IF NOT EXISTS `kol_id` VARCHAR(50) NULL COMMENT "KOL用户ID";

-- 添加 entity_id 字段（保留兼容性）
ALTER TABLE twitter_tweet
ADD COLUMN IF NOT EXISTS `entity_id` VARCHAR(50) NULL COMMENT "实体ID（如话题ID）- 保留兼容性";

-- 添加 project_id 字段
ALTER TABLE twitter_tweet
ADD COLUMN IF NOT EXISTS `project_id` VARCHAR(50) NULL COMMENT "项目ID（project_xxx格式）";

-- 添加 topic_id 字段
ALTER TABLE twitter_tweet
ADD COLUMN IF NOT EXISTS `topic_id` VARCHAR(50) NULL COMMENT "话题ID（topic_xxx格式）";

-- 添加 is_valid 字段
ALTER TABLE twitter_tweet
ADD COLUMN IF NOT EXISTS `is_valid` BOOLEAN NULL COMMENT "是否为有效的加密货币相关内容";

-- 添加 sentiment 字段
ALTER TABLE twitter_tweet
ADD COLUMN IF NOT EXISTS `sentiment` VARCHAR(20) NULL COMMENT "情绪倾向：Positive/Negative/Neutral";

-- 添加 tweet_url 字段
ALTER TABLE twitter_tweet
ADD COLUMN IF NOT EXISTS `tweet_url` VARCHAR(500) NULL COMMENT "推文URL";

-- 添加 link_url 字段
ALTER TABLE twitter_tweet
ADD COLUMN IF NOT EXISTS `link_url` VARCHAR(500) NULL COMMENT "提取的链接URL（来自entities字段）";

-- 添加 token_tag 字段
ALTER TABLE twitter_tweet
ADD COLUMN IF NOT EXISTS `token_tag` VARCHAR(200) NULL COMMENT "Token符号标签（如BTC,ETH，多个用逗号分隔）";

-- 添加 project_tag 字段
ALTER TABLE twitter_tweet
ADD COLUMN IF NOT EXISTS `project_tag` VARCHAR(200) NULL COMMENT "项目标签（匹配RootData的项目名称）";

-- 添加 is_announce 字段
ALTER TABLE twitter_tweet
ADD COLUMN IF NOT EXISTS `is_announce` TINYINT NULL DEFAULT 0 COMMENT "是否为重要公告（0=否，1=是）";

-- 添加 summary 字段
ALTER TABLE twitter_tweet
ADD COLUMN IF NOT EXISTS `summary` TEXT NULL COMMENT "AI总结（针对公告推文的简洁总结）";
