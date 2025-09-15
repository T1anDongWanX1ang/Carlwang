#!/usr/bin/env python3
"""
调试真实的话题分析流程
模拟话题引擎的调用过程，查看话题提取和summary生成的完整流程
"""
import sys
import os
from datetime import datetime, timedelta

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.database.tweet_dao import tweet_dao
from src.utils.topic_analyzer import topic_analyzer
from src.utils.logger import setup_logger


def test_real_topic_analysis():
    """测试真实的话题分析流程"""
    setup_logger()
    
    print("🔍 调试真实话题分析流程")
    print("=" * 60)
    
    try:
        # 1. 获取最近的推文（模拟topic_engine的逻辑）
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=1)  # 最近1小时
        
        recent_tweets = tweet_dao.get_tweets_by_date_range(
            start_date=start_time,
            end_date=end_time,
            limit=20  # 少一些推文便于调试
        )
        
        print(f"📊 获取到 {len(recent_tweets)} 条最近推文")
        
        if not recent_tweets:
            print("❌ 没有找到最近的推文数据")
            return False
            
        # 2. 分析推文内容
        print("\n📋 推文样本（前5条）:")
        for i, tweet in enumerate(recent_tweets[:5], 1):
            kol_status = f"KOL: {tweet.kol_id}" if hasattr(tweet, 'kol_id') and tweet.kol_id else "非KOL"
            print(f"   {i}. [{kol_status}] {tweet.full_text[:100]}...")
        
        # 3. 调用话题提取（这是关键步骤）
        print(f"\n🔧 开始话题提取...")
        topics = topic_analyzer.extract_topics_from_tweets(recent_tweets[:10])  # 只用前10条
        
        print(f"📊 话题提取结果: {len(topics)} 个话题")
        
        if topics:
            print("\n📄 提取的话题详情:")
            for i, topic in enumerate(topics, 1):
                print(f"   话题 {i}: {topic.topic_name}")
                print(f"     Brief: {topic.brief}")
                print(f"     Summary: {'有内容' if topic.summary else '无内容(None)'}")
                if topic.summary:
                    preview = topic.summary[:150] + "..." if len(topic.summary) > 150 else topic.summary
                    print(f"     Summary预览: {preview}")
                print(f"     热度: {topic.popularity}")
                print()
                
            return True
        else:
            print("❌ 没有提取到任何话题")
            return False
            
    except Exception as e:
        print(f"❌ 调试过程异常: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_single_tweet_extraction():
    """测试单条推文的话题提取"""
    print("\n🧪 测试单条推文话题提取")
    print("=" * 60)
    
    try:
        # 获取一条KOL推文进行测试
        recent_tweets = tweet_dao.get_tweets_by_date_range(
            start_date=datetime.now() - timedelta(days=1),
            end_date=datetime.now(),
            limit=50
        )
        
        kol_tweet = None
        for tweet in recent_tweets:
            if hasattr(tweet, 'kol_id') and tweet.kol_id:
                kol_tweet = tweet
                break
        
        if kol_tweet:
            print(f"📊 找到KOL推文: {kol_tweet.full_text[:100]}...")
            print(f"   KOL ID: {kol_tweet.kol_id}")
            
            # 使用ChatGPT提取话题信息
            from src.api.chatgpt_client import chatgpt_client
            topic_info = chatgpt_client.extract_topic_from_tweet(kol_tweet.full_text)
            
            print(f"📄 ChatGPT提取结果:")
            if topic_info:
                print(f"   话题名称: {topic_info.get('topic_name')}")
                print(f"   话题简述: {topic_info.get('brief')}")
                return True
            else:
                print("   ❌ 没有提取到话题信息")
                return False
        else:
            print("❌ 没有找到KOL推文")
            return False
            
    except Exception as e:
        print(f"❌ 单条推文测试异常: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """主函数"""
    print("🚨 真实话题分析流程调试")
    print("=" * 80)
    
    # 测试1: 完整的话题分析流程
    success1 = test_real_topic_analysis()
    
    # 测试2: 单条推文提取
    success2 = test_single_tweet_extraction()
    
    # 总结
    print("\n" + "=" * 80)
    print("🎯 调试结果总结:")
    print(f"   完整话题分析: {'✅ 通过' if success1 else '❌ 失败'}")
    print(f"   单条推文提取: {'✅ 通过' if success2 else '❌ 失败'}")
    
    if success1 and success2:
        print("\n✅ 话题分析流程正常，问题可能在其他环节")
    elif success1 and not success2:
        print("\n⚠️ 单条推文提取有问题，可能是ChatGPT调用异常")
    elif not success1 and success2:
        print("\n⚠️ 话题聚合或创建过程有问题")
    else:
        print("\n❌ 话题提取的基础功能有问题")


if __name__ == '__main__':
    main()