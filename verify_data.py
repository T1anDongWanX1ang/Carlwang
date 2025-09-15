#!/usr/bin/env python3
"""
验证存储数据脚本
"""
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.database.connection import db_manager
from src.utils.logger import get_logger


def verify_data():
    """验证存储的数据"""
    logger = get_logger(__name__)
    
    logger.info("验证存储的数据...")
    
    try:
        # 检查推文数据
        logger.info("推文表数据样例:")
        tweet_samples = db_manager.execute_query("SELECT * FROM twitter_tweet LIMIT 3")
        for i, tweet in enumerate(tweet_samples, 1):
            logger.info(f"  推文 {i}: ID={tweet['id_str']}, 内容={tweet['full_text'][:50] if tweet['full_text'] else 'N/A'}...")
        
        tweet_count = db_manager.execute_query("SELECT COUNT(*) as count FROM twitter_tweet")[0]['count']
        logger.info(f"推文总数: {tweet_count}")
        
        print()
        
        # 检查用户数据
        logger.info("用户表数据样例:")
        user_samples = db_manager.execute_query("SELECT * FROM twitter_user LIMIT 3")
        for i, user in enumerate(user_samples, 1):
            logger.info(f"  用户 {i}: ID={user['id_str']}, 用户名=@{user['screen_name']}, 姓名={user['name']}")
        
        user_count = db_manager.execute_query("SELECT COUNT(*) as count FROM twitter_user")[0]['count']
        logger.info(f"用户总数: {user_count}")
        
        print()
        
        # 检查热门推文
        logger.info("热门推文（按互动总量排序）:")
        popular_tweets = db_manager.execute_query("""
            SELECT id_str, full_text, engagement_total, view_count 
            FROM twitter_tweet 
            WHERE engagement_total > 0 
            ORDER BY engagement_total DESC 
            LIMIT 3
        """)
        for i, tweet in enumerate(popular_tweets, 1):
            logger.info(f"  热门推文 {i}: 互动={tweet['engagement_total']}, 浏览={tweet['view_count']}, 内容={tweet['full_text'][:50]}...")
        
        print()
        
        # 检查热门用户
        logger.info("热门用户（按粉丝数排序）:")
        popular_users = db_manager.execute_query("""
            SELECT id_str, screen_name, name, followers_count 
            FROM twitter_user 
            ORDER BY followers_count DESC 
            LIMIT 3
        """)
        for i, user in enumerate(popular_users, 1):
            logger.info(f"  热门用户 {i}: @{user['screen_name']}, 粉丝={user['followers_count']}")
        
        return True
        
    except Exception as e:
        logger.error(f"验证数据失败: {e}")
        return False


def main():
    """主函数"""
    logger = get_logger(__name__)
    
    logger.info("数据验证工具")
    logger.info("=" * 30)
    
    # 测试连接
    if not db_manager.test_connection():
        logger.error("数据库连接失败")
        sys.exit(1)
    
    # 验证数据
    verify_data()


if __name__ == '__main__':
    main() 