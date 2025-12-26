#!/usr/bin/env python3
"""
清理最近入错的数据（update_time >= 22:32:00）
"""
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.database.connection import db_manager
from src.utils.logger import get_logger

logger = get_logger(__name__)

# 删除最近入错的数据
sql = """
DELETE FROM twitter_tweet
WHERE update_time >= '2025-12-26 22:32:00'
"""

affected_rows = db_manager.execute_update(sql)
logger.info(f"✅ 成功删除 {affected_rows} 条错误数据")
