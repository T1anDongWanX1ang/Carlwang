#!/usr/bin/env python3
"""
查找特定推文ID
"""
import sys
import os

# 添加项目根目录到路径
sys.path.append(os.path.dirname(__file__))

from src.database.tweet_dao import tweet_dao

def find_specific_tweet():
    """查找特定推文ID"""
    
    try:
        # 连接数据库
        if not tweet_dao.db_manager.test_connection():
            print("数据库连接失败")
            return
        
        # 查找特定推文ID（从日志中看到的最新的）
        target_ids = [
            '1965748278731186224',  # 最近看到的有效推文
            '1965751245827924157',  # 最新的推文
            '1965751193055248619',
            '1965751100033908801'
        ]
        
        for tweet_id in target_ids:
            sql = f"""
            SELECT id_str, kol_id, is_valid, sentiment, tweet_url, 
                   LEFT(full_text, 60) as text_preview, update_time
            FROM twitter_tweet 
            WHERE id_str = '{tweet_id}'
            """
            
            result = tweet_dao.db_manager.execute_query(sql)
            
            if result:
                print(f"\n找到推文 {tweet_id}:")
                row = result[0]
                print(f"  - kol_id: {row.get('kol_id')}")
                print(f"  - is_valid: {row.get('is_valid')}")
                print(f"  - sentiment: {row.get('sentiment')}")
                print(f"  - tweet_url: {row.get('tweet_url')}")
                print(f"  - update_time: {row.get('update_time')}")
                print(f"  - text: {row.get('text_preview')}")
            else:
                print(f"\n推文 {tweet_id} 未找到")
        
        # 也查询最新的15条推文，看看实际存储的ID格式
        print("\n=== 最新15条推文的ID格式 ===")
        sql = """
        SELECT id_str, update_time, kol_id, is_valid, sentiment
        FROM twitter_tweet 
        ORDER BY update_time DESC 
        LIMIT 15
        """
        
        result = tweet_dao.db_manager.execute_query(sql)
        
        if result:
            for row in result:
                print(f"ID: {row.get('id_str'):<20} | {row.get('update_time')} | kol_id:{row.get('kol_id')} | valid:{row.get('is_valid')} | sentiment:{row.get('sentiment')}")
            
    except Exception as e:
        print(f"查找推文失败: {e}")
        
    finally:
        tweet_dao.db_manager.close()

if __name__ == '__main__':
    find_specific_tweet()