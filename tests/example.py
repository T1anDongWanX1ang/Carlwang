#!/usr/bin/env python3
"""
Twitter数据爬虫使用示例
"""
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.crawler import crawler
from src.utils.config_manager import config
from src.utils.logger import get_logger
from src.database.tweet_dao import tweet_dao
from src.database.user_dao import user_dao
from src.api.twitter_api import twitter_api


def example_basic_usage():
    """基本使用示例"""
    logger = get_logger(__name__)
    
    logger.info("=== 基本使用示例 ===")
    
    # 1. 测试连接
    logger.info("1. 测试数据库连接...")
    db_success = crawler.test_connection()
    logger.info(f"数据库连接: {'成功' if db_success else '失败'}")
    
    logger.info("2. 测试API连接...")
    api_success = crawler.test_api_connection()
    logger.info(f"API连接: {'成功' if api_success else '失败'}")
    
    # 2. 单次爬取（少量数据用于测试）
    if db_success and api_success:
        logger.info("3. 执行单次数据爬取...")
        success = crawler.crawl_tweets(max_pages=1, page_size=10)
        logger.info(f"爬取结果: {'成功' if success else '失败'}")
        
        # 显示统计信息
        stats = crawler.get_statistics()
        logger.info(f"爬取统计: {stats}")


def example_configuration():
    """配置管理示例"""
    logger = get_logger(__name__)
    
    logger.info("=== 配置管理示例 ===")
    
    # 获取各种配置
    api_config = config.get_api_config()
    db_config = config.get_database_config()
    scheduler_config = config.get_scheduler_config()
    field_mapping = config.get_field_mapping()
    
    logger.info(f"API基础URL: {api_config.get('base_url')}")
    logger.info(f"数据库主机: {db_config.get('host')}:{db_config.get('port')}")
    logger.info(f"调度间隔: {scheduler_config.get('interval_minutes')} 分钟")
    logger.info(f"字段映射数量: {len(field_mapping)}")
    
    # 动态修改配置（示例）
    original_interval = config.get('scheduler.interval_minutes')
    logger.info(f"原始调度间隔: {original_interval} 分钟")
    
    # 更新配置
    config.update_config('scheduler.interval_minutes', 10)
    new_interval = config.get('scheduler.interval_minutes')
    logger.info(f"新的调度间隔: {new_interval} 分钟")
    
    # 恢复原始配置
    config.update_config('scheduler.interval_minutes', original_interval)
    logger.info("配置已恢复")


def example_database_operations():
    """数据库操作示例"""
    logger = get_logger(__name__)
    
    logger.info("=== 数据库操作示例 ===")
    
    # 获取推文总数
    total_count = tweet_dao.get_tweet_count()
    logger.info(f"数据库中推文总数: {total_count}")
    
    # 获取用户总数
    user_count = user_dao.get_user_count()
    logger.info(f"数据库中用户总数: {user_count}")
    
    # 如果有数据，查询最新的几条
    if total_count > 0:
        from datetime import datetime, timedelta
        
        # 查询最近7天的推文
        end_date = datetime.now()
        start_date = end_date - timedelta(days=7)
        
        recent_tweets = tweet_dao.get_tweets_by_date_range(
            start_date=start_date,
            end_date=end_date,
            limit=5
        )
        
        logger.info(f"最近7天的推文数量: {len(recent_tweets)}")
        
        for tweet in recent_tweets[:3]:  # 显示前3条
            logger.info(f"推文 {tweet.id_str}: {tweet.full_text[:50] if tweet.full_text else 'N/A'}...")


def example_api_operations():
    """API操作示例"""
    logger = get_logger(__name__)
    
    logger.info("=== API操作示例 ===")
    
    # 获取API统计信息
    stats = twitter_api.get_request_stats()
    logger.info(f"API请求统计: {stats}")
    
    # 尝试获取少量数据（用于测试）
    logger.info("尝试获取1条推文数据...")
    try:
        test_tweets = twitter_api.fetch_tweets(count=1)
        logger.info(f"获取到 {len(test_tweets)} 条测试数据")
        
        if test_tweets:
            # 显示第一条推文的结构
            first_tweet = test_tweets[0]
            logger.info(f"推文数据结构示例: {list(first_tweet.keys())}")
            
    except Exception as e:
        logger.error(f"API测试失败: {e}")


def example_data_mapping():
    """数据映射示例"""
    logger = get_logger(__name__)
    
    logger.info("=== 数据映射示例 ===")
    
    # 模拟API数据
    mock_api_data = {
        "bookmark_count": 5,
        "conversation_id_str": "1234567890123456789",
        "created_at": "Mon Jan 01 12:00:00 +0000 2024",
        "favorite_count": 100,
        "full_text": "这是一条测试推文内容",
        "id_str": "1234567890123456789",
        "in_reply_to_status_id_str": None,
        "is_quote_status": False,
        "quote_count": 10,
        "reply_count": 25,
        "retweet_count": 50,
        "view_count": 1000,
        "user": {
            "avatar": "https://example.com/avatar.jpg",
            "can_dm": True,
            "created_at": "Mon Jan 01 10:00:00 +0000 2020",
            "description": "这是一个测试用户的简介",
            "followers_count": 1500,
            "friends_count": 300,
            "id_str": "9876543210987654321",
            "name": "测试用户",
            "screen_name": "test_user",
            "statuses_count": 500
        }
    }
    
    logger.info("模拟API数据映射...")
    
    # 使用数据映射器
    from src.utils.data_mapper import data_mapper
    
    # 映射推文数据
    tweet = data_mapper.map_api_data_to_tweet(mock_api_data)
    
    if tweet:
        logger.info(f"推文映射成功: {tweet}")
        logger.info(f"互动总量: {tweet.engagement_total}")
        logger.info(f"推文数据验证: {'通过' if tweet.validate() else '失败'}")
        
        # 转换为数据库格式
        db_data = tweet.to_dict()
        logger.info(f"推文数据库字段数量: {len(db_data)}")
    else:
        logger.error("推文数据映射失败")
    
    # 映射用户数据
    if 'user' in mock_api_data:
        user = data_mapper.map_api_data_to_user(mock_api_data['user'])
        
        if user:
            logger.info(f"用户映射成功: {user}")
            logger.info(f"用户数据验证: {'通过' if user.validate() else '失败'}")
            
            # 转换为数据库格式
            user_db_data = user.to_dict()
            logger.info(f"用户数据库字段数量: {len(user_db_data)}")
        else:
            logger.error("用户数据映射失败")
    
    # 测试从推文中提取用户
    users_from_tweets = data_mapper.extract_users_from_tweets([mock_api_data])
    logger.info(f"从推文中提取到 {len(users_from_tweets)} 个用户")


def main():
    """主函数"""
    logger = get_logger(__name__)
    
    logger.info("Twitter数据爬虫使用示例")
    logger.info("=" * 50)
    
    try:
        # 运行各种示例
        example_configuration()
        print()
        
        example_data_mapping()
        print()
        
        example_database_operations()
        print()
        
        example_api_operations()
        print()
        
        example_basic_usage()
        
    except Exception as e:
        logger.error(f"示例执行异常: {e}")
    finally:
        # 清理资源
        crawler.close()
        logger.info("示例执行完成")


if __name__ == '__main__':
    main() 