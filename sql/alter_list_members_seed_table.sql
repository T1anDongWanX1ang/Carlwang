-- ============================================================================
-- 修改 twitter_list_members_seed 表以匹配 Twitter API 返回字段
-- API 文档: https://docs.twitterapi.io/api-reference/endpoint/get_list_members
-- 修改日期: 2025-12-17
-- ============================================================================

USE public_data;

-- 添加 API 返回的所有字段
-- 注意：如果字段已存在会报错，请根据实际情况调整

-- 基础身份字段
ALTER TABLE twitter_list_members_seed ADD COLUMN IF NOT EXISTS `type` VARCHAR(20) DEFAULT 'user' COMMENT 'API返回类型';
ALTER TABLE twitter_list_members_seed ADD COLUMN IF NOT EXISTS `url` TEXT NULL COMMENT 'x.com个人主页URL';

-- 认证相关
ALTER TABLE twitter_list_members_seed ADD COLUMN IF NOT EXISTS `is_blue_verified` TINYINT DEFAULT 0 COMMENT '是否Twitter Blue认证';
ALTER TABLE twitter_list_members_seed ADD COLUMN IF NOT EXISTS `verified_type` VARCHAR(50) NULL COMMENT '认证类型(如: government)';

-- 个人资料媒体
ALTER TABLE twitter_list_members_seed ADD COLUMN IF NOT EXISTS `profile_picture` TEXT NULL COMMENT '个人头像URL';
ALTER TABLE twitter_list_members_seed ADD COLUMN IF NOT EXISTS `cover_picture` TEXT NULL COMMENT '封面图片URL';

-- 位置信息
ALTER TABLE twitter_list_members_seed ADD COLUMN IF NOT EXISTS `location` VARCHAR(255) NULL COMMENT '用户位置';

-- 互动指标
ALTER TABLE twitter_list_members_seed ADD COLUMN IF NOT EXISTS `favourites_count` INT DEFAULT 0 COMMENT '喜欢数量';
ALTER TABLE twitter_list_members_seed ADD COLUMN IF NOT EXISTS `media_count` INT DEFAULT 0 COMMENT '媒体数量';

-- 账户属性
ALTER TABLE twitter_list_members_seed ADD COLUMN IF NOT EXISTS `can_dm` TINYINT DEFAULT 0 COMMENT '是否可以发送私信';
ALTER TABLE twitter_list_members_seed ADD COLUMN IF NOT EXISTS `has_custom_timelines` TINYINT DEFAULT 0 COMMENT '是否有自定义时间线';
ALTER TABLE twitter_list_members_seed ADD COLUMN IF NOT EXISTS `is_translator` TINYINT DEFAULT 0 COMMENT '是否为翻译者';
ALTER TABLE twitter_list_members_seed ADD COLUMN IF NOT EXISTS `is_automated` TINYINT DEFAULT 0 COMMENT '是否为自动化账户';
ALTER TABLE twitter_list_members_seed ADD COLUMN IF NOT EXISTS `automated_by` VARCHAR(255) NULL COMMENT '自动化账户的操作者';

-- 简介详情（JSON格式存储）
ALTER TABLE twitter_list_members_seed ADD COLUMN IF NOT EXISTS `profile_bio` JSON NULL COMMENT '个人简介详细信息(JSON格式)';

-- 可用性状态
ALTER TABLE twitter_list_members_seed ADD COLUMN IF NOT EXISTS `unavailable` TINYINT DEFAULT 0 COMMENT '账户是否不可用';
ALTER TABLE twitter_list_members_seed ADD COLUMN IF NOT EXISTS `unavailable_reason` VARCHAR(255) NULL COMMENT '不可用原因';
ALTER TABLE twitter_list_members_seed ADD COLUMN IF NOT EXISTS `message` TEXT NULL COMMENT '相关消息';

-- 其他属性
ALTER TABLE twitter_list_members_seed ADD COLUMN IF NOT EXISTS `withheld_in_countries` JSON NULL COMMENT '受限国家列表(JSON数组)';
ALTER TABLE twitter_list_members_seed ADD COLUMN IF NOT EXISTS `pinned_tweet_ids` JSON NULL COMMENT '置顶推文ID列表(JSON数组)';

-- 添加索引以提升查询性能
CREATE INDEX IF NOT EXISTS idx_is_blue_verified ON twitter_list_members_seed(is_blue_verified);
CREATE INDEX IF NOT EXISTS idx_verified_type ON twitter_list_members_seed(verified_type);
CREATE INDEX IF NOT EXISTS idx_favourites_count ON twitter_list_members_seed(favourites_count DESC);
CREATE INDEX IF NOT EXISTS idx_media_count ON twitter_list_members_seed(media_count DESC);

-- ============================================================================
-- 字段映射说明
-- ============================================================================
-- API 字段名 -> 数据库字段名
-- id -> twitter_user_id
-- userName -> username
-- name -> name
-- description -> description
-- profilePicture -> profile_picture
-- coverPicture -> cover_picture
-- followers -> followers_count
-- following -> following_count
-- statusesCount -> statuses_count
-- createdAt -> account_created_at
-- isBlueVerified -> is_blue_verified
-- verifiedType -> verified_type
-- favouritesCount -> favourites_count
-- mediaCount -> media_count
-- canDm -> can_dm
-- hasCustomTimelines -> has_custom_timelines
-- isTranslator -> is_translator
-- isAutomated -> is_automated
-- automatedBy -> automated_by
-- withheldInCountries -> withheld_in_countries
-- pinnedTweetIds -> pinned_tweet_ids
-- ============================================================================

-- 查看修改后的表结构
DESCRIBE twitter_list_members_seed;
