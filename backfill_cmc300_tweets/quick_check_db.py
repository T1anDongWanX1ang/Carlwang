#!/usr/bin/env python3
import sys
from pathlib import Path
parent_dir = Path(__file__).parent.parent
sys.path.insert(0, str(parent_dir))

from src.database.connection import db_manager

with db_manager.get_cursor() as (conn, cursor):
    query = """
    SELECT
        COUNT(*) as total,
        MIN(created_at) as earliest,
        MAX(created_at) as latest
    FROM twitter_tweet_back_test_cmc300
    WHERE created_at >= '2025-12-22'
    """
    cursor.execute(query)
    result = cursor.fetchone()

    print(f'📊 2025-12-22 之后的推文统计:')
    if result:
        if isinstance(result, dict):
            print(f'   总数: {result["total"]:,} 条')
            print(f'   最早: {result["earliest"]}')
            print(f'   最新: {result["latest"]}')
        else:
            print(f'   总数: {result[0]:,} 条')
            print(f'   最早: {result[1]}')
            print(f'   最新: {result[2]}')
    else:
        print('   无数据')
