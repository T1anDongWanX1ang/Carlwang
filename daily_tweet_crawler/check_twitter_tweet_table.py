#!/usr/bin/env python3
"""
检查 twitter_tweet 表的最新数据
"""
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.database.connection import db_manager
from src.utils.logger import get_logger

logger = get_logger(__name__)

sql = """
SELECT id_str, kol_id, update_time, created_at_datetime
FROM twitter_tweet
WHERE update_time >= '2025-12-26 22:25:00'
ORDER BY update_time DESC
LIMIT 10
"""

results = db_manager.execute_query(sql)
logger.info("twitter_tweet 表最新数据:")
for row in results:
    logger.info(f"ID: {row['id_str']}, kol_id: {row['kol_id']}, update_time: {row['update_time']}, created_at: {row['created_at_datetime']}")

logger.info(f"\n总共 {len(results)} 条记录")
