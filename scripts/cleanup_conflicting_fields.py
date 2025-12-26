#!/usr/bin/env python3
"""
清理 twitter_list_members_seed 表中与API字段冲突的旧字段
以API返回的字段为准
"""
import sys
from pathlib import Path

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.database.connection import db_manager
from src.utils.logger import get_logger

def cleanup_conflicting_fields():
    """删除与API字段冲突的旧字段"""
    logger = get_logger(__name__)

    logger.info("开始清理与API字段冲突的旧字段...")

    # 冲突字段分析:
    # avatar (旧) vs profile_picture (API: profilePicture) - 保留 profile_picture，删除 avatar

    conflicting_fields = [
        {
            'old_field': 'avatar',
            'new_field': 'profile_picture',
            'api_field': 'profilePicture',
            'reason': 'API返回profilePicture，应使用profile_picture'
        }
    ]

    try:
        # 测试连接
        if not db_manager.test_connection():
            logger.error("数据库连接失败")
            return False

        logger.info("数据库连接成功\n")

        # 显示冲突字段
        logger.info("检测到以下冲突字段:")
        logger.info("=" * 80)
        for conflict in conflicting_fields:
            logger.info(f"旧字段: {conflict['old_field']}")
            logger.info(f"API字段: {conflict['api_field']} -> 数据库字段: {conflict['new_field']}")
            logger.info(f"原因: {conflict['reason']}")
            logger.info("-" * 80)

        # 执行删除
        logger.info("\n开始删除冲突的旧字段...\n")

        for conflict in conflicting_fields:
            old_field = conflict['old_field']
            try:
                # 先将旧字段的数据迁移到新字段（如果新字段为空）
                logger.info(f"  迁移数据: {old_field} -> {conflict['new_field']}")
                migrate_sql = f"""
                UPDATE public_data.twitter_list_members_seed
                SET {conflict['new_field']} = {old_field}
                WHERE {conflict['new_field']} IS NULL AND {old_field} IS NOT NULL
                """
                affected = db_manager.execute_update(migrate_sql)
                logger.info(f"    ✓ 迁移了 {affected} 条记录")

                # 删除旧字段
                logger.info(f"  删除旧字段: {old_field}")
                drop_sql = f"ALTER TABLE public_data.twitter_list_members_seed DROP COLUMN {old_field}"
                db_manager.execute_update(drop_sql)
                logger.info(f"    ✓ 已删除字段 {old_field}\n")

            except Exception as e:
                logger.error(f"    ✗ 处理字段 {old_field} 失败: {e}\n")
                continue

        # 验证最终表结构
        logger.info("验证表结构...")
        desc_sql = "DESCRIBE public_data.twitter_list_members_seed"
        final_columns = db_manager.execute_query(desc_sql)
        logger.info(f"清理后的表共有 {len(final_columns)} 个字段\n")

        logger.info("关键字段验证:")
        logger.info("-" * 60)
        key_fields = ['profile_picture', 'cover_picture', 'is_blue_verified',
                     'verified_type', 'favourites_count', 'media_count']
        for col in final_columns:
            if col['Field'] in key_fields:
                logger.info(f"  ✓ {col['Field']:30s} {col['Type']}")

        return True

    except Exception as e:
        logger.error(f"清理字段失败: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False

if __name__ == '__main__':
    logger = get_logger(__name__)
    logger.info("=" * 80)
    logger.info("清理 twitter_list_members_seed 表的冲突字段")
    logger.info("以 Twitter API 返回的字段为准")
    logger.info("=" * 80)

    if cleanup_conflicting_fields():
        print("\n✓ 冲突字段清理成功！")
        print("\n字段对应关系:")
        print("  API: profilePicture -> DB: profile_picture")
        print("  API: coverPicture -> DB: cover_picture")
        print("  API: isBlueVerified -> DB: is_blue_verified")
    else:
        print("\n✗ 冲突字段清理失败")
        sys.exit(1)
