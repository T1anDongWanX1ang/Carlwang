-- 为twitter_tweet_project_new表添加is_retweet字段
-- 用于标识推文是否为转发推文
-- 执行日期: 2025-12-10
-- 数据库: Apache Doris

-- 为项目推文表添加is_retweet字段
-- 注意: Doris不支持BOOLEAN类型，使用TINYINT代替 (0=false, 1=true)
ALTER TABLE twitter_tweet_project_new
ADD COLUMN is_retweet TINYINT DEFAULT 0 COMMENT '是否为转发推文（检测retweeted_status字段，0=否，1=是）';

-- 如果你也需要为主推文表添加该字段，取消下面这行的注释:
-- ALTER TABLE twitter_tweet
-- ADD COLUMN is_retweet TINYINT DEFAULT 0 COMMENT '是否为转发推文（检测retweeted_status字段，0=否，1=是）';

-- 验证字段是否添加成功
-- DESC twitter_tweet_project_new;

-- 查看示例数据
-- SELECT id_str, is_retweet, is_quote_status, SUBSTRING(full_text, 1, 50) as text_preview
-- FROM twitter_tweet_project_new
-- LIMIT 5;
