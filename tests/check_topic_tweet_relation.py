#!/usr/bin/env python3
"""
检查topics和tweets表的关联关系
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
        
        # 1. 检查tweets表中topic_id字段的情况
        print("1️⃣ 检查tweets表topic_id字段")
        print("-" * 40)
        
        topic_id_stats_sql = """
        SELECT 
            COUNT(*) as total_tweets,
            COUNT(topic_id) as tweets_with_topic_id,
            COUNT(CASE WHEN topic_id IS NOT NULL AND topic_id != '' THEN 1 END) as tweets_with_valid_topic_id
        FROM twitter_tweet
        """
        
        stats = db_manager.execute_query(topic_id_stats_sql)[0]
        print(f"📊 推文总数: {stats['total_tweets']}")
        print(f"📊 有topic_id的推文: {stats['tweets_with_topic_id']}")
        print(f"📊 有效topic_id的推文: {stats['tweets_with_valid_topic_id']}")
        print(f"📊 topic_id覆盖率: {stats['tweets_with_valid_topic_id']/stats['total_tweets']*100:.1f}%")
        
        # 2. 检查tweets表中有topic_id的推文样本
        print(f"\n2️⃣ 有topic_id的推文样本")
        print("-" * 40)
        
        tweet_samples_sql = """
        SELECT id_str, topic_id, kol_id, full_text, created_at
        FROM twitter_tweet 
        WHERE topic_id IS NOT NULL AND topic_id != ''
        ORDER BY created_at DESC 
        LIMIT 10
        """
        
        tweet_samples = db_manager.execute_query(tweet_samples_sql)
        
        if tweet_samples:
            print(f"✅ 找到 {len(tweet_samples)} 条有topic_id的推文:")
            for tweet in tweet_samples:
                kol_status = f"KOL:{tweet['kol_id']}" if tweet['kol_id'] else "非KOL"
                print(f"   • 推文ID: {tweet['id_str']}")
                print(f"     Topic ID: {tweet['topic_id']}")  
                print(f"     KOL状态: {kol_status}")
                print(f"     内容: {tweet['full_text'][:60]}...")
                print()
        else:
            print("❌ 没有找到有topic_id的推文")
        
        # 3. 检查topics表中哪些话题有对应的推文
        print(f"3️⃣ 检查topics表话题的推文关联")
        print("-" * 40)
        
        topic_with_tweets_sql = """
        SELECT 
            t.topic_id,
            t.topic_name,
            COUNT(tw.id_str) as tweet_count,
            COUNT(CASE WHEN tw.kol_id IS NOT NULL AND tw.kol_id != '' THEN 1 END) as kol_tweet_count
        FROM topics t
        LEFT JOIN twitter_tweet tw ON t.topic_id = tw.topic_id
        WHERE t.created_at >= DATE_SUB(NOW(), INTERVAL 24 HOUR)
        GROUP BY t.topic_id, t.topic_name
        ORDER BY t.created_at DESC
        LIMIT 10
        """
        
        topic_relations = db_manager.execute_query(topic_with_tweets_sql)
        
        if topic_relations:
            print(f"📋 最近24小时话题的推文关联情况:")
            topics_with_tweets = 0
            topics_with_kol_tweets = 0
            
            for topic in topic_relations:
                tweet_count = topic['tweet_count']
                kol_count = topic['kol_tweet_count']
                
                if tweet_count > 0:
                    topics_with_tweets += 1
                if kol_count > 0:
                    topics_with_kol_tweets += 1
                
                print(f"   • {topic['topic_name'][:40]}...")
                print(f"     Topic ID: {topic['topic_id']}")
                print(f"     关联推文: {tweet_count} 条 (KOL: {kol_count} 条)")
                print()
            
            total_topics = len(topic_relations)
            print(f"📊 统计:")
            print(f"   有关联推文的话题: {topics_with_tweets}/{total_topics} ({topics_with_tweets/total_topics*100:.1f}%)")
            print(f"   有KOL推文的话题: {topics_with_kol_tweets}/{total_topics} ({topics_with_kol_tweets/total_topics*100:.1f}%)")
        else:
            print("❌ 没有找到最近的话题")
        
        # 4. 检查具体某个话题的推文
        print(f"\n4️⃣ 检查具体话题的推文详情")
        print("-" * 40)
        
        if topic_relations:
            # 选择第一个话题进行详细检查
            sample_topic = topic_relations[0]
            topic_id = sample_topic['topic_id']
            
            topic_tweets_sql = """
            SELECT id_str, kol_id, full_text, created_at
            FROM twitter_tweet
            WHERE topic_id = %s
            ORDER BY created_at DESC
            """
            
            topic_tweets = db_manager.execute_query(topic_tweets_sql, [topic_id])
            
            print(f"🔍 话题 '{sample_topic['topic_name']}' 的推文详情:")
            if topic_tweets:
                for i, tweet in enumerate(topic_tweets[:5], 1):
                    kol_status = f"KOL:{tweet['kol_id']}" if tweet['kol_id'] else "非KOL"
                    print(f"   {i}. 推文ID: {tweet['id_str']} [{kol_status}]")
                    print(f"      内容: {tweet['full_text'][:80]}...")
                    print()
            else:
                print(f"   ❌ 该话题没有关联的推文")
        
        # 5. 总结问题
        print(f"5️⃣ 问题分析")
        print("-" * 40)
        
        if stats['tweets_with_valid_topic_id'] == 0:
            print("❌ 严重问题: tweets表中没有有效的topic_id，关联关系完全缺失")
        elif stats['tweets_with_valid_topic_id'] < stats['total_tweets'] * 0.5:
            print("⚠️ 问题: 大部分推文没有topic_id，关联关系不完整")
        else:
            print("✅ tweets表topic_id字段基本正常")
            
        if topic_relations and topics_with_tweets == 0:
            print("❌ 问题: topics表中的话题都没有关联推文")
        elif topic_relations and topics_with_kol_tweets == 0:
            print("⚠️ 问题: 话题有关联推文，但都不是KOL推文")
        elif topic_relations:
            print("✅ 部分话题有KOL推文关联")
        
    except Exception as e:
        print(f"❌ 检查异常: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    check_topic_tweet_relation()