#!/usr/bin/env python3
"""
优化 twitter_list_members_seed 表结构
删除重复字段，只保留与API返回字段对应的列
"""
import sys
from pathlib import Path

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.database.connection import db_manager
from src.utils.logger import get_logger

def optimize_table():
    """优化表结构"""
    logger = get_logger(__name__)

    logger.info("开始优化 twitter_list_members_seed 表结构...")

    try:
        # 测试连接
        if not db_manager.test_connection():
            logger.error("数据库连接失败")
            return False

        logger.info("数据库连接成功")

        # 字段映射说明
        logger.info("\n字段优化方案:")
        logger.info("  1. 保留 avatar (原字段) - 映射到API的 profilePicture")
        logger.info("  2. 删除 profile_picture (重复字段)")
        logger.info("  3. 保留 is_verified (用于标记任何类型的认证)")
        logger.info("  4. 保留 is_blue_verified (专门标记Twitter Blue)")
        logger.info("  5. 保留 is_protected (虽然API未返回，但保留用于后续扩展)")

        # 询问用户确认
        response = input("\n是否继续删除重复的 profile_picture 字段? (y/n): ")

        if response.lower() != 'y':
            logger.info("已取消操作")
            return False

        # 删除重复字段 profile_picture
        logger.info("\n删除重复字段 profile_picture...")
        try:
            drop_sql = "ALTER TABLE public_data.twitter_list_members_seed DROP COLUMN profile_picture"
            db_manager.execute_update(drop_sql)
            logger.info("  ✓ 已删除字段 profile_picture")
        except Exception as e:
            logger.error(f"  ✗ 删除失败: {e}")
            return False

        # 验证最终表结构
        logger.info("\n验证表结构...")
        desc_sql = "DESCRIBE public_data.twitter_list_members_seed"
        final_columns = db_manager.execute_query(desc_sql)
        logger.info(f"优化后的表共有 {len(final_columns)} 个字段")

        logger.info("\n保留的关键字段:")
        key_fields = ['avatar', 'is_verified', 'is_blue_verified', 'verified_type',
                     'is_protected', 'cover_picture', 'profile_bio']
        for col in final_columns:
            if col['Field'] in key_fields:
                logger.info(f"  ✓ {col['Field']}: {col['Type']}")

        return True

    except Exception as e:
        logger.error(f"优化表结构失败: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False

if __name__ == '__main__':
    logger = get_logger(__name__)
    logger.info("=" * 70)
    logger.info("优化 twitter_list_members_seed 表结构")
    logger.info("删除与 avatar 重复的 profile_picture 字段")
    logger.info("=" * 70)

    if optimize_table():
        print("\n✓ 表结构优化成功！")
        print("\n字段说明:")
        print("  - avatar: 映射API的 profilePicture")
        print("  - cover_picture: 映射API的 coverPicture")
        print("  - is_verified: 通用认证标记")
        print("  - is_blue_verified: Twitter Blue认证")
    else:
        print("\n✗ 表结构优化失败或已取消")
        sys.exit(1)
