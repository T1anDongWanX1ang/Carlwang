#!/usr/bin/env python3
"""
使用真实KOL推文测试话题分析
"""
import sys
import os
from datetime import datetime

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.database.tweet_dao import tweet_dao
from src.utils.topic_analyzer import topic_analyzer
from src.models.tweet import Tweet
from src.utils.logger import setup_logger


def test_with_real_kol_tweets():
    """使用真实的KOL推文测试话题分析"""
    setup_logger()
    
    print("🔍 使用真实KOL推文测试话题分析")
    print("=" * 60)
    
    try:
        # 获取真实的KOL推文
        db_manager = tweet_dao.db_manager
        
        sql = """
        SELECT id_str, full_text, created_at, kol_id, 
               favorite_count, retweet_count, reply_count, view_count
        FROM twitter_tweet 
        WHERE kol_id IS NOT NULL AND kol_id != '' 
        ORDER BY created_at DESC 
        LIMIT 5
        """
        
        kol_tweet_data = db_manager.execute_query(sql)
        
        if not kol_tweet_data:
            print("❌ 没有找到KOL推文")
            return False
        
        print(f"📊 找到 {len(kol_tweet_data)} 条KOL推文")
        
        # 转换为Tweet对象
        tweets = []
        for row in kol_tweet_data:
            tweet = Tweet(
                id_str=row['id_str'],
                full_text=row['full_text'],
                kol_id=row['kol_id'],
                created_at=row['created_at'],
                created_at_datetime=datetime.now(),
                favorite_count=row.get('favorite_count', 0),
                retweet_count=row.get('retweet_count', 0),
                reply_count=row.get('reply_count', 0),
                view_count=row.get('view_count', 0)
            )
            tweets.append(tweet)
        
        # 显示推文信息
        print("\n📋 KOL推文详情:")
        for i, tweet in enumerate(tweets, 1):
            print(f"   {i}. KOL:{tweet.kol_id}")
            print(f"      内容: {tweet.full_text[:100]}...")
            print()
        
        # 测试单个话题的summary生成
        print("🧪 测试单个话题的summary生成...")
        
        # 构造话题数据
        topic_data = {
            'topic_name': 'Real KOL Tweet Analysis Test',
            'brief': 'Testing with real KOL tweets from database',
            'category': 'cryptocurrency',
            'key_entities': ['crypto', 'KOL'],
            'created_at': datetime.now()
        }
        
        # 调用增强版的summary生成方法
        summary = topic_analyzer._generate_enhanced_topic_summary(topic_data, tweets)
        
        print(f"📄 Summary生成结果:")
        if summary:
            print(f"   ✅ 成功生成 (长度: {len(summary)})")
            print(f"   内容预览: {summary[:200]}...")
        else:
            print("   ❌ 生成失败，返回None")
            
        # 测试完整的话题提取流程
        print(f"\n🔧 测试完整话题提取流程...")
        topics = topic_analyzer.extract_topics_from_tweets(tweets)
        
        print(f"📊 话题提取结果: {len(topics)} 个话题")
        
        if topics:
            for i, topic in enumerate(topics, 1):
                print(f"   话题 {i}: {topic.topic_name}")
                print(f"     Summary状态: {'有内容' if topic.summary else 'None'}")
                if topic.summary:
                    print(f"     Summary预览: {topic.summary[:150]}...")
                print()
        
        return len(topics) > 0 and any(t.summary for t in topics)
        
    except Exception as e:
        print(f"❌ 测试异常: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == '__main__':
    success = test_with_real_kol_tweets()
    print(f"\n🎯 测试结果: {'✅ 成功' if success else '❌ 失败'}")
