#!/usr/bin/env python3
"""
话题分析测试脚本
"""
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.topic_engine import topic_engine
from src.database.tweet_dao import tweet_dao
from src.database.topic_dao import topic_dao
from src.utils.logger import get_logger


def test_topic_analysis():
    """测试话题分析功能"""
    logger = get_logger(__name__)
    
    logger.info("开始测试话题分析功能...")
    
    try:
        # 1. 测试ChatGPT连接
        logger.info("1. 测试ChatGPT API连接...")
        test_topic = topic_engine.topic_analyzer.chatgpt_client.extract_topic_from_tweet(
            "Bitcoin突破新高，市场情绪高涨，投资者纷纷看好后市表现"
        )
        
        if test_topic:
            logger.info(f"ChatGPT连接成功，测试话题: {test_topic}")
        else:
            logger.error("ChatGPT连接失败")
            return False
        
        # 2. 获取最近的推文进行分析
        logger.info("2. 获取最近推文进行话题分析...")
        success = topic_engine.analyze_recent_tweets(hours=1, max_tweets=5)  # 少量测试
        
        if success:
            logger.info("话题分析执行成功")
        else:
            logger.error("话题分析执行失败")
            return False
        
        # 3. 检查生成的话题
        logger.info("3. 检查生成的话题...")
        topic_count = topic_dao.get_topic_count()
        logger.info(f"数据库中话题总数: {topic_count}")
        
        if topic_count > 0:
            # 显示一些话题样例
            hot_topics = topic_dao.get_hot_topics(limit=3)
            logger.info("热门话题样例:")
            for i, topic in enumerate(hot_topics, 1):
                logger.info(f"  话题 {i}: {topic.topic_name}")
                logger.info(f"    简介: {topic.brief}")
                logger.info(f"    热度: {topic.popularity}")
                logger.info(f"    情感方向: {topic.mob_opinion_direction}")
                if topic.summary:
                    logger.info(f"    总结: {topic.summary[:100]}...")
        
        # 4. 显示统计信息
        logger.info("4. 话题分析统计信息:")
        stats = topic_engine.get_topic_statistics()
        for key, value in stats.items():
            logger.info(f"  {key}: {value}")
        
        return True
        
    except Exception as e:
        logger.error(f"话题分析测试失败: {e}")
        return False


def main():
    """主函数"""
    logger = get_logger(__name__)
    
    logger.info("话题分析测试工具")
    logger.info("=" * 40)
    
    # 检查推文数据
    tweet_count = tweet_dao.get_tweet_count()
    logger.info(f"数据库中推文总数: {tweet_count}")
    
    if tweet_count == 0:
        logger.error("数据库中没有推文数据，请先运行爬虫获取推文")
        sys.exit(1)
    
    # 运行话题分析测试
    if test_topic_analysis():
        logger.info("话题分析测试成功")
    else:
        logger.error("话题分析测试失败")
        sys.exit(1)


if __name__ == '__main__':
    main() 