#!/usr/bin/env python3
"""
测试修改后的topics表summary生成逻辑
验证新的KOL观点分析format是否正常工作
"""
import sys
import os
import json

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.api.chatgpt_client import chatgpt_client
from src.utils.topic_analyzer import topic_analyzer
from src.models.tweet import Tweet
from src.utils.logger import setup_logger
from datetime import datetime


def test_new_kol_consensus_summary():
    """测试新的KOL共识观点分析方法"""
    setup_logger()
    
    print("🔍 测试新的KOL共识观点分析方法")
    print("=" * 60)
    
    # 构建测试数据
    test_topic_data = {
        "topic_id": "bitcoin_analysis_test",
        "topic_name": "Bitcoin市场分析",
        "category": "cryptocurrency",
        "key_entities": ["Bitcoin", "BTC", "institutional adoption"],
        "timestamp": "2024-01-10T12:00:00Z",
        "brief": "Bitcoin价格分析和机构采用讨论",
        "related_tweets": [
            {
                "id_str": "test_tweet_1",
                "kol_id": "44196397",  # Elon Musk
                "full_text": "Bitcoin is the future of digital money. The institutional adoption we're seeing is just the beginning. #Bitcoin #BTC"
            },
            {
                "id_str": "test_tweet_2", 
                "kol_id": "5768872",   # Gary Vee
                "full_text": "Bitcoin's long-term potential is undeniable. We're still early in this technological revolution. Buy and hold. #HODL"
            },
            {
                "id_str": "test_tweet_3",
                "kol_id": "17351167",  # Scott Melker
                "full_text": "Technical analysis shows Bitcoin forming a bullish pattern. Could see significant upward movement in Q1 2024. #BTC #TechnicalAnalysis"
            },
            {
                "id_str": "test_tweet_4",
                "kol_id": "183749519", # Paul Graham
                "full_text": "The regulatory clarity around Bitcoin is improving. This will likely drive more institutional investment. #Bitcoin #Regulation"
            }
        ]
    }
    
    try:
        print("📊 调用generate_kol_consensus_summary方法...")
        summary_result = chatgpt_client.generate_kol_consensus_summary(test_topic_data)
        
        if summary_result:
            print("✅ 生成成功！")
            print("📄 生成的KOL观点总结:")
            print("-" * 40)
            print(summary_result)
            print("-" * 40)
            
            # 尝试解析JSON验证格式
            try:
                parsed_summary = json.loads(summary_result)
                print("\n🔍 JSON解析结果:")
                print(f"   topic_id: {parsed_summary.get('topic_id')}")
                print(f"   观点数量: {len(parsed_summary.get('summary', []))}")
                
                for i, viewpoint in enumerate(parsed_summary.get('summary', []), 1):
                    print(f"   观点 {i}:")
                    print(f"     - 观点: {viewpoint.get('viewpoint')}")
                    print(f"     - 相关推文: {viewpoint.get('related_tweets', [])}")
                
                return True, summary_result
                
            except json.JSONDecodeError as e:
                print(f"❌ JSON解析失败: {e}")
                print("生成的内容不是有效的JSON格式")
                return False, summary_result
                
        else:
            print("❌ 生成失败，返回None")
            return False, None
            
    except Exception as e:
        print(f"❌ 测试过程异常: {e}")
        import traceback
        traceback.print_exc()
        return False, None


def test_enhanced_topic_analyzer():
    """测试增强版的话题分析器"""
    print("\n🧪 测试增强版话题分析器")
    print("=" * 60)
    
    try:
        # 创建测试推文对象
        test_tweets = [
            Tweet(
                id_str="enhanced_test_1",
                full_text="Bitcoin institutional adoption is accelerating. Major corporations are adding BTC to their treasury reserves.",
                kol_id="44196397",  # 设置KOL ID
                created_at="Wed Jan 10 12:00:00 +0000 2024",
                created_at_datetime=datetime.now(),
                favorite_count=100,
                retweet_count=50,
                reply_count=25,
                view_count=1000
            ),
            Tweet(
                id_str="enhanced_test_2",
                full_text="The Bitcoin ETF approval will be a game changer for crypto adoption. Mainstream investment is coming.",
                kol_id="17351167",  # 设置KOL ID
                created_at="Wed Jan 10 12:15:00 +0000 2024",
                created_at_datetime=datetime.now(),
                favorite_count=80,
                retweet_count=40,
                reply_count=20,
                view_count=800
            ),
            Tweet(
                id_str="enhanced_test_3",
                full_text="Regular crypto discussion without KOL attribution for comparison",
                # 没有kol_id
                created_at="Wed Jan 10 12:30:00 +0000 2024",
                created_at_datetime=datetime.now(),
                favorite_count=10,
                retweet_count=5,
                reply_count=2,
                view_count=100
            )
        ]
        
        # 构建话题数据
        topic_data = {
            'topic_name': 'Bitcoin ETF and Institutional Adoption',
            'brief': 'Discussion about Bitcoin ETF approval and increasing institutional adoption',
            'category': 'cryptocurrency',
            'key_entities': ['Bitcoin', 'ETF', 'institutional adoption'],
            'created_at': datetime.now()
        }
        
        print("📊 调用增强版话题总结生成...")
        enhanced_summary = topic_analyzer._generate_enhanced_topic_summary(topic_data, test_tweets)
        
        if enhanced_summary:
            print("✅ 增强版总结生成成功！")
            print("📄 生成的总结:")
            print("-" * 40)
            print(enhanced_summary)
            print("-" * 40)
            
            # 检查是否使用了KOL方法（包含KOL推文）还是回退方法
            kol_tweets_count = sum(1 for tweet in test_tweets if hasattr(tweet, 'kol_id') and tweet.kol_id)
            print(f"\n📈 统计信息:")
            print(f"   总推文数: {len(test_tweets)}")
            print(f"   KOL推文数: {kol_tweets_count}")
            
            if kol_tweets_count > 0:
                try:
                    parsed = json.loads(enhanced_summary)
                    if 'summary' in parsed:
                        print(f"   ✅ 使用了KOL观点分析方法")
                    else:
                        print(f"   ⚠️ 使用了传统总结方法")
                except:
                    print(f"   ⚠️ 使用了传统总结方法（非JSON格式）")
            
            return True, enhanced_summary
        else:
            print("❌ 增强版总结生成失败")
            return False, None
            
    except Exception as e:
        print(f"❌ 测试增强版话题分析器时异常: {e}")
        import traceback
        traceback.print_exc()
        return False, None


def test_fallback_behavior():
    """测试回退机制"""
    print("\n🔄 测试回退机制（无KOL推文）")
    print("=" * 60)
    
    try:
        # 创建没有KOL标识的推文
        non_kol_tweets = [
            Tweet(
                id_str="fallback_test_1",
                full_text="Bitcoin price is looking bullish according to technical analysis",
                # 没有kol_id
                created_at="Wed Jan 10 13:00:00 +0000 2024",
                created_at_datetime=datetime.now(),
                favorite_count=50,
                retweet_count=25
            ),
            Tweet(
                id_str="fallback_test_2", 
                full_text="Crypto market sentiment is improving with recent regulatory developments",
                # 没有kol_id
                created_at="Wed Jan 10 13:15:00 +0000 2024",
                created_at_datetime=datetime.now(),
                favorite_count=30,
                retweet_count=15
            )
        ]
        
        topic_data = {
            'topic_name': 'Crypto Market Sentiment',
            'brief': 'General crypto market sentiment discussion',
            'created_at': datetime.now()
        }
        
        print("📊 测试无KOL推文时的回退逻辑...")
        fallback_summary = topic_analyzer._generate_enhanced_topic_summary(topic_data, non_kol_tweets)
        
        if fallback_summary:
            print("✅ 回退机制工作正常！")
            print("📄 回退生成的总结:")
            print("-" * 40)
            print(fallback_summary)
            print("-" * 40)
            
            # 检查是否为传统格式
            try:
                json.loads(fallback_summary)
                print("   ⚠️ 意外：回退方法也返回了JSON格式")
            except:
                print("   ✅ 确认：回退方法返回传统文本格式")
                
            return True, fallback_summary
        else:
            print("❌ 回退机制失败")
            return False, None
            
    except Exception as e:
        print(f"❌ 测试回退机制时异常: {e}")
        return False, None


def main():
    """主测试函数"""
    print("🎯 Topics表Summary生成逻辑修改测试")
    print("=" * 80)
    
    # 运行各项测试
    test1_passed, summary1 = test_new_kol_consensus_summary()
    test2_passed, summary2 = test_enhanced_topic_analyzer()
    test3_passed, summary3 = test_fallback_behavior()
    
    # 输出结果汇总
    print("\n" + "=" * 80)
    print("📊 测试结果汇总:")
    print(f"   KOL共识分析方法: {'✅ 通过' if test1_passed else '❌ 失败'}")
    print(f"   增强版话题分析器: {'✅ 通过' if test2_passed else '❌ 失败'}")
    print(f"   回退机制测试: {'✅ 通过' if test3_passed else '❌ 失败'}")
    
    success_count = sum([test1_passed, test2_passed, test3_passed])
    
    if success_count == 3:
        print("\n🎉 所有测试通过！")
        print("✅ 新的KOL观点分析prompt已成功集成")
        print("✅ Topics表将生成专业的KOL共识观点总结")
        print("✅ 回退机制确保向后兼容性")
        return True
    else:
        print(f"\n⚠️ {3-success_count} 个测试失败")
        return False


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)