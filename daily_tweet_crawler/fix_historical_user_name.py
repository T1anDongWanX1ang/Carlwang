#!/usr/bin/env python3
"""
修复历史数据的 user_name 字段
从 twitter_user 表中根据 user_id 关联获取 screen_name
"""
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.database.connection import db_manager
from src.utils.logger import get_logger

logger = get_logger(__name__)

def fix_user_name():
    """修复 user_name 字段"""
    try:
        # 1. 先检查需要修复的数据量
        check_sql = """
        SELECT COUNT(*) as need_fix_count
        FROM twitter_tweet_back_test_cmc300
        WHERE user_id IS NOT NULL
          AND user_name IS NULL
          AND update_time >= '2025-12-25 00:00:00'
        """

        results = db_manager.execute_query(check_sql)
        if results:
            need_fix_count = results[0]['need_fix_count']
            logger.info(f"需要修复 user_name 的记录数: {need_fix_count}")

            if need_fix_count == 0:
                logger.info("✅ 没有需要修复的数据")
                return True

        # 2. 查询需要修复的数据（user_id 和对应的 screen_name）
        query_sql = """
        SELECT DISTINCT t.user_id, u.screen_name
        FROM twitter_tweet_back_test_cmc300 t
        INNER JOIN twitter_user u ON t.user_id = u.id_str
        WHERE t.user_id IS NOT NULL
          AND t.user_name IS NULL
          AND t.update_time >= '2025-12-25 00:00:00'
        """

        user_mapping = db_manager.execute_query(query_sql)
        logger.info(f"找到 {len(user_mapping)} 个用户需要修复")

        # 3. 逐个修复
        fixed_count = 0
        for row in user_mapping:
            user_id = row['user_id']
            screen_name = row['screen_name']

            update_sql = """
            UPDATE twitter_tweet_back_test_cmc300
            SET user_name = %s
            WHERE user_id = %s
              AND user_name IS NULL
              AND update_time >= '2025-12-25 00:00:00'
            """

            affected = db_manager.execute_update(update_sql, (screen_name, user_id))
            if affected > 0:
                fixed_count += affected
                logger.info(f"修复 user_id={user_id} 的 {affected} 条记录 -> user_name={screen_name}")

        logger.info(f"✅ 成功修复 {fixed_count} 条记录的 user_name")

        # 4. 再次检查
        results2 = db_manager.execute_query(check_sql)
        if results2:
            remaining = results2[0]['need_fix_count']
            if remaining == 0:
                logger.info("✅ 所有数据已修复完成")
            else:
                logger.warning(f"⚠️  仍有 {remaining} 条记录未修复（可能twitter_user表中没有对应用户）")

        return True

    except Exception as e:
        logger.error(f"修复 user_name 失败: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False

if __name__ == '__main__':
    logger.info("=" * 70)
    logger.info("开始修复历史数据的 user_name 字段")
    logger.info("=" * 70)

    success = fix_user_name()

    if success:
        logger.info("修复完成")
        sys.exit(0)
    else:
        logger.error("修复失败")
        sys.exit(1)
