#!/usr/bin/env python3
"""
验证项目推文数据是否正确保存到 twitter_tweet_back_test_cmc300 表
"""
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.database.connection import db_manager
from src.utils.logger import get_logger

logger = get_logger(__name__)

def verify_data():
    """验证最新数据"""
    try:
        # 1. 检查 twitter_tweet_back_test_cmc300 表最新数据
        sql1 = """
        SELECT id_str, user_id, user_name, sentiment, isAnnounce, is_activity, created_at_datetime, update_time
        FROM twitter_tweet_back_test_cmc300
        WHERE update_time >= '2025-12-26 22:25:00'
        ORDER BY update_time DESC
        LIMIT 5
        """
        results1 = db_manager.execute_query(sql1)

        logger.info("=" * 70)
        logger.info("✅ twitter_tweet_back_test_cmc300 表最新数据 (应该有数据)")
        logger.info("=" * 70)
        if results1:
            for row in results1:
                logger.info(f"ID: {row['id_str']}")
                logger.info(f"  user_id: {row['user_id']}")
                logger.info(f"  user_name: {row['user_name']}")
                logger.info(f"  sentiment: {row['sentiment']}")
                logger.info(f"  isAnnounce: {row['isAnnounce']}")
                logger.info(f"  is_activity: {row['is_activity']}")
                logger.info(f"  created_at: {row['created_at_datetime']}")
                logger.info(f"  update_time: {row['update_time']}")
                logger.info("-" * 70)
        else:
            logger.warning("⚠️  没有找到最新数据!")

        # 2. 检查 twitter_tweet 表最新数据（应该没有新增）
        sql2 = """
        SELECT COUNT(*) as count
        FROM twitter_tweet
        WHERE update_time >= '2025-12-26 22:25:00'
        """
        results2 = db_manager.execute_query(sql2)

        logger.info("")
        logger.info("=" * 70)
        logger.info("❌ twitter_tweet 表最新数据 (应该没有新增)")
        logger.info("=" * 70)
        if results2:
            count = results2[0]['count']
            if count == 0:
                logger.info("✅ 正确！twitter_tweet 表没有新增数据")
            else:
                logger.error(f"⚠️  错误！twitter_tweet 表有 {count} 条新增数据（不应该有）")

        logger.info("")
        logger.info("=" * 70)
        logger.info("验证完成")
        logger.info("=" * 70)

        return True

    except Exception as e:
        logger.error(f"验证数据失败: {e}")
        return False


if __name__ == '__main__':
    verify_data()
