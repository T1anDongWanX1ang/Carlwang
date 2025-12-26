#!/usr/bin/env python3
"""
修改 twitter_list_members_seed 表结构以匹配 Twitter API 返回字段
API 文档: https://docs.twitterapi.io/api-reference/endpoint/get_list_members
"""
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.database.connection import db_manager
from src.utils.logger import get_logger

def alter_table():
    """修改表结构"""
    logger = get_logger(__name__)

    logger.info("开始修改 twitter_list_members_seed 表结构...")
    logger.info("将添加 Twitter API 返回的所有字段...")

    # 要添加的字段列表
    alter_statements = [
        # 基础身份字段
        ("type", "VARCHAR(20) DEFAULT 'user'", "API返回类型"),
        ("url", "TEXT NULL", "x.com个人主页URL"),

        # 认证相关
        ("is_blue_verified", "TINYINT DEFAULT 0", "是否Twitter Blue认证"),
        ("verified_type", "VARCHAR(50) NULL", "认证类型(如: government)"),

        # 个人资料媒体
        ("profile_picture", "TEXT NULL", "个人头像URL"),
        ("cover_picture", "TEXT NULL", "封面图片URL"),

        # 位置信息
        ("location", "VARCHAR(255) NULL", "用户位置"),

        # 互动指标
        ("favourites_count", "INT DEFAULT 0", "喜欢数量"),
        ("media_count", "INT DEFAULT 0", "媒体数量"),

        # 账户属性
        ("can_dm", "TINYINT DEFAULT 0", "是否可以发送私信"),
        ("has_custom_timelines", "TINYINT DEFAULT 0", "是否有自定义时间线"),
        ("is_translator", "TINYINT DEFAULT 0", "是否为翻译者"),
        ("is_automated", "TINYINT DEFAULT 0", "是否为自动化账户"),
        ("automated_by", "VARCHAR(255) NULL", "自动化账户的操作者"),

        # 简介详情（JSON格式存储）
        ("profile_bio", "JSON NULL", "个人简介详细信息(JSON格式)"),

        # 可用性状态
        ("unavailable", "TINYINT DEFAULT 0", "账户是否不可用"),
        ("unavailable_reason", "VARCHAR(255) NULL", "不可用原因"),
        ("message", "TEXT NULL", "相关消息"),

        # 其他属性
        ("withheld_in_countries", "JSON NULL", "受限国家列表(JSON数组)"),
        ("pinned_tweet_ids", "JSON NULL", "置顶推文ID列表(JSON数组)"),
    ]

    try:
        # 测试连接
        if not db_manager.test_connection():
            logger.error("数据库连接失败")
            return False

        logger.info("数据库连接成功")

        # 获取当前表结构
        desc_sql = "DESCRIBE public_data.twitter_list_members_seed"
        existing_columns = db_manager.execute_query(desc_sql)
        existing_column_names = {col['Field'] for col in existing_columns}

        logger.info(f"当前表有 {len(existing_columns)} 个字段")

        # 逐个添加字段
        added_count = 0
        skipped_count = 0

        for column_name, column_type, comment in alter_statements:
            if column_name in existing_column_names:
                logger.info(f"  ⊘ 跳过已存在的字段: {column_name}")
                skipped_count += 1
                continue

            try:
                alter_sql = f"""
                ALTER TABLE public_data.twitter_list_members_seed
                ADD COLUMN `{column_name}` {column_type} COMMENT '{comment}'
                """
                db_manager.execute_update(alter_sql)
                logger.info(f"  ✓ 添加字段: {column_name} ({column_type})")
                added_count += 1
            except Exception as e:
                logger.warning(f"  ✗ 添加字段 {column_name} 失败: {e}")

        logger.info(f"\n字段添加完成:")
        logger.info(f"  - 新增: {added_count} 个")
        logger.info(f"  - 跳过: {skipped_count} 个")

        # 添加索引
        logger.info("\n添加索引...")
        index_statements = [
            ("idx_is_blue_verified", "is_blue_verified"),
            ("idx_verified_type", "verified_type"),
            ("idx_favourites_count", "favourites_count DESC"),
            ("idx_media_count", "media_count DESC"),
        ]

        for index_name, index_column in index_statements:
            try:
                # 检查索引是否已存在
                check_index_sql = f"""
                SHOW INDEX FROM public_data.twitter_list_members_seed
                WHERE Key_name = '{index_name}'
                """
                existing_index = db_manager.execute_query(check_index_sql)

                if existing_index:
                    logger.info(f"  ⊘ 索引已存在: {index_name}")
                    continue

                create_index_sql = f"""
                CREATE INDEX {index_name}
                ON public_data.twitter_list_members_seed({index_column})
                """
                db_manager.execute_update(create_index_sql)
                logger.info(f"  ✓ 创建索引: {index_name}")
            except Exception as e:
                logger.warning(f"  ✗ 创建索引 {index_name} 失败: {e}")

        # 验证最终表结构
        logger.info("\n验证表结构...")
        final_columns = db_manager.execute_query(desc_sql)
        logger.info(f"修改后的表共有 {len(final_columns)} 个字段")

        logger.info("\n新增的字段:")
        new_column_names = {col[0] for col in alter_statements}
        for col in final_columns:
            if col['Field'] in new_column_names:
                logger.info(f"  - {col['Field']}: {col['Type']}")

        return True

    except Exception as e:
        logger.error(f"修改表结构失败: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False

if __name__ == '__main__':
    logger = get_logger(__name__)
    logger.info("=" * 70)
    logger.info("修改 twitter_list_members_seed 表结构")
    logger.info("匹配 Twitter API 返回字段")
    logger.info("API: https://docs.twitterapi.io/api-reference/endpoint/get_list_members")
    logger.info("=" * 70)

    if alter_table():
        print("\n✓ 表结构修改成功！")
        print("\n字段映射说明:")
        print("  API字段 -> 数据库字段")
        print("  id -> twitter_user_id")
        print("  userName -> username")
        print("  isBlueVerified -> is_blue_verified")
        print("  profilePicture -> profile_picture")
        print("  favouritesCount -> favourites_count")
        print("  ... 等等")
        print("\n下一步：更新 fetch_list_members.py 以使用新字段")
    else:
        print("\n✗ 表结构修改失败")
        sys.exit(1)
