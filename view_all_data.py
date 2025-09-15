#!/usr/bin/env python3
"""
综合数据查看工具
"""
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.database.tweet_dao import tweet_dao
from src.database.user_dao import user_dao
from src.database.topic_dao import topic_dao
from src.database.kol_dao import kol_dao
from src.database.project_dao import project_dao
from src.utils.logger import get_logger


def show_data_overview():
    """显示数据概览"""
    logger = get_logger(__name__)
    
    logger.info("=== 数据库概览 ===")
    
    # 统计信息
    tweet_count = tweet_dao.get_tweet_count()
    user_count = user_dao.get_user_count()
    topic_count = topic_dao.get_topic_count()
    kol_count = kol_dao.get_kol_count()
    project_count = project_dao.get_project_count()
    
    logger.info(f"推文总数: {tweet_count}")
    logger.info(f"用户总数: {user_count}")
    logger.info(f"话题总数: {topic_count}")
    logger.info(f"KOL总数: {kol_count}")
    logger.info(f"项目总数: {project_count}")
    
    print()
    
    # 显示热门推文
    logger.info("=== 热门推文 (按互动总量) ===")
    try:
        popular_tweets = tweet_dao.db_manager.execute_query("""
            SELECT id_str, full_text, engagement_total, view_count, created_at 
            FROM twitter_tweet 
            WHERE engagement_total > 0 
            ORDER BY engagement_total DESC 
            LIMIT 3
        """)
        
        for i, tweet in enumerate(popular_tweets, 1):
            logger.info(f"{i}. 推文ID: {tweet['id_str']}")
            logger.info(f"   互动总量: {tweet['engagement_total']}")
            logger.info(f"   浏览数: {tweet['view_count']}")
            logger.info(f"   内容: {tweet['full_text'][:100]}...")
            logger.info(f"   时间: {tweet['created_at']}")
            print()
            
    except Exception as e:
        logger.error(f"查询热门推文失败: {e}")
    
    # 显示热门用户
    logger.info("=== 热门用户 (按粉丝数) ===")
    try:
        popular_users = user_dao.get_top_users_by_followers(limit=3)
        
        for i, user in enumerate(popular_users, 1):
            logger.info(f"{i}. 用户: @{user.screen_name}")
            logger.info(f"   姓名: {user.name}")
            logger.info(f"   粉丝数: {user.followers_count:,}")
            logger.info(f"   关注数: {user.friends_count:,}")
            logger.info(f"   推文数: {user.statuses_count:,}")
            if user.description:
                logger.info(f"   简介: {user.description[:80]}...")
            print()
            
    except Exception as e:
        logger.error(f"查询热门用户失败: {e}")
    
    # 显示热门话题
    logger.info("=== 热门话题 ===")
    try:
        hot_topics = topic_dao.get_hot_topics(limit=5)
        
        for i, topic in enumerate(hot_topics, 1):
            logger.info(f"{i}. 话题: {topic.topic_name}")
            logger.info(f"   简介: {topic.brief}")
            logger.info(f"   热度: {topic.popularity}")
            logger.info(f"   情感方向: {topic.mob_opinion_direction}")
            logger.info(f"   传播速度(5m/1h/4h): {topic.propagation_speed_5m}/{topic.propagation_speed_1h}/{topic.propagation_speed_4h}")
            if topic.summary:
                logger.info(f"   AI总结: {topic.summary[:100]}...")
            logger.info(f"   创建时间: {topic.created_at}")
            print()
            
    except Exception as e:
        logger.error(f"查询热门话题失败: {e}")
    
    # 显示情感分布
    logger.info("=== 话题情感分布 ===")
    try:
        sentiment_stats = topic_dao.db_manager.execute_query("""
            SELECT mob_opinion_direction, COUNT(*) as count 
            FROM topics 
            WHERE mob_opinion_direction IS NOT NULL 
            GROUP BY mob_opinion_direction
        """)
        
        for stat in sentiment_stats:
            logger.info(f"{stat['mob_opinion_direction']}: {stat['count']} 个话题")
            
    except Exception as e:
        logger.error(f"查询情感分布失败: {e}")
    
    # 显示顶级KOL
    logger.info("=== 顶级KOL (按影响力排序) ===")
    try:
        top_kols = kol_dao.get_top_kols_by_influence(limit=3)
        
        for i, kol in enumerate(top_kols, 1):
            user = user_dao.get_user_by_id(kol.kol_id)
            screen_name = user.screen_name if user else "unknown"
            followers = user.followers_count if user else 0
            
            logger.info(f"{i}. KOL: @{screen_name}")
            logger.info(f"   类型: {kol.type}")
            logger.info(f"   标签: {kol.tag}")
            logger.info(f"   影响力评分: {kol.influence_score}")
            logger.info(f"   情感倾向: {kol.sentiment}")
            logger.info(f"   信任度: {kol.trust_rating}")
            logger.info(f"   粉丝数: {followers:,}")
            logger.info(f"   KOL100: {'是' if kol.is_kol100 else '否'}")
            if kol.summary:
                logger.info(f"   AI总结: {kol.summary[:80]}...")
            print()
            
    except Exception as e:
        logger.error(f"查询顶级KOL失败: {e}")
    
    # 显示KOL类型分布
    logger.info("=== KOL类型分布 ===")
    try:
        type_stats = kol_dao.db_manager.execute_query("""
            SELECT type, COUNT(*) as count 
            FROM kols 
            WHERE type IS NOT NULL 
            GROUP BY type
        """)
        
        for stat in type_stats:
            logger.info(f"{stat['type']}: {stat['count']} 个KOL")
            
    except Exception as e:
        logger.error(f"查询KOL类型分布失败: {e}")
    
    # 显示KOL情感分布
    logger.info("=== KOL情感分布 ===")
    try:
        kol_sentiment_stats = kol_dao.db_manager.execute_query("""
            SELECT sentiment, COUNT(*) as count 
            FROM kols 
            WHERE sentiment IS NOT NULL 
            GROUP BY sentiment
        """)
        
        for stat in kol_sentiment_stats:
            logger.info(f"{stat['sentiment']}: {stat['count']} 个KOL")
            
    except Exception as e:
        logger.error(f"查询KOL情感分布失败: {e}")
    
    # 显示热门项目
    logger.info("=== 热门项目 (按热度排序) ===")
    try:
        hot_projects = project_dao.get_hot_projects(limit=5)
        
        for i, project in enumerate(hot_projects, 1):
            logger.info(f"{i}. 项目: {project.name} ({project.symbol})")
            logger.info(f"   分类: {project.category}")
            logger.info(f"   叙事: {', '.join(project.narratives or [])}")
            logger.info(f"   热度: {project.popularity}")
            logger.info(f"   情感指数: {project.sentiment_index}")
            logger.info(f"   情感趋势: {project.get_sentiment_trend()}")
            if project.summary:
                logger.info(f"   AI总结: {project.summary[:80]}...")
            print()
            
    except Exception as e:
        logger.error(f"查询热门项目失败: {e}")
    
    # 显示项目分类分布
    logger.info("=== 项目分类分布 ===")
    try:
        category_stats = project_dao.db_manager.execute_query("""
            SELECT category, COUNT(*) as count 
            FROM twitter_projects 
            WHERE category IS NOT NULL 
            GROUP BY category
        """)
        
        for stat in category_stats:
            logger.info(f"{stat['category']}: {stat['count']} 个项目")
            
    except Exception as e:
        logger.error(f"查询项目分类分布失败: {e}")
    
    # 显示热门项目
    logger.info("=== 热门项目 (按热度排序) ===")
    try:
        hot_projects = project_dao.get_hot_projects(limit=5)
        
        for i, project in enumerate(hot_projects, 1):
            logger.info(f"{i}. 项目: {project.name} ({project.symbol})")
            logger.info(f"   分类: {project.category}")
            logger.info(f"   叙事: {', '.join(project.narratives or [])}")
            logger.info(f"   热度: {project.popularity}")
            logger.info(f"   情感指数: {project.sentiment_index}")
            logger.info(f"   情感趋势: {project.get_sentiment_trend()}")
            if project.summary:
                logger.info(f"   AI总结: {project.summary[:80]}...")
            print()
            
    except Exception as e:
        logger.error(f"查询热门项目失败: {e}")
    
    # 显示项目分类分布
    logger.info("=== 项目分类分布 ===")
    try:
        category_stats = project_dao.db_manager.execute_query("""
            SELECT category, COUNT(*) as count 
            FROM twitter_projects 
            WHERE category IS NOT NULL 
            GROUP BY category
        """)
        
        for stat in category_stats:
            logger.info(f"{stat['category']}: {stat['count']} 个项目")
            
    except Exception as e:
        logger.error(f"查询项目分类分布失败: {e}")


def main():
    """主函数"""
    logger = get_logger(__name__)
    
    logger.info("Twitter数据综合查看工具")
    logger.info("=" * 60)
    
    show_data_overview()
    
    logger.info("数据查看完成")


if __name__ == '__main__':
    main() 