-- ============================================================================
-- Twitter List Members Seed 表
-- 用途: 存储从 Twitter List 抓取的种子用户 (KOL扩充阶段1)
-- 创建日期: 2025-12-17
-- ============================================================================

CREATE TABLE IF NOT EXISTS public_data.twitter_list_members_seed (
    -- 主键
    `id` BIGINT AUTO_INCREMENT COMMENT '自增主键',

    -- Twitter用户基础信息
    `twitter_user_id` VARCHAR(64) NOT NULL COMMENT 'Twitter用户唯一ID (id_str)',
    `username` VARCHAR(255) NOT NULL COMMENT 'Twitter用户名 (screen_name, 如 elonmusk)',
    `name` VARCHAR(255) NULL COMMENT '用户显示名称',
    `description` TEXT NULL COMMENT '用户简介',
    `avatar` TEXT NULL COMMENT '用户头像URL (profile_image_url_https)',

    -- 来源追踪
    `source_list_id` VARCHAR(64) NOT NULL COMMENT '来源List ID',
    `source_list_name` VARCHAR(255) NULL COMMENT 'List名称 (方便识别，如: KOL_CMC_top100)',

    -- 用户基础指标
    `followers_count` INT DEFAULT 0 COMMENT '粉丝数',
    `following_count` INT DEFAULT 0 COMMENT '关注数 (friends_count)',
    `statuses_count` INT DEFAULT 0 COMMENT '推文总数',
    `account_created_at` VARCHAR(50) NULL COMMENT 'Twitter账户创建时间原始字符串',

    -- 处理状态 (支持断点续传)
    `status` VARCHAR(20) DEFAULT 'pending' COMMENT '处理状态: pending(待处理)/processing(处理中)/completed(已完成)/failed(失败)',
    `is_processed` TINYINT DEFAULT 0 COMMENT '是否已处理 (0=否, 1=是)',
    `error_message` TEXT NULL COMMENT '处理失败时的错误信息',

    -- 数据质量标记
    `is_verified` TINYINT DEFAULT 0 COMMENT '是否Twitter认证账户 (蓝V)',
    `is_protected` TINYINT DEFAULT 0 COMMENT '是否受保护账户 (私密账户)',

    -- 时间字段
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '入库时间',
    `updated_at` DATETIME ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    `processed_at` DATETIME NULL COMMENT '开始处理时间 (阶段2使用)',

    -- 主键和索引
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_twitter_user_id` (`twitter_user_id`),
    INDEX `idx_source_list` (`source_list_id`),
    INDEX `idx_status` (`status`),
    INDEX `idx_is_processed` (`is_processed`),
    INDEX `idx_created_at` (`created_at`),
    INDEX `idx_followers` (`followers_count` DESC)

) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
COMMENT='种子用户表 - 从Twitter List抓取的初始成员 (KOL扩充阶段1)';

-- ============================================================================
-- 使用说明
-- ============================================================================
-- 1. 这个表用于存储从 Twitter List 获取的种子用户
-- 2. twitter_user_id 有 UNIQUE 约束，避免重复
-- 3. status 字段支持断点续传，脚本会自动跳过已处理的用户
-- 4. 数据流向:
--    twitter_list_members_seed (本表) → twitter_kol_all (阶段2)
--
-- 查询示例:
-- -- 查看某个List抓取的用户数
-- SELECT source_list_id, COUNT(*) as user_count
-- FROM public_data.twitter_list_members_seed
-- GROUP BY source_list_id;
--
-- -- 查看待处理的用户
-- SELECT COUNT(*) FROM public_data.twitter_list_members_seed WHERE status = 'pending';
--
-- -- 查看粉丝数Top 10的种子用户
-- SELECT username, followers_count, description
-- FROM public_data.twitter_list_members_seed
-- ORDER BY followers_count DESC LIMIT 10;
