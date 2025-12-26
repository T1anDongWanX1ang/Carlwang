#!/usr/bin/env python3
"""
检查需要删除和重新爬取的数据范围
"""
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.database.connection import db_manager
from src.utils.logger import get_logger

logger = get_logger(__name__)

# Get time range
sql = """
SELECT
    MIN(update_time) as earliest,
    MAX(update_time) as latest,
    COUNT(*) as total,
    SUM(CASE WHEN user_name IS NULL THEN 1 ELSE 0 END) as null_user_name,
    SUM(CASE WHEN user_id IS NULL THEN 1 ELSE 0 END) as null_user_id,
    SUM(CASE WHEN is_retweet = 0 THEN 1 ELSE 0 END) as is_retweet_zero,
    SUM(CASE WHEN is_retweet = 1 THEN 1 ELSE 0 END) as is_retweet_one
FROM twitter_tweet_back_test_cmc300
WHERE update_time >= '2025-12-25 00:00:00'
"""

result = db_manager.execute_query(sql)
if result:
    r = result[0]
    logger.info("=" * 70)
    logger.info("需要删除并重新爬取的数据范围")
    logger.info("=" * 70)
    logger.info(f"时间范围: {r['earliest']} 到 {r['latest']}")
    logger.info(f"总记录数: {r['total']} 条")
    logger.info("")
    logger.info("数据质量问题:")
    logger.info(f"  user_name 为空: {r['null_user_name']} 条 ({r['null_user_name']/r['total']*100:.1f}%)")
    logger.info(f"  user_id 为空: {r['null_user_id']} 条 ({r['null_user_id']/r['total']*100:.1f}%)")
    logger.info(f"  is_retweet = 0: {r['is_retweet_zero']} 条 ({r['is_retweet_zero']/r['total']*100:.1f}%)")
    logger.info(f"  is_retweet = 1: {r['is_retweet_one']} 条 ({r['is_retweet_one']/r['total']*100:.1f}%)")
    logger.info("=" * 70)
