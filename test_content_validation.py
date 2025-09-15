#!/usr/bin/env python3
"""
推文内容验证和情绪分析测试
"""
import sys
import os
from datetime import datetime

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.utils.tweet_enricher import tweet_enricher
from src.models.tweet import Tweet
from src.utils.logger import setup_logger


def test_content_validation():
    """测试内容验证功能"""
    setup_logger()
    
    print("🚀 测试推文内容验证和情绪分析")
    
    # 测试用例
    test_cases = [
        {
            "name": "有效的比特币分析",
            "text": "Bitcoin is showing strong support at $65,000. Technical analysis suggests a potential breakout to $70k. The market structure looks bullish.",
            "expected_valid": True,
            "expected_sentiment": "Positive"
        },
        {
            "name": "有效的负面观点",
            "text": "Ethereum gas fees are getting ridiculous again. This is why DeFi adoption is slowing down. We need Layer 2 solutions urgently.",
            "expected_valid": True,
            "expected_sentiment": "Negative"
        },
        {
            "name": "有效的中性分析",
            "text": "Bitcoin price analysis: Currently trading in a range between $60k-$68k. Volume has been declining. Market waiting for next catalyst.",
            "expected_valid": True,
            "expected_sentiment": "Neutral"
        },
        {
            "name": "明显的广告",
            "text": "🚀🚀🚀 FREE AIRDROP!!! Join our Telegram now and get 1000 FREE tokens! Limited time offer! Click link in bio! 💰💰💰",
            "expected_valid": False,
            "expected_sentiment": None
        },
        {
            "name": "非加密货币内容",
            "text": "Just had an amazing coffee at Starbucks! The weather is beautiful today. Going to watch a movie tonight.",
            "expected_valid": False,
            "expected_sentiment": None
        },
        {
            "name": "中文加密货币内容",
            "text": "比特币今天突破了重要阻力位，技术面看起来很强势。以太坊也在跟涨，整个市场情绪转向乐观。",
            "expected_valid": True,
            "expected_sentiment": "Positive"
        }
    ]
    
    print(f"\n=== 测试 {len(test_cases)} 个用例 ===")
    
    success_count = 0
    total_count = len(test_cases)
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n📝 测试用例 {i}: {test_case['name']}")
        print(f"内容: {test_case['text'][:80]}...")
        
        try:
            # 创建测试推文
            tweet = Tweet(
                id_str=f"test_{i:03d}",
                full_text=test_case['text'],
                created_at_datetime=datetime.now()
            )
            
            # 测试内容验证
            is_valid = tweet_enricher._validate_crypto_content(tweet.full_text)
            print(f"内容验证: {is_valid} (预期: {test_case['expected_valid']})")
            
            # 测试情绪分析（仅对有效内容）
            if is_valid:
                sentiment = tweet_enricher._analyze_tweet_sentiment(tweet.full_text)
                print(f"情绪分析: {sentiment} (预期: {test_case['expected_sentiment']})")
                
                # 验证结果
                valid_correct = is_valid == test_case['expected_valid']
                sentiment_correct = sentiment == test_case['expected_sentiment']
                
                if valid_correct and sentiment_correct:
                    print("✅ 测试通过")
                    success_count += 1
                else:
                    print("❌ 测试失败")
                    
            else:
                # 无效内容的测试
                valid_correct = is_valid == test_case['expected_valid']
                
                if valid_correct:
                    print("✅ 测试通过（正确识别为无效内容）")
                    success_count += 1
                else:
                    print("❌ 测试失败")
            
        except Exception as e:
            print(f"❌ 测试用例执行失败: {e}")
    
    print(f"\n=== 测试结果 ===")
    print(f"成功: {success_count}/{total_count}")
    print(f"成功率: {success_count/total_count*100:.1f}%")
    
    return success_count == total_count


def test_full_enrichment_flow():
    """测试完整的推文增强流程"""
    print("\n🔄 测试完整推文增强流程")
    
    # 创建测试推文
    test_tweet = Tweet(
        id_str="full_flow_test_001",
        full_text="Solana ecosystem is gaining momentum! New DeFi protocols launching daily. SOL price looking strong with good fundamentals.",
        created_at_datetime=datetime.now()
    )
    
    # 用户数据映射
    user_data_map = {
        "17351167": {
            "id_str": "17351167",
            "screen_name": "testuser",
            "name": "Test User"
        }
    }
    
    try:
        print(f"原始推文: {test_tweet.full_text[:100]}...")
        print(f"初始状态 - is_valid: {test_tweet.is_valid}, sentiment: {test_tweet.sentiment}")
        
        # 执行完整增强
        enriched_tweet = tweet_enricher.enrich_single_tweet(test_tweet, user_data_map)
        
        if enriched_tweet:
            print(f"\n✅ 完整增强成功!")
            print(f"KOL ID: {enriched_tweet.kol_id}")
            print(f"Is Valid: {enriched_tweet.is_valid}")
            print(f"Sentiment: {enriched_tweet.sentiment}")
            print(f"Entity ID: {enriched_tweet.entity_id}")
            
            return True
        else:
            print("❌ 完整增强失败")
            return False
            
    except Exception as e:
        print(f"❌ 完整增强流程出错: {e}")
        return False


def main():
    """主函数"""
    print("🎯 推文内容验证和情绪分析测试")
    
    # 测试内容验证
    if test_content_validation():
        print("\n✅ 内容验证测试通过")
    else:
        print("\n❌ 内容验证测试失败")
        return
    
    # 测试完整流程
    if test_full_enrichment_flow():
        print("\n✅ 完整流程测试通过")
    else:
        print("\n❌ 完整流程测试失败")
        return
    
    print("""
🎉 所有测试通过！

=== 功能总结 ===
✅ 内容质量验证：自动识别有效的加密货币相关内容
✅ 广告过滤：过滤明显的广告和垃圾内容
✅ 情绪分析：Positive/Negative/Neutral三级分类
✅ 流程优化：仅对有效内容进行深度分析
✅ 关键词备用：在API不可用时使用关键词模式

=== 数据映射 ===
- is_valid字段：true(有效加密货币内容) / false(无效或广告)
- sentiment字段：Positive / Negative / Neutral
- 仅有效推文会进行话题分析和entity_id生成
    """)


if __name__ == '__main__':
    main() 