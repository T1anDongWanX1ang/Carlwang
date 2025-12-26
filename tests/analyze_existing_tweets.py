#!/usr/bin/env python3
"""
分析现有推文数据脚本
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


def analyze_existing_tweets():
    """分析现有推文数据"""
    logger = get_logger(__name__)
    
    logger.info("开始分析现有推文数据...")
    
    try:
        # 获取所有推文
        tweet_count = tweet_dao.get_tweet_count()
        logger.info(f"数据库中推文总数: {tweet_count}")
        
        if tweet_count == 0:
            logger.error("没有推文数据可供分析")
            return False
        
        # 分析推文（分批处理以控制成本）
        max_tweets = min(20, tweet_count)  # 限制分析数量以控制API成本
        logger.info(f"将分析最新的 {max_tweets} 条推文")
        
        # 获取最新的推文
        from datetime import datetime, timedelta
        end_time = datetime.now()
        start_time = end_time - timedelta(days=7)  # 最近7天的推文
        
        recent_tweets = tweet_dao.get_tweets_by_date_range(
            start_date=start_time,
            end_date=end_time,
            limit=max_tweets
        )
        
        if not recent_tweets:
            logger.error("没有找到最近的推文数据")
            return False
        
        logger.info(f"获取到 {len(recent_tweets)} 条最近推文")
        
        # 使用话题引擎分析
        success = topic_engine.analyze_recent_tweets(hours=24*7, max_tweets=max_tweets)
        
        if success:
            logger.info("话题分析完成")
            
            # 显示结果
            topic_count = topic_dao.get_topic_count()
            logger.info(f"生成的话题总数: {topic_count}")
            
            if topic_count > 0:
                # 显示热门话题
                hot_topics = topic_dao.get_hot_topics(limit=5)
                logger.info("\n=== 生成的热门话题 ===")
                for i, topic in enumerate(hot_topics, 1):
                    logger.info(f"\n话题 {i}: {topic.topic_name}")
                    logger.info(f"  简介: {topic.brief}")
                    logger.info(f"  热度: {topic.popularity}")
                    logger.info(f"  情感方向: {topic.mob_opinion_direction}")
                    logger.info(f"  传播速度(5m): {topic.propagation_speed_5m}")
                    logger.info(f"  传播速度(1h): {topic.propagation_speed_1h}")
                    if topic.summary:
                        logger.info(f"  AI总结: {topic.summary}")
            
            # 显示统计信息
            stats = topic_engine.get_topic_statistics()
            logger.info(f"\n=== 分析统计 ===")
            logger.info(f"ChatGPT请求数: {stats.get('chatgpt_stats', {}).get('chatgpt_requests', 0)}")
            logger.info(f"ChatGPT成功率: {stats.get('chatgpt_stats', {}).get('chatgpt_success_rate', 0):.1f}%")
            logger.info(f"生成话题数: {stats.get('topics_generated', 0)}")
            
            return True
        else:
            logger.error("话题分析失败")
            return False
        
    except Exception as e:
        logger.error(f"分析现有推文失败: {e}")
        return False


def main():
    """主函数"""
    logger = get_logger(__name__)
    
    logger.info("现有推文话题分析工具")
    logger.info("=" * 50)
    
    # 运行分析
    if analyze_existing_tweets():
        logger.info("推文话题分析完成")
    else:
        logger.error("推文话题分析失败")
        sys.exit(1)


if __name__ == '__main__':
    main() 