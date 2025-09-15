#!/usr/bin/env python3
"""
数据库表设置脚本
"""
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.database.connection import db_manager
from src.utils.logger import get_logger


def drop_tables():
    """删除现有表"""
    logger = get_logger(__name__)
    
    logger.info("删除现有表...")
    
    try:
        # 删除推文表
        db_manager.execute_update("DROP TABLE IF EXISTS twitter_tweet")
        logger.info("推文表已删除")
        
        # 删除用户表
        db_manager.execute_update("DROP TABLE IF EXISTS twitter_user")
        logger.info("用户表已删除")
        
        return True
        
    except Exception as e:
        logger.error(f"删除表失败: {e}")
        return False


def create_tables():
    """创建数据库表"""
    logger = get_logger(__name__)
    
    logger.info("开始创建数据库表...")
    
    # 创建用户表
    create_user_table_sql = """
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
        `can_dm` BOOLEAN NULL DEFAULT 0 COMMENT "是否可以发送私信",
        
        `update_time` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT "记录更新时间"
    )
    ENGINE=olap
    UNIQUE KEY(`id_str`)
    COMMENT "推特用户数据表"
    DISTRIBUTED BY HASH(`id_str`) BUCKETS 10
    PROPERTIES (
        "replication_num" = "3"
    )
    """
    
    # 创建推文表
    create_tweet_table_sql = """
    CREATE TABLE twitter_tweet (
        `id_str` VARCHAR(50) NOT NULL COMMENT "推文唯一ID字符串",
        `conversation_id_str` VARCHAR(50) NULL COMMENT "会话ID字符串",
        `in_reply_to_status_id_str` VARCHAR(50) NULL COMMENT "回复的目标推文ID",
        
        `full_text` TEXT NULL COMMENT "推文完整文本内容",
        `is_quote_status` BOOLEAN NULL DEFAULT 0 COMMENT "是否为引用推文",
        
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
    )
    """
    
    try:
        # 创建用户表
        logger.info("创建用户表...")
        db_manager.execute_update(create_user_table_sql)
        logger.info("用户表创建成功")
        
        # 创建推文表
        logger.info("创建推文表...")
        db_manager.execute_update(create_tweet_table_sql)
        logger.info("推文表创建成功")
        
        logger.info("所有表创建完成")
        return True
        
    except Exception as e:
        logger.error(f"创建表失败: {e}")
        return False


def check_tables():
    """检查表是否存在"""
    logger = get_logger(__name__)
    
    logger.info("检查数据库表...")
    
    try:
        # 检查用户表
        user_count = db_manager.execute_query("SELECT COUNT(*) as count FROM twitter_user")
        logger.info(f"用户表存在，当前记录数: {user_count[0]['count'] if user_count else 0}")
        
        # 检查推文表
        tweet_count = db_manager.execute_query("SELECT COUNT(*) as count FROM twitter_tweet")
        logger.info(f"推文表存在，当前记录数: {tweet_count[0]['count'] if tweet_count else 0}")
        
        return True
        
    except Exception as e:
        logger.error(f"检查表失败: {e}")
        return False


def main():
    """主函数"""
    logger = get_logger(__name__)
    
    logger.info("数据库表设置工具")
    logger.info("=" * 30)
    
    # 测试连接
    if not db_manager.test_connection():
        logger.error("数据库连接失败")
        sys.exit(1)
    
    # 删除旧表
    logger.info("删除现有表...")
    drop_tables()
    
    # 创建新表
    logger.info("创建新表...")
    if create_tables():
        logger.info("表创建成功")
    else:
        logger.error("表创建失败")
        sys.exit(1)
    
    # 验证表
    if check_tables():
        logger.info("表验证成功")
    else:
        logger.error("表验证失败")
        sys.exit(1)
    
    logger.info("数据库设置完成")


if __name__ == '__main__':
    main() 