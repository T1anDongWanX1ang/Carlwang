#!/usr/bin/env python3
"""
为 twitter_tweet 表添加活动字段
添加 is_activity 字段用于标记活动推文
"""
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.database.connection import db_manager
from src.utils.logger import get_logger


def add_activity_field():
    """为 twitter_tweet 表添加 is_activity 字段"""
    logger = get_logger(__name__)

    logger.info("=" * 60)
    logger.info("数据库迁移：添加 is_activity 字段到 twitter_tweet 表")
    logger.info("=" * 60)

    # 获取表名
    table_name = db_manager.db_config.get('tables', {}).get('tweet', 'twitter_tweet')

    # 需要添加的字段
    alter_statement = f"""
    ALTER TABLE {table_name}
    ADD COLUMN `is_activity` TINYINT NULL DEFAULT 0
    COMMENT '是否为活动推文 (0=否, 1=是, 包含campaign/airdrop/quest/reward/giveaway)'
    """

    try:
        logger.info(f"目标表: {table_name}")
        logger.info("准备添加 is_activity 字段...")

        logger.debug(f"执行SQL: {alter_statement.strip()}")

        db_manager.execute_update(alter_statement)
        logger.info(f"✓ 字段 'is_activity' 添加成功")

        # 验证字段是否添加成功
        verify_field(table_name, logger)

        return True

    except Exception as e:
        error_msg = str(e)
        if "Duplicate column name" in error_msg or "already exists" in error_msg.lower():
            logger.warning(f"⚠ 字段 'is_activity' 已存在，跳过")
            return True
        elif "Syntax error" in error_msg:
            logger.error(f"✗ SQL语法错误: {error_msg}")
            logger.error(f"SQL: {alter_statement.strip()}")
            return False
        else:
            logger.error(f"✗ 添加字段失败: {error_msg}")
            return False


def verify_field(table_name: str, logger):
    """验证字段是否添加成功"""
    try:
        logger.info(f"\n验证 {table_name} 表结构...")

        # 查询表结构
        sql = f"DESCRIBE {table_name}"
        results = db_manager.execute_query(sql)

        # 检查新字段
        field_names = [row['Field'] for row in results]

        if 'is_activity' in field_names:
            logger.info(f"✓ 字段已存在: is_activity")

            # 显示字段详情
            for row in results:
                if row['Field'] == 'is_activity':
                    logger.info(f"\n字段详情:")
                    logger.info(f"  - 字段名: {row['Field']}")
                    logger.info(f"  - 类型: {row['Type']}")
                    logger.info(f"  - 允许NULL: {row['Null']}")
                    logger.info(f"  - 默认值: {row['Default'] or 'NULL'}")
        else:
            logger.warning(f"⚠ 字段不存在: is_activity")

    except Exception as e:
        logger.warning(f"验证表结构时出错: {e}")


def main():
    """主函数"""
    logger = get_logger(__name__)

    logger.info("twitter_tweet 表活动字段迁移工具")
    logger.info("")

    # 测试数据库连接
    if not db_manager.test_connection():
        logger.error("数据库连接失败，请检查配置")
        sys.exit(1)

    logger.info("数据库连接成功\n")

    # 执行迁移
    if add_activity_field():
        logger.info("\n✓ 数据库迁移成功完成")
        logger.info("\n新字段说明:")
        logger.info("  - is_activity: 标识推文是否为活动 (0=否, 1=是)")
        logger.info("  - 活动类型包括: campaign, airdrop, quest, reward, giveaway")
        sys.exit(0)
    else:
        logger.error("\n✗ 数据库迁移失败")
        sys.exit(1)


if __name__ == '__main__':
    main()
