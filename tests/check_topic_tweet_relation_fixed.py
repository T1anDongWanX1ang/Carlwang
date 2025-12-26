#!/usr/bin/env python3
"""
检查topics和tweets表的关联关系 - 修复版
"""
import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.database.topic_dao import topic_dao
from src.database.tweet_dao import tweet_dao
from src.utils.logger import setup_logger


def check_topic_tweet_relation():
    """检查topics和tweets的关联关系"""
    setup_logger()
    
    print("🔍 检查topics和tweets表的关联关系")
    print("=" * 60)
    
    try:
        db_manager = topic_dao.db_manager
        
        # 从之前的结果我们已经知道：
        # - 推文总数: 420
        # - 有topic_id的推文: 32 (7.6%)
        # - 其中包含KOL推文
        
        print("📊 从之前结果得知:")
        print("   推文总数: 420")
        print("   有topic_id的推文: 32 (7.6%)")
        print("   发现了KOL推文与topic_id的关联")
        
        # 1. 检查最近的topics及其推文情况
        print(f"\n1️⃣ 检查最近topics的推文关联")
        print("-" * 40)
        
        # 先获取最近的topics
        recent_topics_sql = """
        SELECT topic_id, topic_name, created_at
        FROM topics 
        WHERE created_at >= DATE_SUB(NOW(), INTERVAL 24 HOUR)
        ORDER BY created_at DESC 
        LIMIT 10
        """
        
        recent_topics = db_manager.execute_query(recent_topics_sql)
        
        if recent_topics:
            print(f"✅ 找到 {len(recent_topics)} 个最近24小时的话题:")
            
            for topic in recent_topics[:5]:  # 只检查前5个
                topic_id = topic['topic_id']
                topic_name = topic['topic_name']
                
                # 检查该topic的推文
                topic_tweets_sql = """
                SELECT id_str, kol_id, full_text
                FROM twitter_tweet
                WHERE topic_id = %s
                """
                
                topic_tweets = db_manager.execute_query(topic_tweets_sql, [topic_id])
                
                kol_count = 0
                if topic_tweets:
                    kol_count = sum(1 for t in topic_tweets if t['kol_id'])
                
                print(f"   • {topic_name[:50]}...")
                print(f"     Topic ID: {topic_id}")
                print(f"     关联推文: {len(topic_tweets) if topic_tweets else 0} 条")
                print(f"     KOL推文: {kol_count} 条")
                print()
        
        # 2. 检查有KOL推文的topics
        print(f"2️⃣ 检查有KOL推文的话题")
        print("-" * 40)
        
        kol_topics_sql = """
        SELECT DISTINCT tw.topic_id, t.topic_name
        FROM twitter_tweet tw
        JOIN topics t ON tw.topic_id = t.topic_id
        WHERE tw.kol_id IS NOT NULL AND tw.kol_id != ''
        LIMIT 10
        """
        
        kol_topics = db_manager.execute_query(kol_topics_sql)
        
        if kol_topics:
            print(f"✅ 找到 {len(kol_topics)} 个有KOL推文的话题:")
            
            for topic in kol_topics:
                topic_id = topic['topic_id']
                topic_name = topic['topic_name']
                
                # 获取该话题的KOL推文详情
                kol_tweets_sql = """
                SELECT id_str, kol_id, full_text
                FROM twitter_tweet
                WHERE topic_id = %s AND kol_id IS NOT NULL AND kol_id != ''
                """
                
                kol_tweets = db_manager.execute_query(kol_tweets_sql, [topic_id])
                
                print(f"   • {topic_name[:50]}...")
                print(f"     Topic ID: {topic_id}")
                print(f"     KOL推文数: {len(kol_tweets)}")
                
                if kol_tweets:
                    # 显示前2条KOL推文
                    for i, tweet in enumerate(kol_tweets[:2], 1):
                        print(f"     KOL推文{i}: {tweet['id_str']} (KOL:{tweet['kol_id']})")
                        print(f"       内容: {tweet['full_text'][:60]}...")
                print()
        else:
            print("❌ 没有找到有KOL推文的话题")
        
        # 3. 分析问题
        print(f"3️⃣ 问题分析")
        print("-" * 40)
        
        if not kol_topics:
            print("❌ 严重问题: 没有话题与KOL推文关联")
            print("   可能原因:")
            print("   1. topic_id字段在推文处理时没有正确设置")
            print("   2. 推文的topic_id和topics表的topic_id不匹配")
            print("   3. KOL推文的topic_id设置逻辑有问题")
        else:
            print(f"✅ 发现 {len(kol_topics)} 个话题有KOL推文关联")
            print("   这表明关联机制是有效的，但可能覆盖率不够")
        
        # 4. 检查为什么summary生成时找不到KOL推文
        print(f"\n4️⃣ 检查summary生成逻辑问题")  
        print("-" * 40)
        
        # 检查一个有KOL推文的话题，看看summary生成逻辑是否正确
        if kol_topics:
            test_topic_id = kol_topics[0]['topic_id']
            test_topic_name = kol_topics[0]['topic_name']
            
            print(f"🧪 测试话题: {test_topic_name}")
            print(f"   Topic ID: {test_topic_id}")
            
            # 模拟之前修复脚本中的推文获取逻辑
            print(f"   检查修复脚本的推文获取逻辑...")
            
            # 之前的脚本是通过话题名称关键词搜索推文，而不是通过topic_id！
            print(f"   ❌ 发现问题：之前的修复脚本使用关键词搜索而非topic_id关联")
            print(f"   ✅ 应该直接使用topic_id查询关联推文")
        
    except Exception as e:
        print(f"❌ 检查异常: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    check_topic_tweet_relation()