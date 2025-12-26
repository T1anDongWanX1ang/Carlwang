#!/usr/bin/env python3
"""
数据库迁移脚本：为 twitter_projects 表添加活动公告相关字段
添加字段：
- is_announce: 是否为活动公告 (0=否, 1=是)
- announce_summary: 活动摘要（当is_announce=1时）
"""
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.database.connection import db_manager
from src.utils.logger import get_logger


def add_campaign_fields():
    """为 twitter_projects 表添加活动公告相关字段"""
    logger = get_logger(__name__)

    logger.info("=" * 60)
    logger.info("数据库迁移：添加活动公告字段到 twitter_projects 表")
    logger.info("=" * 60)

    # 获取表名
    table_name = db_manager.db_config.get('tables', {}).get('project', 'twitter_projects')

    # 需要添加的字段
    alter_statements = [
        f"""
        ALTER TABLE {table_name}
        ADD COLUMN `is_announce` TINYINT NULL DEFAULT 0
        COMMENT '是否为活动公告 (0=否, 1=是)'
        """,
        f"""
        ALTER TABLE {table_name}
        ADD COLUMN `announce_summary` TEXT NULL
        COMMENT '活动摘要（当is_announce=1时，包含活动详情）'
        """
    ]

    try:
        logger.info(f"目标表: {table_name}")
        logger.info(f"准备添加 {len(alter_statements)} 个字段...")

        success_count = 0

        for i, sql in enumerate(alter_statements, 1):
            try:
                field_name = "is_announce" if i == 1 else "announce_summary"
                logger.info(f"\n[{i}/{len(alter_statements)}] 添加字段: {field_name}")
                logger.debug(f"执行SQL: {sql.strip()}")

                db_manager.execute_update(sql)
                success_count += 1
                logger.info(f"✓ 字段 '{field_name}' 添加成功")

            except Exception as e:
                error_msg = str(e)
                if "Duplicate column name" in error_msg or "already exists" in error_msg.lower():
                    logger.warning(f"⚠ 字段 '{field_name}' 已存在，跳过")
                    success_count += 1  # 已存在也算成功
                elif "Syntax error" in error_msg:
                    logger.error(f"✗ SQL语法错误: {error_msg}")
                    logger.error(f"SQL: {sql.strip()}")
                else:
                    logger.error(f"✗ 添加字段失败: {error_msg}")

        logger.info("\n" + "=" * 60)
        logger.info(f"迁移完成！成功处理 {success_count}/{len(alter_statements)} 个字段")
        logger.info("=" * 60)

        # 验证字段是否添加成功
        verify_fields(table_name, logger)

        return success_count == len(alter_statements)

    except Exception as e:
        logger.error(f"\n数据库迁移失败: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False


def verify_fields(table_name: str, logger):
    """验证字段是否添加成功"""
    try:
        logger.info(f"\n验证 {table_name} 表结构...")

        # 查询表结构
        sql = f"DESCRIBE {table_name}"
        results = db_manager.execute_query(sql)

        # 检查新字段
        field_names = [row['Field'] for row in results]

        required_fields = ['is_announce', 'announce_summary']
        missing_fields = []
        existing_fields = []

        for field in required_fields:
            if field in field_names:
                existing_fields.append(field)
            else:
                missing_fields.append(field)

        if missing_fields:
            logger.warning(f"⚠ 缺失字段: {', '.join(missing_fields)}")

        if existing_fields:
            logger.info(f"✓ 已存在字段: {', '.join(existing_fields)}")

        # 显示完整的表结构（只显示新添加的字段）
        logger.info(f"\n新添加的字段详情:")
        for row in results:
            if row['Field'] in required_fields:
                logger.info(f"  - {row['Field']}: {row['Type']} {row['Null']} {row['Default'] or ''}")

    except Exception as e:
        logger.warning(f"验证表结构时出错: {e}")


def main():
    """主函数"""
    logger = get_logger(__name__)

    logger.info("twitter_projects 表活动公告字段迁移工具")
    logger.info("")

    # 测试数据库连接
    if not db_manager.test_connection():
        logger.error("数据库连接失败，请检查配置")
        sys.exit(1)

    logger.info("数据库连接成功\n")

    # 执行迁移
    if add_campaign_fields():
        logger.info("\n✓ 数据库迁移成功完成")
        logger.info("\n新字段说明:")
        logger.info("  - is_announce: 标识项目是否有活动公告 (0=否, 1=是)")
        logger.info("  - announce_summary: 存储活动摘要信息（包括活动类型、要求、时间等）")
        sys.exit(0)
    else:
        logger.error("\n✗ 数据库迁移失败")
        sys.exit(1)


if __name__ == '__main__':
    main()
