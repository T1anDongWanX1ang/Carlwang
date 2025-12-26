#!/usr/bin/env python3
"""
检查历史数据的 is_retweet 字段情况
"""
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.database.connection import db_manager
from src.utils.logger import get_logger

logger = get_logger(__name__)

# 检查 is_retweet 字段
sql = """
SELECT
    is_retweet,
    COUNT(*) as count
FROM twitter_tweet_back_test_cmc300
WHERE update_time >= '2025-12-25 00:00:00'
GROUP BY is_retweet
ORDER BY is_retweet
"""

results = db_manager.execute_query(sql)

logger.info("=" * 70)
logger.info("历史数据 is_retweet 字段统计（自2025-12-25以来）")
logger.info("=" * 70)

for row in results:
    is_retweet = row['is_retweet']
    count = row['count']
    logger.info(f"is_retweet={is_retweet}: {count} 条")

logger.info("=" * 70)

# 同时检查有多少数据 is_retweet 为 NULL 或 0
sql2 = """
SELECT
    SUM(CASE WHEN is_retweet IS NULL THEN 1 ELSE 0 END) as null_count,
    SUM(CASE WHEN is_retweet = 0 THEN 1 ELSE 0 END) as zero_count,
    SUM(CASE WHEN is_retweet = 1 THEN 1 ELSE 0 END) as one_count,
    COUNT(*) as total
FROM twitter_tweet_back_test_cmc300
WHERE update_time >= '2025-12-25 00:00:00'
"""

results2 = db_manager.execute_query(sql2)
if results2:
    row = results2[0]
    logger.info("")
    logger.info(f"总计: {row['total']} 条")
    logger.info(f"  is_retweet IS NULL: {row['null_count']} ({row['null_count']/row['total']*100:.1f}%)")
    logger.info(f"  is_retweet = 0: {row['zero_count']} ({row['zero_count']/row['total']*100:.1f}%)")
    logger.info(f"  is_retweet = 1: {row['one_count']} ({row['one_count']/row['total']*100:.1f}%)")
