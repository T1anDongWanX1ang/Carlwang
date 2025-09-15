#!/usr/bin/env python3
"""
测试kol_id提取逻辑修复
"""
import sys
import os
from datetime import datetime

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.models.tweet import Tweet
from src.utils.tweet_enricher import tweet_enricher
from src.utils.logger import setup_logger


def test_kol_id_extraction():
    """测试修复后的kol_id提取逻辑"""
    setup_logger()
    
    print("🚀 测试修复后的kol_id提取逻辑")
    
    # 模拟API数据结构 - 每个推文对应一个用户
    test_cases = [
        {
            "tweet": Tweet(
                id_str="tweet_001",
                full_text="Bitcoin is looking bullish today!",
                created_at_datetime=datetime.now()
            ),
            "user_data_map": {
                "tweet_001": {
                    "id_str": "user_123",
                    "screen_name": "bitcoin_trader",
                    "name": "Bitcoin Trader"
                }
            },
            "expected_kol_id": "user_123"
        },
        {
            "tweet": Tweet(
                id_str="tweet_002", 
                full_text="Ethereum DeFi ecosystem is growing rapidly",
                created_at_datetime=datetime.now()
            ),
            "user_data_map": {
                "tweet_002": {
                    "id_str": "user_456",
                    "screen_name": "defi_expert",
                    "name": "DeFi Expert"
                }
            },
            "expected_kol_id": "user_456"
        },
        {
            "tweet": Tweet(
                id_str="tweet_003",
                full_text="Solana network performance improvements",
                created_at_datetime=datetime.now()
            ),
            "user_data_map": {
                "tweet_003": {
                    "id_str": "user_789", 
                    "screen_name": "sol_developer",
                    "name": "Solana Developer"
                }
            },
            "expected_kol_id": "user_789"
        },
        {
            "tweet": Tweet(
                id_str="tweet_004",
                full_text="Market analysis for today",
                created_at_datetime=datetime.now()
            ),
            "user_data_map": {
                # 没有对应的用户数据
            },
            "expected_kol_id": None
        }
    ]
    
    print(f"\n=== 测试 {len(test_cases)} 个用例 ===")
    
    success_count = 0
    total_count = len(test_cases)
    
    for i, test_case in enumerate(test_cases, 1):
        tweet = test_case["tweet"] 
        user_data_map = test_case["user_data_map"]
        expected_kol_id = test_case["expected_kol_id"]
        
        print(f"\n📝 测试用例 {i}: 推文 {tweet.id_str}")
        print(f"用户数据映射: {list(user_data_map.keys())}")
        print(f"预期kol_id: {expected_kol_id}")
        
        try:
            # 使用修复后的方法提取kol_id
            extracted_kol_id = tweet_enricher._extract_kol_id_from_user_data(tweet, user_data_map)
            print(f"提取的kol_id: {extracted_kol_id}")
            
            # 验证结果
            if extracted_kol_id == expected_kol_id:
                print("✅ 测试通过")
                success_count += 1
            else:
                print("❌ 测试失败")
                
        except Exception as e:
            print(f"❌ 测试用例执行失败: {e}")
    
    print(f"\n=== 测试结果 ===")
    print(f"成功: {success_count}/{total_count}")
    print(f"成功率: {success_count/total_count*100:.1f}%")
    
    return success_count == total_count


def test_multiple_tweets_unique_users():
    """测试多条推文对应不同用户的情况"""
    print("\n🔄 测试多条推文对应不同用户")
    
    # 模拟多条推文，每条推文对应不同的用户
    tweets = [
        Tweet(id_str="tweet_A", full_text="Tweet A content", created_at_datetime=datetime.now()),
        Tweet(id_str="tweet_B", full_text="Tweet B content", created_at_datetime=datetime.now()), 
        Tweet(id_str="tweet_C", full_text="Tweet C content", created_at_datetime=datetime.now())
    ]
    
    # 每条推文对应不同的用户
    user_data_map = {
        "tweet_A": {"id_str": "user_A", "screen_name": "userA"},
        "tweet_B": {"id_str": "user_B", "screen_name": "userB"},
        "tweet_C": {"id_str": "user_C", "screen_name": "userC"}
    }
    
    print(f"测试推文数量: {len(tweets)}")
    print(f"用户数据映射: {list(user_data_map.keys())}")
    
    results = []
    for tweet in tweets:
        kol_id = tweet_enricher._extract_kol_id_from_user_data(tweet, user_data_map)
        results.append((tweet.id_str, kol_id))
        print(f"推文 {tweet.id_str} -> kol_id: {kol_id}")
    
    # 验证每条推文都得到了正确的用户ID
    expected_mapping = {
        "tweet_A": "user_A",
        "tweet_B": "user_B", 
        "tweet_C": "user_C"
    }
    
    all_correct = True
    for tweet_id, kol_id in results:
        if kol_id != expected_mapping.get(tweet_id):
            print(f"❌ 推文 {tweet_id} 的kol_id不正确: 期望 {expected_mapping.get(tweet_id)}, 实际 {kol_id}")
            all_correct = False
    
    if all_correct:
        print("✅ 多推文测试通过 - 每条推文都正确映射到对应用户")
    else:
        print("❌ 多推文测试失败")
    
    return all_correct


def main():
    """主函数"""
    print("🎯 kol_id提取逻辑修复验证")
    
    # 测试基本提取逻辑
    if test_kol_id_extraction():
        print("\n✅ 基本提取逻辑测试通过")
    else:
        print("\n❌ 基本提取逻辑测试失败")
        return
    
    # 测试多推文映射
    if test_multiple_tweets_unique_users():
        print("\n✅ 多推文映射测试通过")
    else:
        print("\n❌ 多推文映射测试失败")
        return
    
    print("""
🎉 所有测试通过！

=== 修复内容总结 ===
✅ 修改了user_data_map的构建逻辑：从 {user_id: user_data} 改为 {tweet_id: user_data}
✅ 修复了_extract_kol_id_from_user_data方法：根据tweet_id正确查找对应用户
✅ 解决了kol_id重复问题：每条推文现在能正确映射到发推的用户
✅ 保持了向后兼容性：处理了映射为空的边界情况

=== 实现原理 ===
- API数据结构：每条推文数据包含一个user字段
- 映射关系：tweet_id -> user_data，确保每条推文对应正确的用户
- 提取逻辑：根据推文ID直接查找对应的用户数据
- 缓存问题解决：不再使用有问题的全局用户缓存遍历
    """)


if __name__ == '__main__':
    main()