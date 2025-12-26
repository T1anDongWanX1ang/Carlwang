#!/usr/bin/env python3
"""
创建twitter_projects表脚本
"""
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.database.connection import db_manager
from src.utils.logger import get_logger


def create_projects_table():
    """创建twitter_projects表"""
    logger = get_logger(__name__)
    
    logger.info("开始创建twitter_projects表...")
    
    # 创建twitter_projects表SQL
    create_table_sql = """
    CREATE TABLE IF NOT EXISTS twitter_projects (
        `project_id` VARCHAR(100) NOT NULL COMMENT "项目标识（主键）",
        `name` VARCHAR(200) NOT NULL COMMENT "项目名称（如Uniswap）",
        `symbol` VARCHAR(50) NOT NULL COMMENT "代币符号（如UNI）",
        `token_address` VARCHAR(100) NULL COMMENT "代币地址",
        `twitter_id` VARCHAR(100) NULL COMMENT "官方推特账号ID",
        `created_at` DATETIME NOT NULL COMMENT "项目纳入系统的时间",
        `category` VARCHAR(100) NULL COMMENT "项目分类（如DEX、L2），唯一值",
        `narratives` JSON NULL COMMENT "项目叙事（如AI Agent、RWA)，可能多个（JSON数组）",
        `sentiment_index` FLOAT NULL COMMENT "项目（代币）推特情绪分，[0, 100]范围",
        `sentiment_history` JSON NULL COMMENT "情绪分历史记录",
        `popularity` BIGINT NULL DEFAULT 0 COMMENT "项目热度（综合推文数量和互动数据计算）",
        `popularity_history` JSON NULL COMMENT "热度历史记录",
        `summary` TEXT NULL COMMENT "AI总结，KOL对此项目的观点总结（通过LLM生成）",
        `last_updated` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT "最后更新时间",
        `update_time` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT "记录更新时间"
    )
    ENGINE=olap
    UNIQUE KEY(`project_id`)
    COMMENT "项目分析主表"
    DISTRIBUTED BY HASH(`project_id`) BUCKETS 12
    PROPERTIES (
        "replication_allocation" = "tag.location.default: 1"
    )
    """
    
    try:
        logger.info("创建twitter_projects表...")
        db_manager.execute_update(create_table_sql)
        logger.info("twitter_projects表创建成功")
        
        # 验证表是否创建成功
        count_result = db_manager.execute_query("SELECT COUNT(*) as count FROM twitter_projects")
        if count_result:
            logger.info(f"twitter_projects表验证成功，当前记录数: {count_result[0]['count']}")
        
        return True
        
    except Exception as e:
        logger.error(f"创建twitter_projects表失败: {e}")
        return False


def main():
    """主函数"""
    logger = get_logger(__name__)
    
    logger.info("twitter_projects表创建工具")
    logger.info("=" * 40)
    
    # 测试连接
    if not db_manager.test_connection():
        logger.error("数据库连接失败")
        sys.exit(1)
    
    # 创建表
    if create_projects_table():
        logger.info("twitter_projects表创建完成")
    else:
        logger.error("twitter_projects表创建失败")
        sys.exit(1)


if __name__ == '__main__':
    main() 