#!/usr/bin/env python3
import sys
from pathlib import Path
parent_dir = Path(__file__).parent.parent
sys.path.insert(0, str(parent_dir))

from src.database.connection import db_manager

with db_manager.get_cursor() as (conn, cursor):
    # 查看前10条数据的 created_at 字段
    query = """
    SELECT 
        id_str,
        created_at,
        created_at_datetime,
        full_text
    FROM twitter_tweet_back_test_cmc300
    LIMIT 10
    """
    cursor.execute(query)
    results = cursor.fetchall()
    
    print('🔍 数据库中前10条数据的时间字段:')
    print('=' * 100)
    
    for i, row in enumerate(results, 1):
        if isinstance(row, dict):
            id_str = row['id_str']
            created_at = row['created_at']
            created_at_datetime = row['created_at_datetime']
            text = row['full_text'][:50] if row['full_text'] else ''
        else:
            id_str = row[0]
            created_at = row[1]
            created_at_datetime = row[2]
            text = row[3][:50] if row[3] else ''
        
        print(f'{i}. ID: {id_str}')
        print(f'   created_at: {created_at} (type: {type(created_at).__name__})')
        print(f'   created_at_datetime: {created_at_datetime} (type: {type(created_at_datetime).__name__})')
        print(f'   文本: {text}...')
        print()
