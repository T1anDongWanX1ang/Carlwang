#!/usr/bin/env python3
"""
快速创建 twitter_list_members_seed 表
"""
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.database.connection import db_manager
from src.utils.logger import get_logger

def create_table():
    """创建表"""
    logger = get_logger(__name__)

    logger.info("开始创建 twitter_list_members_seed 表...")

    create_sql = """
    CREATE TABLE IF NOT EXISTS public_data.twitter_list_members_seed (
        `twitter_user_id` VARCHAR(64) NOT NULL COMMENT "Twitter用户唯一ID",
        `username` VARCHAR(255) NOT NULL COMMENT "Twitter用户名",
        `name` VARCHAR(255) NULL COMMENT "用户显示名称",
        `description` TEXT NULL COMMENT "用户简介",
        `avatar` TEXT NULL COMMENT "用户头像URL",
        `source_list_id` VARCHAR(64) NOT NULL COMMENT "来源List ID",
        `source_list_name` VARCHAR(255) NULL COMMENT "List名称",
        `followers_count` INT NULL DEFAULT 0 COMMENT "粉丝数",
        `following_count` INT NULL DEFAULT 0 COMMENT "关注数",
        `statuses_count` INT NULL DEFAULT 0 COMMENT "推文总数",
        `account_created_at` VARCHAR(50) NULL COMMENT "Twitter账户创建时间",
        `status` VARCHAR(20) DEFAULT "pending" COMMENT "处理状态",
        `is_processed` TINYINT DEFAULT 0 COMMENT "是否已处理",
        `error_message` TEXT NULL COMMENT "错误信息",
        `is_verified` TINYINT DEFAULT 0 COMMENT "是否认证账户",
        `is_protected` TINYINT DEFAULT 0 COMMENT "是否私密账户",
        `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT "入库时间",
        `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT "更新时间",
        `processed_at` DATETIME NULL COMMENT "处理时间"
    )
    ENGINE=olap
    UNIQUE KEY(`twitter_user_id`)
    COMMENT "种子用户表-从Twitter List抓取的初始成员"
    DISTRIBUTED BY HASH(`twitter_user_id`) BUCKETS 10
    PROPERTIES (
        "replication_num" = "1"
    )
    """

    try:
        # 测试连接
        if not db_manager.test_connection():
            logger.error("数据库连接失败")
            return False

        logger.info("数据库连接成功")

        # 创建表
        db_manager.execute_update(create_sql)
        logger.info("✓ 表创建成功")

        # 验证表是否创建
        verify_sql = "SHOW TABLES LIKE 'twitter_list_members_seed'"
        result = db_manager.execute_query(verify_sql)

        if result:
            logger.info("✓ 验证成功：表已存在")

            # 查看表结构
            desc_sql = "DESCRIBE public_data.twitter_list_members_seed"
            columns = db_manager.execute_query(desc_sql)

            logger.info(f"\n表结构 (共 {len(columns)} 个字段):")
            for col in columns[:5]:  # 只显示前5个字段
                logger.info(f"  - {col.get('Field')}: {col.get('Type')}")
            logger.info(f"  ... 等 {len(columns)} 个字段")

            return True
        else:
            logger.error("表创建失败：未找到表")
            return False

    except Exception as e:
        logger.error(f"创建表失败: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False

if __name__ == '__main__':
    logger = get_logger(__name__)
    logger.info("=" * 60)
    logger.info("创建 twitter_list_members_seed 表")
    logger.info("=" * 60)

    if create_table():
        print("\n✓ 表创建成功！")
        print("\n下一步：运行 fetch_list_members.py 开始抓取数据")
    else:
        print("\n✗ 表创建失败")
        sys.exit(1)
