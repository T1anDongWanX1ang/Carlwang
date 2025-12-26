#!/usr/bin/env python3
"""
测试回退逻辑（无KOL推文时的summary生成）
"""
import sys
import os
from datetime import datetime

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.database.tweet_dao import tweet_dao
from src.utils.topic_analyzer import topic_analyzer
from src.models.tweet import Tweet
from src.utils.logger import setup_logger


def test_fallback_logic():
    """测试无KOL推文时的回退逻辑"""
    setup_logger()
    
    print("🔍 测试回退逻辑（无KOL推文）")
    print("=" * 60)
    
    try:
        # 获取没有KOL标识的推文
        db_manager = tweet_dao.db_manager
        
        sql = """
        SELECT id_str, full_text, created_at, 
               favorite_count, retweet_count, reply_count, view_count
        FROM twitter_tweet 
        WHERE (kol_id IS NULL OR kol_id = '') 
        ORDER BY created_at DESC 
        LIMIT 5
        """
        
        non_kol_tweet_data = db_manager.execute_query(sql)
        
        if not non_kol_tweet_data:
            print("❌ 没有找到非KOL推文")
            return False
        
        print(f"📊 找到 {len(non_kol_tweet_data)} 条非KOL推文")
        
        # 转换为Tweet对象
        tweets = []
        for row in non_kol_tweet_data:
            tweet = Tweet(
                id_str=row['id_str'],
                full_text=row['full_text'],
                # 明确不设置kol_id
                created_at=row['created_at'],
                created_at_datetime=datetime.now(),
                favorite_count=row.get('favorite_count', 0),
                retweet_count=row.get('retweet_count', 0),
                reply_count=row.get('reply_count', 0),
                view_count=row.get('view_count', 0)
            )
            tweets.append(tweet)
        
        # 显示推文信息
        print("\n📋 非KOL推文详情:")
        for i, tweet in enumerate(tweets, 1):
            kol_status = getattr(tweet, 'kol_id', 'None')
            print(f"   {i}. KOL状态: {kol_status}")
            print(f"      内容: {tweet.full_text[:100]}...")
            print()
        
        # 测试单个话题的回退summary生成
        print("🧪 测试回退逻辑的summary生成...")
        
        # 构造话题数据
        topic_data = {
            'topic_name': 'Fallback Logic Test',
            'brief': 'Testing fallback logic with non-KOL tweets',
            'category': 'cryptocurrency',
            'key_entities': ['crypto'],
            'created_at': datetime.now()
        }
        
        # 调用增强版的summary生成方法
        print("📊 调用_generate_enhanced_topic_summary...")
        summary = topic_analyzer._generate_enhanced_topic_summary(topic_data, tweets)
        
        print(f"📄 回退逻辑Summary生成结果:")
        if summary:
            print(f"   ✅ 成功生成 (长度: {len(summary)})")
            print(f"   内容预览: {summary[:200]}...")
            
            # 检查是否是JSON格式（KOL方法）还是文本格式（传统方法）
            try:
                import json
                parsed = json.loads(summary)
                print(f"   📊 格式: JSON格式（可能误用了KOL方法）")
            except:
                print(f"   📊 格式: 文本格式（正确的传统方法）")
        else:
            print("   ❌ 生成失败，返回None")
            
        # 直接测试传统方法
        print(f"\n🔧 直接测试传统方法...")
        from src.api.chatgpt_client import chatgpt_client
        
        tweet_contents = [tweet.full_text for tweet in tweets if tweet.full_text]
        print(f"📊 推文内容数量: {len(tweet_contents)}")
        
        traditional_summary = chatgpt_client.generate_topic_summary(
            topic_name=topic_data['topic_name'],
            related_tweets=tweet_contents
        )
        
        print(f"📄 传统方法结果:")
        if traditional_summary:
            print(f"   ✅ 成功生成 (长度: {len(traditional_summary)})")
            print(f"   内容: {traditional_summary}")
        else:
            print("   ❌ 传统方法也失败")
        
        return summary is not None or traditional_summary is not None
        
    except Exception as e:
        print(f"❌ 测试异常: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == '__main__':
    success = test_fallback_logic()
    print(f"\n🎯 回退逻辑测试结果: {'✅ 成功' if success else '❌ 失败'}")
