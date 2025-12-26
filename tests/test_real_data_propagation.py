#!/usr/bin/env python3
"""
测试真实数据库环境中的propagation_speed修正
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

def test_real_database():
    """测试真实数据库环境"""
    print("=== 测试真实数据库环境 ===")
    
    # 测试数据库连接
    try:
        # 获取一个话题的推文数据
        sql = """
        SELECT t.topic_id, t.topic_name, COUNT(*) as tweet_count
        FROM topics t
        INNER JOIN twitter_tweet tt ON t.topic_id = tt.topic_id
        WHERE t.topic_name IS NOT NULL
        GROUP BY t.topic_id, t.topic_name
        HAVING COUNT(*) >= 3
        ORDER BY tweet_count DESC
        LIMIT 5
        """
        
        topics_result = topic_dao.db_manager.execute_query(sql)
        
        if not topics_result:
            print("❌ 没有找到合适的话题数据")
            return
        
        print(f"找到 {len(topics_result)} 个话题用于测试")
        
        analyzer = TopicAnalyzer()
        
        for topic_row in topics_result:
            topic_id = topic_row['topic_id']
            topic_name = topic_row['topic_name']
            tweet_count = topic_row['tweet_count']
            
            print(f"\n--- 测试话题: {topic_name[:50]}... (推文数: {tweet_count}) ---")
            
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
                print("  ❌ 没有找到推文数据")
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
            
            # 打印前3条推文的信息
            for i, tweet in enumerate(tweets[:3]):
                print(f"    推文{i+1}: 时间={tweet.created_at_datetime}, 互动={tweet.favorite_count}+{tweet.retweet_count}+{tweet.reply_count}")
            
            # 计算传播速度
            speeds = analyzer.calculate_propagation_speeds(tweets)
            
            print(f"  📊 传播速度结果:")
            print(f"    5分钟: {speeds['5m']}")
            print(f"    1小时: {speeds['1h']}")
            print(f"    4小时: {speeds['4h']}")
            
            # 验证结果
            if any(speed > 0 for speed in speeds.values()):
                print("  ✅ 成功计算出非零传播速度")
            else:
                print("  ⚠️  所有传播速度仍为0")
            
            # 更新数据库中的传播速度
            try:
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
                print("  ✅ 已更新数据库中的传播速度")
                
            except Exception as e:
                print(f"  ❌ 更新数据库失败: {e}")
                
    except Exception as e:
        print(f"❌ 数据库测试失败: {e}")
        import traceback
        traceback.print_exc()

def check_updated_results():
    """检查更新后的结果"""
    print("\n=== 检查更新后的结果 ===")
    
    try:
        sql = """
        SELECT topic_name, propagation_speed_5m, propagation_speed_1h, propagation_speed_4h, update_time
        FROM topics 
        WHERE propagation_speed_5m > 0 OR propagation_speed_1h > 0 OR propagation_speed_4h > 0
        ORDER BY update_time DESC
        LIMIT 10
        """
        
        results = topic_dao.db_manager.execute_query(sql)
        
        if results:
            print(f"找到 {len(results)} 个话题有非零传播速度:")
            for row in results:
                print(f"  话题: {row['topic_name'][:40]}...")
                print(f"    5m: {row['propagation_speed_5m']}, 1h: {row['propagation_speed_1h']}, 4h: {row['propagation_speed_4h']}")
                print(f"    更新时间: {row['update_time']}")
                print("  ---")
        else:
            print("❌ 仍然没有找到非零传播速度的话题")
            
    except Exception as e:
        print(f"❌ 检查结果失败: {e}")

if __name__ == '__main__':
    try:
        # 测试真实数据库
        test_real_database()
        
        # 检查更新结果
        check_updated_results()
        
        print("\n=== 真实环境测试完成 ===")
        
    except Exception as e:
        print(f"测试失败: {e}")
        import traceback
        traceback.print_exc()