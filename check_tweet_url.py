#!/usr/bin/env python3
"""
检查tweet_url字段
"""
import sys
import os

# 添加项目根目录到路径
sys.path.append(os.path.dirname(__file__))

from src.database.tweet_dao import tweet_dao

def check_tweet_url():
    """检查tweet_url字段"""
    
    try:
        # 连接数据库
        if not tweet_dao.db_manager.test_connection():
            print("数据库连接失败")
            return
        
        # 查询有kol_id的推文的tweet_url值
        sql = """
        SELECT id_str, kol_id, tweet_url, 
               CHAR_LENGTH(tweet_url) as url_length,
               tweet_url IS NULL as is_null,
               tweet_url = '' as is_empty
        FROM twitter_tweet 
        WHERE kol_id IS NOT NULL 
        ORDER BY update_time DESC 
        LIMIT 10
        """
        
        result = tweet_dao.db_manager.execute_query(sql)
        
        if result:
            print("推文URL字段详细检查:")
            print("=" * 100)
            print(f"{'ID':<20} {'KOL_ID':<20} {'URL_LENGTH':<12} {'IS_NULL':<8} {'IS_EMPTY':<8} {'URL':<30}")
            print("-" * 100)
            
            for row in result:
                id_str = str(row.get('id_str', 'N/A'))[:18]
                kol_id = str(row.get('kol_id', 'N/A'))[:18]
                url_length = str(row.get('url_length', 'N/A'))
                is_null = str(row.get('is_null', 'N/A'))
                is_empty = str(row.get('is_empty', 'N/A'))
                tweet_url = row.get('tweet_url')
                url_display = tweet_url[:25] + '...' if tweet_url and len(str(tweet_url)) > 25 else str(tweet_url)
                
                print(f"{id_str:<20} {kol_id:<20} {url_length:<12} {is_null:<8} {is_empty:<8} {url_display:<30}")
            
        else:
            print("未找到相关数据")
            
    except Exception as e:
        print(f"查询失败: {e}")
        
    finally:
        tweet_dao.db_manager.close()

if __name__ == '__main__':
    check_tweet_url()