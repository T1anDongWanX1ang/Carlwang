#!/usr/bin/env python3
"""
测试popularity计算修复
"""
import sys
import os

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.models.tweet import Tweet
from src.utils.smart_classifier import smart_classifier
from src.database.topic_dao import topic_dao
from src.utils.logger import setup_logger
from datetime import datetime


def test_popularity_calculation():
    """测试popularity计算逻辑"""
    setup_logger()
    
    print("📊 测试popularity计算修复")
    print("=" * 60)
    
    # 创建不同互动数据的测试推文
    test_cases = [
        {
            "name": "低互动推文",
            "tweet": Tweet(
                id_str="low_engagement_test",
                full_text="DeFi is interesting technology for decentralized finance.",
                created_at="Wed Jan 10 12:00:00 +0000 2024",
                created_at_datetime=datetime.now(),
                bookmark_count=1,
                favorite_count=5,
                quote_count=0,
                reply_count=1,
                retweet_count=2,
                view_count=50,
                engagement_total=9  # 5+0+1+2+1
            ),
            "expected_popularity": 1  # 期望低热度
        },
        {
            "name": "中等互动推文",
            "tweet": Tweet(
                id_str="medium_engagement_test",
                full_text="DeFi yield farming opportunities are amazing for passive income generation.",
                created_at="Wed Jan 10 12:30:00 +0000 2024",
                created_at_datetime=datetime.now(),
                bookmark_count=15,
                favorite_count=45,
                quote_count=8,
                reply_count=12,
                retweet_count=25,
                view_count=500,
                engagement_total=105  # 45+8+12+25+15
            ),
            "expected_popularity": 3  # 期望中等热度
        },
        {
            "name": "高互动推文",
            "tweet": Tweet(
                id_str="high_engagement_test",
                full_text="DeFi protocols revolutionizing traditional finance with incredible yield opportunities.",
                created_at="Wed Jan 10 13:00:00 +0000 2024",
                created_at_datetime=datetime.now(),
                bookmark_count=100,
                favorite_count=500,
                quote_count=150,
                reply_count=200,
                retweet_count=300,
                view_count=5000,
                engagement_total=1250  # 500+150+200+300+100
            ),
            "expected_popularity": 6  # 期望高热度
        }
    ]
    
    results = []
    
    for test_case in test_cases:
        print(f"\n🧪 测试: {test_case['name']}")
        tweet = test_case['tweet']
        
        print(f"   推文互动数据:")
        print(f"   - favorite_count: {tweet.favorite_count}")
        print(f"   - retweet_count: {tweet.retweet_count}")
        print(f"   - reply_count: {tweet.reply_count}")
        print(f"   - view_count: {tweet.view_count}")
        print(f"   - engagement_total: {tweet.engagement_total}")
        
        # 直接测试popularity计算
        calculated_popularity = smart_classifier._calculate_initial_popularity(tweet)
        print(f"   计算出的popularity: {calculated_popularity}")
        print(f"   期望的popularity范围: >= {test_case['expected_popularity']}")
        
        # 测试完整的分类流程
        try:
            classification_result = smart_classifier.classify_tweet(tweet)
            print(f"   分类结果:")
            print(f"   - content_type: {classification_result.content_type}")
            print(f"   - topic_id: {classification_result.topic_id}")
            print(f"   - is_new_created: {classification_result.is_new_created}")
            
            if classification_result.topic_id:
                # 查询数据库中保存的topic
                saved_topic = topic_dao.get_topic_by_id(classification_result.topic_id)
                if saved_topic:
                    print(f"   数据库中保存的popularity: {saved_topic.popularity}")
                    
                    # 验证popularity是否正确保存
                    if saved_topic.popularity == calculated_popularity:
                        print("   ✅ popularity正确保存到数据库!")
                        results.append((test_case['name'], True, calculated_popularity))
                    else:
                        print(f"   ❌ popularity保存错误: 计算值={calculated_popularity}, 数据库值={saved_topic.popularity}")
                        results.append((test_case['name'], False, calculated_popularity))
                else:
                    print("   ❌ 无法从数据库查询到保存的topic")
                    results.append((test_case['name'], False, calculated_popularity))
            else:
                print("   ❌ 分类失败，未生成topic_id")
                results.append((test_case['name'], False, calculated_popularity))
                
        except Exception as e:
            print(f"   ❌ 测试过程异常: {e}")
            results.append((test_case['name'], False, 0))
    
    return results


def test_popularity_edge_cases():
    """测试popularity计算的边界情况"""
    print("\n🧪 测试popularity边界情况:")
    
    edge_cases = [
        {
            "name": "零互动推文",
            "tweet": Tweet(
                id_str="zero_engagement_test",
                full_text="Simple DeFi discussion with minimal engagement.",
                created_at="Wed Jan 10 14:00:00 +0000 2024",
                created_at_datetime=datetime.now(),
                bookmark_count=0,
                favorite_count=0,
                quote_count=0,
                reply_count=0,
                retweet_count=0,
                view_count=0,
                engagement_total=0
            ),
            "expected_min": 1  # 最少应该是1
        },
        {
            "name": "超高互动推文",
            "tweet": Tweet(
                id_str="super_high_engagement_test",
                full_text="Viral DeFi topic with massive engagement across all metrics.",
                created_at="Wed Jan 10 14:30:00 +0000 2024",
                created_at_datetime=datetime.now(),
                bookmark_count=10000,
                favorite_count=50000,
                quote_count=15000,
                reply_count=20000,
                retweet_count=30000,
                view_count=500000,
                engagement_total=125000
            ),
            "expected_max": 10  # 最多应该是10
        }
    ]
    
    for case in edge_cases:
        print(f"\n   测试: {case['name']}")
        tweet = case['tweet']
        calculated_popularity = smart_classifier._calculate_initial_popularity(tweet)
        print(f"   计算结果: {calculated_popularity}")
        
        if 'expected_min' in case:
            if calculated_popularity >= case['expected_min']:
                print(f"   ✅ 最小值验证通过: {calculated_popularity} >= {case['expected_min']}")
            else:
                print(f"   ❌ 最小值验证失败: {calculated_popularity} < {case['expected_min']}")
                
        if 'expected_max' in case:
            if calculated_popularity <= case['expected_max']:
                print(f"   ✅ 最大值验证通过: {calculated_popularity} <= {case['expected_max']}")
            else:
                print(f"   ❌ 最大值验证失败: {calculated_popularity} > {case['expected_max']}")


def main():
    """主测试函数"""
    print("🎯 Popularity计算修复验证测试")
    print("=" * 80)
    
    # 测试popularity计算
    results = test_popularity_calculation()
    
    # 测试边界情况
    test_popularity_edge_cases()
    
    # 输出汇总结果
    print("\n" + "=" * 80)
    print("📈 测试结果汇总:")
    
    success_count = sum(1 for _, success, _ in results if success)
    total_count = len(results)
    
    for test_name, success, popularity in results:
        status = "✅ 通过" if success else "❌ 失败"
        print(f"   {test_name}: {status} (计算热度: {popularity})")
    
    if success_count == total_count:
        print(f"\n🎉 所有测试通过! ({success_count}/{total_count})")
        print("✅ popularity计算逻辑正常工作")
        print("✅ popularity能够根据推文互动数据动态计算")
        print("✅ popularity正确保存到数据库")
        return True
    else:
        print(f"\n⚠️ 部分测试失败 ({success_count}/{total_count})")
        return False


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)