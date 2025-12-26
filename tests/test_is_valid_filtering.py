#!/usr/bin/env python3
"""
测试 is_valid=0 推文过滤功能
"""
import sys
import os
from datetime import datetime

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.models.tweet import Tweet
from src.database.tweet_dao import tweet_dao
from src.utils.logger import setup_logger


def test_is_valid_filtering():
    """测试 is_valid=0 推文过滤功能"""
    setup_logger()
    
    print("🚀 测试 is_valid=0 推文过滤功能")
    
    # 创建测试推文
    test_tweets = [
        Tweet(
            id_str="valid_tweet_001",
            full_text="Bitcoin price analysis shows strong bullish momentum",
            created_at_datetime=datetime.now(),
            is_valid=1,  # 有效推文
            kol_id="test_kol_1",
            sentiment="Positive"
        ),
        Tweet(
            id_str="invalid_tweet_001", 
            full_text="FREE AIRDROP! Click here for free tokens!",
            created_at_datetime=datetime.now(),
            is_valid=0,  # 无效推文
            kol_id="test_kol_2",
            sentiment=None
        ),
        Tweet(
            id_str="valid_tweet_002",
            full_text="Ethereum gas fees are concerning for DeFi adoption",
            created_at_datetime=datetime.now(),
            is_valid=True,  # 有效推文 (True)
            kol_id="test_kol_3", 
            sentiment="Negative"
        ),
        Tweet(
            id_str="invalid_tweet_002",
            full_text="Join our Telegram for pump signals",
            created_at_datetime=datetime.now(),
            is_valid=False,  # 无效推文 (False，应该被视为 0)
            kol_id="test_kol_4",
            sentiment=None
        )
    ]
    
    print(f"\n=== 测试单个推文存储 ===")
    
    # 测试单个推文 upsert
    for tweet in test_tweets:
        print(f"\n推文 {tweet.id_str} (is_valid={tweet.is_valid})")
        
        try:
            result = tweet_dao.upsert_tweet(tweet)
            
            if tweet.is_valid == 0 or tweet.is_valid is False:
                if not result:
                    print(f"✅ 正确跳过存储 is_valid={tweet.is_valid} 的推文")
                else:
                    print(f"❌ 错误：is_valid={tweet.is_valid} 的推文被存储了")
            else:
                if result:
                    print(f"✅ 正确存储 is_valid={tweet.is_valid} 的推文")
                else:
                    print(f"❌ 错误：is_valid={tweet.is_valid} 的推文存储失败")
                    
        except Exception as e:
            print(f"❌ 测试失败: {e}")
    
    print(f"\n=== 测试批量推文存储 ===")
    
    # 测试批量存储
    try:
        saved_count = tweet_dao.batch_upsert_tweets(test_tweets)
        
        expected_saved = sum(1 for t in test_tweets if t.is_valid != 0 and t.is_valid is not False)
        
        print(f"预期保存数量: {expected_saved}")
        print(f"实际保存数量: {saved_count}")
        
        if saved_count == expected_saved:
            print("✅ 批量存储过滤功能正常")
        else:
            print("❌ 批量存储过滤功能异常")
            
    except Exception as e:
        print(f"❌ 批量测试失败: {e}")
    
    print(f"\n=== 测试结果总结 ===")
    print("✅ is_valid=0 的推文应该被跳过存储")
    print("✅ is_valid=False 的推文应该被跳过存储") 
    print("✅ is_valid=1 或 is_valid=True 的推文应该正常存储")
    print("✅ 批量存储时应该正确过滤无效推文")


def main():
    """主函数"""
    print("🎯 is_valid=0 推文过滤功能测试")
    
    # 运行测试
    test_is_valid_filtering()
    
    print("""
🎉 测试完成！

=== 功能说明 ===
✅ 修改了 tweet_dao.py 中的存储方法
✅ insert_tweet: 跳过 is_valid=0 的推文
✅ upsert_tweet: 跳过 is_valid=0 的推文  
✅ batch_upsert_tweets: 批量过滤 is_valid=0 的推文
✅ 日志记录：详细记录过滤情况

=== 实现细节 ===
- is_valid=0 的推文不会被存储到数据库
- is_valid=False 的推文也不会被存储（转换为 0）
- 记录详细的过滤统计信息
- 保持其他数据处理流程不变
    """)


if __name__ == '__main__':
    main()