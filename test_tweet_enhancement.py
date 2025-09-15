#!/usr/bin/env python3
"""
测试推文增强器
"""
import sys
import os

# 添加项目根目录到路径
sys.path.append(os.path.dirname(__file__))

from src.models.tweet import Tweet
from src.utils.tweet_enricher import tweet_enricher

def test_tweet_enhancement():
    """测试推文增强器"""
    
    try:
        # 创建一个测试推文
        test_tweet = Tweet(
            id_str='1965999999999999999',
            full_text='Bitcoin price hits new all-time high! ETH also surging with DeFi protocols showing strong growth. Crypto market looking bullish!',
            created_at='Wed Sep 10 20:00:00 +0000 2025'
        )
        
        # 创建模拟用户数据
        user_data_map = {
            'test_user': {
                'id_str': '123456789',
                'screen_name': 'test_user'
            }
        }
        
        print("原始推文:")
        print(f"  - id_str: {test_tweet.id_str}")
        print(f"  - kol_id: {test_tweet.kol_id}")
        print(f"  - is_valid: {test_tweet.is_valid}")
        print(f"  - sentiment: {test_tweet.sentiment}")
        print(f"  - tweet_url: {test_tweet.tweet_url}")
        print(f"  - full_text: {test_tweet.full_text}")
        
        # 使用推文增强器处理
        enhanced_tweet = tweet_enricher.enrich_single_tweet(test_tweet, user_data_map)
        
        print("\n增强后推文:")
        print(f"  - id_str: {enhanced_tweet.id_str}")
        print(f"  - kol_id: {enhanced_tweet.kol_id}")
        print(f"  - is_valid: {enhanced_tweet.is_valid}")
        print(f"  - sentiment: {enhanced_tweet.sentiment}")
        print(f"  - tweet_url: {enhanced_tweet.tweet_url}")
        print(f"  - entity_id: {enhanced_tweet.entity_id}")
        
        # 测试to_dict()方法
        tweet_dict = enhanced_tweet.to_dict()
        print("\nto_dict()结果:")
        print(f"  - kol_id: {tweet_dict.get('kol_id')}")
        print(f"  - is_valid: {tweet_dict.get('is_valid')}")
        print(f"  - sentiment: {tweet_dict.get('sentiment')}")
        print(f"  - tweet_url: {tweet_dict.get('tweet_url')}")
        print(f"  - entity_id: {tweet_dict.get('entity_id')}")
        
    except Exception as e:
        print(f"测试失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    test_tweet_enhancement()