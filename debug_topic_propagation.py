#!/usr/bin/env python3
"""
调试topic模式的propagation_speed计算问题
"""
import sys
import logging
from pathlib import Path
from datetime import datetime, timedelta

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.topic_engine import topic_engine
from src.database.topic_dao import topic_dao
from src.database.tweet_dao import tweet_dao
from src.utils.logger import get_logger

def debug_topic_propagation():
    """调试话题分析中的propagation_speed计算"""
    print("=== 调试Topic模式的Propagation Speed计算 ===")
    
    # 设置DEBUG级别日志
    logging.getLogger().setLevel(logging.DEBUG)
    
    # 获取最近推文数据用于分析
    end_time = datetime.now()
    start_time = end_time - timedelta(hours=24)
    
    recent_tweets = tweet_dao.get_tweets_by_date_range(
        start_date=start_time,
        end_date=end_time,
        limit=20  # 限制数量以便观察
    )
    
    print(f"获取到 {len(recent_tweets)} 条最近24小时的推文")
    
    if not recent_tweets:
        print("❌ 没有最近推文数据，无法进行调试")
        return
    
    # 显示推文信息
    print("\n=== 推文样本 ===")
    for i, tweet in enumerate(recent_tweets[:3]):
        print(f"推文{i+1}: {tweet.id_str}")
        print(f"  时间: {tweet.created_at_datetime}")
        print(f"  内容: {tweet.full_text[:50]}...")
        print(f"  互动: 点赞{tweet.favorite_count} 转发{tweet.retweet_count} 评论{tweet.reply_count}")
    
    # 记录话题分析前的数据库状态
    topics_before = topic_dao.get_topic_count()
    print(f"\n=== 分析前状态 ===")
    print(f"数据库中现有话题数: {topics_before}")
    
    # 执行话题分析
    print(f"\n=== 开始话题分析 ===")
    print("执行 topic_engine.analyze_recent_tweets...")
    
    success = topic_engine.analyze_recent_tweets(hours=24, max_tweets=20)
    
    print(f"话题分析结果: {'成功' if success else '失败'}")
    
    # 检查分析后的状态
    topics_after = topic_dao.get_topic_count()
    new_topics_count = topics_after - topics_before
    
    print(f"\n=== 分析后状态 ===")
    print(f"数据库中话题总数: {topics_after}")
    print(f"新增话题数: {new_topics_count}")
    
    if new_topics_count > 0:
        # 获取最新创建的话题
        latest_topics_sql = """
        SELECT topic_id, topic_name, propagation_speed_5m, propagation_speed_1h, propagation_speed_4h, 
               created_at, update_time
        FROM topics 
        WHERE created_at >= %s
        ORDER BY created_at DESC
        LIMIT 5
        """
        
        latest_topics = topic_dao.db_manager.execute_query(latest_topics_sql, [start_time])
        
        print(f"\n=== 最新创建的话题 ===")
        for topic in latest_topics:
            print(f"话题: {topic['topic_name']}")
            print(f"  ID: {topic['topic_id']}")
            print(f"  创建时间: {topic['created_at']}")
            print(f"  5分钟速度: {topic['propagation_speed_5m']}")
            print(f"  1小时速度: {topic['propagation_speed_1h']}")
            print(f"  4小时速度: {topic['propagation_speed_4h']}")
            
            # 检查该话题的推文数量
            tweet_count_sql = """
            SELECT COUNT(*) as count 
            FROM twitter_tweet 
            WHERE topic_id = %s
            """
            tweet_count_result = tweet_dao.db_manager.execute_query(tweet_count_sql, [topic['topic_id']])
            tweet_count = tweet_count_result[0]['count'] if tweet_count_result else 0
            print(f"  关联推文数: {tweet_count}")
            
            # 判断propagation_speed状态
            has_speed = any([
                topic['propagation_speed_5m'], 
                topic['propagation_speed_1h'], 
                topic['propagation_speed_4h']
            ])
            
            if has_speed:
                print(f"  ✅ 有传播速度数据")
            else:
                print(f"  ❌ 传播速度为空/0")
                
                # 如果有多条推文但速度为0，手动测试计算
                if tweet_count > 1:
                    print(f"  🔍 话题有{tweet_count}条推文但速度为0，手动测试计算...")
                    test_manual_calculation(topic['topic_id'])
            
            print("  ---")
    else:
        print("❌ 没有创建新话题，可能是:")
        print("  1. 推文内容不符合话题提取条件")
        print("  2. ChatGPT API调用失败")
        print("  3. 话题被聚类到现有话题中")

def test_manual_calculation(topic_id):
    """手动测试传播速度计算"""
    try:
        from src.utils.topic_analyzer import TopicAnalyzer
        from src.models.tweet import Tweet
        
        # 获取该话题的推文
        tweets_sql = """
        SELECT id_str, created_at_datetime, favorite_count, retweet_count, reply_count, full_text
        FROM twitter_tweet
        WHERE topic_id = %s
        AND created_at_datetime IS NOT NULL
        ORDER BY created_at_datetime DESC
        """
        
        tweets_result = tweet_dao.db_manager.execute_query(tweets_sql, [topic_id])
        
        if tweets_result:
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
            
            print(f"    获取到 {len(tweets)} 条推文进行手动计算")
            
            # 手动计算传播速度
            analyzer = TopicAnalyzer()
            speeds = analyzer.calculate_propagation_speeds(tweets)
            
            print(f"    手动计算结果: 5m={speeds['5m']}, 1h={speeds['1h']}, 4h={speeds['4h']}")
            
            # 如果手动计算有结果，更新数据库
            if any(speeds.values()):
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
                print(f"    ✅ 手动计算结果已更新到数据库")
            else:
                print(f"    ⚠️ 手动计算结果也为0（可能推文时间间隔过大或数据不足）")
                
    except Exception as e:
        print(f"    ❌ 手动计算失败: {e}")

if __name__ == '__main__':
    try:
        debug_topic_propagation()
    except Exception as e:
        print(f"调试过程异常: {e}")
        import traceback
        traceback.print_exc()