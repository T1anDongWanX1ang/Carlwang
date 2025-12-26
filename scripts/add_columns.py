#!/usr/bin/env python3
"""
临时脚本：为 twitter_tweet 表添加缺失的字段
"""
import pymysql
import logging

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 数据库配置
DB_CONFIG = {
    'host': '34.46.218.219',
    'port': 9030,
    'user': 'transaction',
    'password': 'trans_dskke33@72hxcys',
    'database': 'public_data',
    'charset': 'utf8mb4'
}

# 需要添加的字段
ALTER_STATEMENTS = [
    "ALTER TABLE twitter_tweet ADD COLUMN `kol_id` VARCHAR(50) NULL COMMENT 'KOL用户ID'",
    "ALTER TABLE twitter_tweet ADD COLUMN `entity_id` VARCHAR(50) NULL COMMENT '实体ID（如话题ID）- 保留兼容性'",
    "ALTER TABLE twitter_tweet ADD COLUMN `project_id` VARCHAR(50) NULL COMMENT '项目ID（project_xxx格式）'",
    "ALTER TABLE twitter_tweet ADD COLUMN `topic_id` VARCHAR(50) NULL COMMENT '话题ID（topic_xxx格式）'",
    "ALTER TABLE twitter_tweet ADD COLUMN `is_valid` BOOLEAN NULL COMMENT '是否为有效的加密货币相关内容'",
    "ALTER TABLE twitter_tweet ADD COLUMN `sentiment` VARCHAR(20) NULL COMMENT '情绪倾向：Positive/Negative/Neutral'",
    "ALTER TABLE twitter_tweet ADD COLUMN `tweet_url` VARCHAR(500) NULL COMMENT '推文URL'",
    "ALTER TABLE twitter_tweet ADD COLUMN `link_url` VARCHAR(500) NULL COMMENT '提取的链接URL（来自entities字段）'",
    "ALTER TABLE twitter_tweet ADD COLUMN `token_tag` VARCHAR(200) NULL COMMENT 'Token符号标签（如BTC,ETH，多个用逗号分隔）'",
    "ALTER TABLE twitter_tweet ADD COLUMN `project_tag` VARCHAR(200) NULL COMMENT '项目标签（匹配RootData的项目名称）'",
    "ALTER TABLE twitter_tweet ADD COLUMN `is_announce` TINYINT NULL DEFAULT 0 COMMENT '是否为重要公告（0=否，1=是）'",
    "ALTER TABLE twitter_tweet ADD COLUMN `summary` TEXT NULL COMMENT 'AI总结（针对公告推文的简洁总结）'"
]

def main():
    """执行数据库表结构更新"""
    connection = None
    try:
        # 连接数据库
        logger.info(f"正在连接数据库 {DB_CONFIG['host']}:{DB_CONFIG['port']}...")
        connection = pymysql.connect(**DB_CONFIG)
        cursor = connection.cursor()

        logger.info(f"成功连接到数据库: {DB_CONFIG['database']}")

        # 执行每条 ALTER TABLE 语句
        success_count = 0
        for i, sql in enumerate(ALTER_STATEMENTS, 1):
            try:
                logger.info(f"[{i}/{len(ALTER_STATEMENTS)}] 执行: {sql[:80]}...")
                cursor.execute(sql)
                connection.commit()
                success_count += 1
                logger.info(f"✓ 成功添加字段")
            except Exception as e:
                error_msg = str(e)
                if "Duplicate column name" in error_msg or "already exists" in error_msg:
                    logger.warning(f"⚠ 字段已存在，跳过")
                else:
                    logger.error(f"✗ 执行失败: {error_msg}")

        logger.info(f"\n完成！成功执行 {success_count}/{len(ALTER_STATEMENTS)} 条语句")

    except Exception as e:
        logger.error(f"数据库操作失败: {e}")
        raise
    finally:
        if connection:
            connection.close()
            logger.info("数据库连接已关闭")

if __name__ == "__main__":
    main()
