#!/usr/bin/env python3
"""
项目分析测试脚本
"""
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.project_engine import project_engine
from src.database.tweet_dao import tweet_dao
from src.database.project_dao import project_dao
from src.utils.logger import get_logger


def test_project_analysis():
    """测试项目分析功能"""
    logger = get_logger(__name__)
    
    logger.info("开始测试项目分析功能...")
    
    try:
        # 1. 检查推文数据
        tweet_count = tweet_dao.get_tweet_count()
        logger.info(f"数据库中推文总数: {tweet_count}")
        
        if tweet_count == 0:
            logger.error("数据库中没有推文数据，请先运行爬虫获取推文")
            return False
        
        # 2. 获取一些最近推文进行测试
        from datetime import datetime, timedelta
        cutoff_time = datetime.now() - timedelta(hours=24)
        recent_tweets = tweet_dao.get_recent_tweets(since_time=cutoff_time, limit=20)
        logger.info(f"获取到 {len(recent_tweets)} 条最近推文用于测试")
        
        # 显示推文样例
        for i, tweet in enumerate(recent_tweets[:3], 1):
            content = tweet.full_text[:100] + "..." if len(tweet.full_text) > 100 else tweet.full_text
            logger.info(f"  {i}. {content}")
        
        # 3. 测试ChatGPT项目分析
        logger.info("\n3. 测试ChatGPT项目分析...")
        if recent_tweets:
            # 准备测试数据
            test_tweets_data = []
            for tweet in recent_tweets[:5]:
                tweet_data = {
                    'tweet_id': tweet.id_str,
                    'content': tweet.full_text,
                    'user_screen_name': 'test_user',
                    'engagement_total': tweet.engagement_total or 0
                }
                test_tweets_data.append(tweet_data)
            
            # 调用ChatGPT分析
            analysis_result = project_engine.project_analyzer.chatgpt_client.analyze_projects_in_tweets(test_tweets_data)
            
            if analysis_result:
                logger.info(f"ChatGPT项目分析成功:")
                logger.info(f"  识别项目数: {len(analysis_result.get('projects', []))}")
                for project in analysis_result.get('projects', [])[:3]:
                    logger.info(f"    - {project.get('name')} ({project.get('symbol')}) - 分类: {project.get('category')}")
            else:
                logger.warning("ChatGPT项目分析失败或未识别出项目")
        
        # 4. 运行完整项目分析
        logger.info("\n4. 运行完整项目分析...")
        success = project_engine.analyze_recent_tweets(hours=6, max_tweets=30)
        
        if success:
            logger.info("项目分析执行成功")
        else:
            logger.error("项目分析执行失败")
            return False
        
        # 5. 检查生成的项目
        logger.info("\n5. 检查识别的项目...")
        project_count = project_dao.get_project_count()
        logger.info(f"数据库中项目总数: {project_count}")
        
        if project_count > 0:
            # 显示一些项目样例
            hot_projects = project_dao.get_hot_projects(limit=3)
            logger.info("\n热门项目样例:")
            for i, project in enumerate(hot_projects, 1):
                logger.info(f"  项目 {i}: {project.name} ({project.symbol})")
                logger.info(f"    分类: {project.category}")
                logger.info(f"    叙事: {', '.join(project.narratives or [])}")
                logger.info(f"    热度: {project.popularity}")
                logger.info(f"    情感: {project.sentiment_index}")
                if project.summary:
                    logger.info(f"    总结: {project.summary[:100]}...")
        
        # 6. 显示统计信息
        logger.info("\n6. 项目分析统计信息:")
        stats = project_engine.get_project_statistics()
        for key, value in stats.items():
            if key not in ['category_distribution', 'sentiment_distribution', 'hot_projects']:
                logger.info(f"  {key}: {value}")
        
        # 显示分类分布
        category_dist = stats.get('category_distribution', {})
        if any(count > 0 for count in category_dist.values()):
            logger.info("\n  分类分布:")
            for category, count in category_dist.items():
                if count > 0:
                    logger.info(f"    {category}: {count}")
        
        return True
        
    except Exception as e:
        logger.error(f"项目分析测试失败: {e}")
        return False


def main():
    """主函数"""
    logger = get_logger(__name__)
    
    logger.info("项目分析测试工具")
    logger.info("=" * 40)
    
    # 运行项目分析测试
    if test_project_analysis():
        logger.info("项目分析测试成功")
    else:
        logger.error("项目分析测试失败")
        sys.exit(1)


if __name__ == '__main__':
    main() 