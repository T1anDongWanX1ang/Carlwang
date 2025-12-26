#!/usr/bin/env python3
"""
检查最新测试数据的质量
"""
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.database.connection import db_manager
from src.utils.logger import get_logger

logger = get_logger(__name__)

sql = """
SELECT
    id_str, user_id, user_name, is_retweet, sentiment, isAnnounce, is_activity, summary,
    created_at_datetime, update_time
FROM twitter_tweet_back_test_cmc300
WHERE update_time >= '2025-12-26 22:25:00'
ORDER BY update_time DESC
LIMIT 5
"""

results = db_manager.execute_query(sql)
logger.info("=" * 80)
logger.info("最新测试数据（22:26之后 - 修复后的代码）")
logger.info("=" * 80)

for r in results:
    logger.info(f"ID: {r['id_str'][:15]}...")
    logger.info(f"  user_id: {r['user_id'] if r['user_id'] else 'NULL'}")
    logger.info(f"  user_name: {r['user_name'] if r['user_name'] else 'NULL'}")
    logger.info(f"  is_retweet: {r['is_retweet']}")
    logger.info(f"  sentiment: {r['sentiment'] if r['sentiment'] else 'NULL'}")
    logger.info(f"  isAnnounce: {r['isAnnounce']}")
    logger.info(f"  is_activity: {r['is_activity']}")
    logger.info(f"  summary: {r['summary'][:50] + '...' if r['summary'] else 'NULL'}")
    logger.info(f"  update_time: {r['update_time']}")
    logger.info("-" * 80)
