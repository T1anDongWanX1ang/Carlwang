#!/usr/bin/env python3
"""
为最近创建的话题更新传播速度
"""
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.database.topic_dao import topic_dao
from src.database.tweet_dao import tweet_dao
from src.utils.topic_analyzer import TopicAnalyzer
from src.models.tweet import Tweet

def update_recent_topics_speed():
    """为最近创建但没有传播速度的话题更新速度"""
    print("=== 更新最近话题的传播速度 ===")
    
    # 获取最近2小时创建但没有传播速度的话题
    sql = """
    SELECT t.topic_id, t.topic_name, COUNT(tt.id_str) as tweet_count
    FROM topics t
    INNER JOIN twitter_tweet tt ON t.topic_id = tt.topic_id
    WHERE t.topic_name IS NOT NULL
    AND t.created_at >= DATE_SUB(NOW(), INTERVAL 2 HOUR)
    AND (t.propagation_speed_5m IS NULL OR t.propagation_speed_5m = 0)
    AND tt.created_at_datetime IS NOT NULL
    GROUP BY t.topic_id, t.topic_name, t.created_at
    HAVING COUNT(tt.id_str) >= 1
    ORDER BY t.created_at DESC
    """
    
    topics_result = topic_dao.db_manager.execute_query(sql)
    
    if not topics_result:
        print("没有找到需要更新的话题")
        return
    
    print(f"找到 {len(topics_result)} 个需要更新传播速度的话题")
    
    analyzer = TopicAnalyzer()
    updated_count = 0
    
    for topic_row in topics_result:
        topic_id = topic_row['topic_id']
        topic_name = topic_row['topic_name']
        tweet_count = topic_row['tweet_count']
        
        print(f"\n处理话题: {topic_name[:50]}... (推文数: {tweet_count})")
        
        try:
            # 获取该话题的推文数据
            tweets_sql = """
            SELECT id_str, created_at_datetime, favorite_count, retweet_count, reply_count, full_text
            FROM twitter_tweet
            WHERE topic_id = %s
            AND created_at_datetime IS NOT NULL
            ORDER BY created_at_datetime DESC
            LIMIT 20
            """
            
            tweets_result = tweet_dao.db_manager.execute_query(tweets_sql, [topic_id])
            
            if not tweets_result:
                print(f"  ❌ 没有找到推文数据")
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
            
            print(f"  获取到 {len(tweets)} 条推文")
            
            # 计算传播速度
            speeds = analyzer.calculate_propagation_speeds(tweets)
            
            print(f"  📊 传播速度: 5m={speeds['5m']}, 1h={speeds['1h']}, 4h={speeds['4h']}")
            
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
            print(f"  ✅ 更新成功")
            
        except Exception as e:
            print(f"  ❌ 处理失败: {e}")
            continue
    
    print(f"\n=== 更新完成 ===")
    print(f"成功更新 {updated_count} 个话题的传播速度")
    
    # 验证结果
    if updated_count > 0:
        verify_sql = """
        SELECT topic_name, propagation_speed_5m, propagation_speed_1h, propagation_speed_4h, update_time
        FROM topics 
        WHERE update_time >= DATE_SUB(NOW(), INTERVAL 5 MINUTE)
        AND (propagation_speed_5m > 0 OR propagation_speed_1h > 0 OR propagation_speed_4h > 0)
        ORDER BY update_time DESC
        LIMIT 5
        """
        
        verify_result = topic_dao.db_manager.execute_query(verify_sql)
        if verify_result:
            print("\n=== 验证结果 ===")
            for row in verify_result:
                print(f"✅ {row['topic_name'][:40]}...")
                print(f"   5m: {row['propagation_speed_5m']}, 1h: {row['propagation_speed_1h']}, 4h: {row['propagation_speed_4h']}")
                print(f"   更新时间: {row['update_time']}")

if __name__ == '__main__':
    update_recent_topics_speed()