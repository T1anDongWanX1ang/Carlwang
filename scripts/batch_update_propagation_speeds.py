#!/usr/bin/env python3
"""
批量更新所有话题的propagation_speed
"""
import sys
from pathlib import Path
from datetime import datetime

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.database.topic_dao import topic_dao
from src.database.tweet_dao import tweet_dao
from src.utils.topic_analyzer import TopicAnalyzer
from src.models.tweet import Tweet
from src.utils.logger import get_logger

def batch_update_propagation_speeds():
    """批量更新所有话题的传播速度"""
    logger = get_logger(__name__)
    logger.info("开始批量更新propagation_speed...")
    
    try:
        # 获取所有有推文的话题
        sql = """
        SELECT t.topic_id, t.topic_name, COUNT(*) as tweet_count
        FROM topics t
        INNER JOIN twitter_tweet tt ON t.topic_id = tt.topic_id
        WHERE t.topic_name IS NOT NULL
        AND tt.created_at_datetime IS NOT NULL
        GROUP BY t.topic_id, t.topic_name
        HAVING COUNT(*) >= 1
        ORDER BY tweet_count DESC
        """
        
        topics_result = topic_dao.db_manager.execute_query(sql)
        
        if not topics_result:
            logger.warning("没有找到合适的话题数据")
            return
        
        logger.info(f"找到 {len(topics_result)} 个话题需要更新")
        
        analyzer = TopicAnalyzer()
        updated_count = 0
        error_count = 0
        
        for i, topic_row in enumerate(topics_result, 1):
            topic_id = topic_row['topic_id']
            topic_name = topic_row['topic_name']
            tweet_count = topic_row['tweet_count']
            
            logger.info(f"[{i}/{len(topics_result)}] 处理话题: {topic_name[:50]}... (推文数: {tweet_count})")
            
            try:
                # 获取该话题的推文数据
                tweets_sql = """
                SELECT id_str, created_at_datetime, favorite_count, retweet_count, reply_count, full_text
                FROM twitter_tweet
                WHERE topic_id = %s
                AND created_at_datetime IS NOT NULL
                ORDER BY created_at_datetime DESC
                LIMIT 50
                """
                
                tweets_result = tweet_dao.db_manager.execute_query(tweets_sql, [topic_id])
                
                if not tweets_result:
                    logger.warning(f"  话题 {topic_name} 没有找到推文数据")
                    continue
                
                # 转换为Tweet对象
                tweets = []
                for tweet_row in tweets_result:
                    tweet = Tweet(
                        id_str=tweet_row['id_str'],
                        created_at_datetime=tweet_row['created_at_datetime'],
                        favorite_count=tweet_row['favorite_count'] or 0,
                        retweet_count=tweet_row['retweet_count'] or 0,
                        reply_count=tweet_row['reply_count'] or 0,
                        full_text=tweet_row['full_text']
                    )
                    tweets.append(tweet)
                
                # 计算传播速度
                speeds = analyzer.calculate_propagation_speeds(tweets)
                
                logger.debug(f"  传播速度: 5m={speeds['5m']}, 1h={speeds['1h']}, 4h={speeds['4h']}")
                
                # 更新数据库
                update_sql = """
                UPDATE topics 
                SET propagation_speed_5m = %s,
                    propagation_speed_1h = %s,
                    propagation_speed_4h = %s,
                    update_time = NOW()
                WHERE topic_id = %s
                """
                
                topic_dao.db_manager.execute_update(
                    update_sql, 
                    [speeds['5m'], speeds['1h'], speeds['4h'], topic_id]
                )
                
                updated_count += 1
                logger.info(f"  ✅ 更新成功")
                
                # 每处理10个话题显示一次进度
                if i % 10 == 0:
                    logger.info(f"进度: {i}/{len(topics_result)} ({updated_count}个成功, {error_count}个失败)")
                
            except Exception as e:
                error_count += 1
                logger.error(f"  ❌ 处理话题 {topic_name} 失败: {e}")
                continue
        
        logger.info(f"批量更新完成！成功: {updated_count}, 失败: {error_count}")
        
        # 验证更新结果
        verify_update_results(logger)
        
    except Exception as e:
        logger.error(f"批量更新失败: {e}")
        import traceback
        traceback.print_exc()

def verify_update_results(logger):
    """验证更新结果"""
    logger.info("验证更新结果...")
    
    try:
        # 统计非零propagation_speed的话题数量
        stats_sql = """
        SELECT 
            COUNT(*) as total_topics,
            COUNT(CASE WHEN propagation_speed_5m > 0 THEN 1 END) as has_5m,
            COUNT(CASE WHEN propagation_speed_1h > 0 THEN 1 END) as has_1h,
            COUNT(CASE WHEN propagation_speed_4h > 0 THEN 1 END) as has_4h,
            COUNT(CASE WHEN propagation_speed_5m > 0 OR propagation_speed_1h > 0 OR propagation_speed_4h > 0 THEN 1 END) as has_any_speed
        FROM topics
        WHERE topic_name IS NOT NULL
        """
        
        stats_result = topic_dao.db_manager.execute_query(stats_sql)
        
        if stats_result:
            stats = stats_result[0]
            logger.info(f"验证结果:")
            logger.info(f"  总话题数: {stats['total_topics']}")
            logger.info(f"  有5分钟速度: {stats['has_5m']}")
            logger.info(f"  有1小时速度: {stats['has_1h']}")
            logger.info(f"  有4小时速度: {stats['has_4h']}")
            logger.info(f"  有任意速度: {stats['has_any_speed']}")
            
            success_rate = (stats['has_any_speed'] / stats['total_topics']) * 100 if stats['total_topics'] > 0 else 0
            logger.info(f"  成功率: {success_rate:.1f}%")
        
        # 显示前10个更新的话题
        sample_sql = """
        SELECT topic_name, propagation_speed_5m, propagation_speed_1h, propagation_speed_4h, update_time
        FROM topics 
        WHERE propagation_speed_5m > 0 OR propagation_speed_1h > 0 OR propagation_speed_4h > 0
        ORDER BY update_time DESC
        LIMIT 10
        """
        
        sample_result = topic_dao.db_manager.execute_query(sample_sql)
        
        if sample_result:
            logger.info("最近更新的话题样本:")
            for row in sample_result:
                logger.info(f"  {row['topic_name'][:40]}... -> 5m:{row['propagation_speed_5m']}, 1h:{row['propagation_speed_1h']}, 4h:{row['propagation_speed_4h']}")
        
    except Exception as e:
        logger.error(f"验证结果失败: {e}")

if __name__ == '__main__':
    batch_update_propagation_speeds()