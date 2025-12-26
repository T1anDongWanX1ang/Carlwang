#!/usr/bin/env python3
"""
检查推文数量变化
"""
import sys
import os
import time

# 添加项目根目录到路径
sys.path.append(os.path.dirname(__file__))

from src.database.tweet_dao import tweet_dao

def check_tweet_count():
    """检查推文数量"""
    
    try:
        # 连接数据库
        if not tweet_dao.db_manager.test_connection():
            print("数据库连接失败")
            return
        
        # 查询推文总数
        sql = "SELECT COUNT(*) as total FROM twitter_tweet"
        result = tweet_dao.db_manager.execute_query(sql)
        total_count = result[0]['total'] if result else 0
        print(f"推文总数: {total_count}")
        
        # 查询最新5分钟的推文数
        sql = """
        SELECT COUNT(*) as recent_count 
        FROM twitter_tweet 
        WHERE update_time >= DATE_SUB(NOW(), INTERVAL 5 MINUTE)
        """
        result = tweet_dao.db_manager.execute_query(sql)
        recent_count = result[0]['recent_count'] if result else 0
        print(f"最近5分钟的推文: {recent_count}")
        
        # 查询有kol_id的推文数量
        sql = "SELECT COUNT(*) as kol_count FROM twitter_tweet WHERE kol_id IS NOT NULL"
        result = tweet_dao.db_manager.execute_query(sql)
        kol_count = result[0]['kol_count'] if result else 0
        print(f"有kol_id的推文: {kol_count}")
        
        # 查询有is_valid字段的推文数量
        sql = "SELECT COUNT(*) as valid_count FROM twitter_tweet WHERE is_valid IS NOT NULL"
        result = tweet_dao.db_manager.execute_query(sql)
        valid_count = result[0]['valid_count'] if result else 0
        print(f"有is_valid的推文: {valid_count}")
        
        # 查询有sentiment的推文数量
        sql = "SELECT COUNT(*) as sentiment_count FROM twitter_tweet WHERE sentiment IS NOT NULL"
        result = tweet_dao.db_manager.execute_query(sql)
        sentiment_count = result[0]['sentiment_count'] if result else 0
        print(f"有sentiment的推文: {sentiment_count}")
        
        # 查询有tweet_url的推文数量
        sql = "SELECT COUNT(*) as url_count FROM twitter_tweet WHERE tweet_url IS NOT NULL"
        result = tweet_dao.db_manager.execute_query(sql)
        url_count = result[0]['url_count'] if result else 0
        print(f"有tweet_url的推文: {url_count}")
        
    except Exception as e:
        print(f"查询失败: {e}")
        
    finally:
        tweet_dao.db_manager.close()

if __name__ == '__main__':
    check_tweet_count()