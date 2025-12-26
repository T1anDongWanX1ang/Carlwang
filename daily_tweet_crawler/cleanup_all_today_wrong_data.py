#!/usr/bin/env python3
"""
清理今天所有错误保存到 twitter_tweet 表的项目推文数据
"""
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.database.connection import db_manager
from src.utils.logger import get_logger

logger = get_logger(__name__)

# 删除今天入错的数据（实际是项目推文，应该在 twitter_tweet_back_test_cmc300 表）
sql = """
DELETE FROM twitter_tweet
WHERE update_time >= '2025-12-26 22:25:00' AND update_time < '2025-12-27 00:00:00'
"""

affected_rows = db_manager.execute_update(sql)
logger.info(f"✅ 成功删除 {affected_rows} 条错误数据（update_time 在 22:25:00 到 23:59:59 之间）")
