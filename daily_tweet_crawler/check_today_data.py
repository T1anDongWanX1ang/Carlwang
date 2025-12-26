#!/usr/bin/env python3
"""
检查今天所有入库的数据情况
"""
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.database.connection import db_manager
from src.utils.logger import get_logger

logger = get_logger(__name__)

# 检查今天的数据
sql = """
SELECT
    DATE_FORMAT(update_time, '%Y-%m-%d %H:00') as hour_group,
    COUNT(*) as count,
    SUM(CASE WHEN user_name IS NULL THEN 1 ELSE 0 END) as null_user_name_count,
    SUM(CASE WHEN user_id IS NULL THEN 1 ELSE 0 END) as null_user_id_count
FROM twitter_tweet_back_test_cmc300
WHERE DATE(update_time) = '2025-12-26'
GROUP BY hour_group
ORDER BY hour_group
"""

results = db_manager.execute_query(sql)

logger.info("=" * 80)
logger.info("今天 twitter_tweet_back_test_cmc300 表入库数据统计（按小时分组）")
logger.info("=" * 80)

total_count = 0
total_null_user_name = 0
total_null_user_id = 0

for row in results:
    logger.info(f"时间段: {row['hour_group']}")
    logger.info(f"  总数: {row['count']}")
    logger.info(f"  user_name为空: {row['null_user_name_count']} ({row['null_user_name_count']/row['count']*100:.1f}%)")
    logger.info(f"  user_id为空: {row['null_user_id_count']} ({row['null_user_id_count']/row['count']*100:.1f}%)")
    logger.info("-" * 80)

    total_count += row['count']
    total_null_user_name += row['null_user_name_count']
    total_null_user_id += row['null_user_id_count']

logger.info("=" * 80)
logger.info(f"今天总计: {total_count} 条")
logger.info(f"user_name为空: {total_null_user_name} 条 ({total_null_user_name/total_count*100:.1f}%)")
logger.info(f"user_id为空: {total_null_user_id} 条 ({total_null_user_id/total_count*100:.1f}%)")
logger.info("=" * 80)
