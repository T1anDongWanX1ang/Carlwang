#!/usr/bin/env python3
"""
测试智能分类逻辑
验证推文的项目和话题自动识别功能
"""
import sys
import os
from datetime import datetime

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.utils.smart_classifier import smart_classifier
from src.utils.tweet_enricher import tweet_enricher
from src.models.tweet import Tweet
from src.utils.logger import setup_logger


def test_smart_classification():
    """测试智能分类功能"""
    setup_logger()
    
    print("🚀 测试智能分类逻辑")
    print("=" * 60)
    
    # 测试用例：涵盖项目和话题的不同情况
    test_cases = [
        # 项目相关推文
        {
            "id": "test_btc_1",
            "text": "Bitcoin just broke $65,000! This is huge for the crypto market. #BTC #Bitcoin",
            "expected_type": "project",
            "expected_name": "Bitcoin"
        },
        {
            "id": "test_eth_1", 
            "text": "Ethereum 2.0 staking rewards are looking great this quarter. ETH holders are benefiting massively.",
            "expected_type": "project",
            "expected_name": "Ethereum"
        },
        {
            "id": "test_sol_1",
            "text": "Solana network congestion is finally resolved. SOL performance is back to normal.",
            "expected_type": "project", 
            "expected_name": "Solana"
        },
        
        # 话题相关推文  
        {
            "id": "test_defi_1",
            "text": "DeFi protocols are revolutionizing traditional finance. Yield farming opportunities are endless.",
            "expected_type": "topic",
            "expected_name": "DeFi"
        },
        {
            "id": "test_nft_1",
            "text": "NFT market analysis shows strong growth in digital art sector. Non-fungible tokens are here to stay.",
            "expected_type": "topic",
            "expected_name": "NFT"
        },
        {
            "id": "test_regulation_1",
            "text": "SEC announces new crypto regulation framework. This will impact the entire industry.",
            "expected_type": "topic",
            "expected_name": "SEC Regulation"
        },
        
        # 边界情况
        {
            "id": "test_mixed_1",
            "text": "Bitcoin and Ethereum are leading the DeFi revolution in Web3 space.",
            "expected_type": "project",  # 应该优先识别具体项目
            "expected_name": "Bitcoin"  # 或者Ethereum
        },
        {
            "id": "test_general_1", 
            "text": "Crypto market sentiment is bullish today. Technical analysis suggests upward trend.",
            "expected_type": "topic",
            "expected_name": "Market Analysis"
        }
    ]
    
    print(f"📋 开始测试 {len(test_cases)} 个测试用例")
    print()
    
    results = {
        "total": len(test_cases),
        "passed": 0,
        "failed": 0,
        "details": []
    }
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"🧪 测试用例 {i}: {test_case['id']}")
        print(f"📝 推文内容: {test_case['text']}")
        print(f"🎯 期望类型: {test_case['expected_type']}")
        print(f"🎯 期望名称: {test_case['expected_name']}")
        
        try:
            # 创建测试推文对象
            tweet = Tweet(
                id_str=test_case['id'],
                full_text=test_case['text'],
                created_at=datetime.now().isoformat(),
                is_valid=True
            )
            
            # 执行分类
            classification_result = smart_classifier.classify_tweet(tweet)
            
            # 分析结果
            print(f"🤖 分类结果:")
            print(f"   类型: {classification_result.content_type}")
            print(f"   实体名称: {classification_result.entity_name}")
            print(f"   置信度: {classification_result.confidence:.2f}")
            print(f"   项目ID: {classification_result.project_id}")
            print(f"   话题ID: {classification_result.topic_id}")
            print(f"   是否新创建: {classification_result.is_new_created}")
            print(f"   原因: {classification_result.reason}")
            
            # 判断测试结果
            type_match = classification_result.content_type == test_case['expected_type']
            name_match = test_case['expected_name'].lower() in classification_result.entity_name.lower()
            
            if type_match and (name_match or classification_result.content_type == 'unknown'):
                print("✅ 测试通过")
                results["passed"] += 1
                status = "PASS"
            else:
                print("❌ 测试失败")
                results["failed"] += 1
                status = "FAIL"
                print(f"   期望类型: {test_case['expected_type']}, 实际: {classification_result.content_type}")
                print(f"   期望包含: {test_case['expected_name']}, 实际: {classification_result.entity_name}")
            
            results["details"].append({
                "test_id": test_case['id'],
                "status": status,
                "expected_type": test_case['expected_type'],
                "actual_type": classification_result.content_type,
                "expected_name": test_case['expected_name'],
                "actual_name": classification_result.entity_name,
                "confidence": classification_result.confidence
            })
            
        except Exception as e:
            print(f"❌ 测试出错: {e}")
            results["failed"] += 1
            results["details"].append({
                "test_id": test_case['id'],
                "status": "ERROR",
                "error": str(e)
            })
        
        print("-" * 60)
    
    # 输出测试总结
    print(f"\n📊 测试总结:")
    print(f"总测试数: {results['total']}")
    print(f"通过: {results['passed']} ✅")
    print(f"失败: {results['failed']} ❌")
    print(f"成功率: {results['passed']/results['total']*100:.1f}%")
    
    # 详细结果
    print(f"\n📋 详细结果:")
    for detail in results["details"]:
        status_icon = "✅" if detail["status"] == "PASS" else "❌"
        print(f"{status_icon} {detail['test_id']}: {detail['status']}")
        if detail["status"] != "ERROR":
            print(f"   类型: {detail.get('expected_type', 'N/A')} → {detail.get('actual_type', 'N/A')}")
            print(f"   名称: {detail.get('expected_name', 'N/A')} → {detail.get('actual_name', 'N/A')}")
            print(f"   置信度: {detail.get('confidence', 0):.2f}")
    
    return results


def test_tweet_enricher_integration():
    """测试TweetEnricher集成"""
    print(f"\n🔧 测试TweetEnricher集成")
    print("=" * 60)
    
    try:
        # 创建测试推文
        test_tweet = Tweet(
            id_str="integration_test_1",
            full_text="Bitcoin price analysis shows strong bullish momentum. BTC technical indicators are very positive.",
            created_at=datetime.now().isoformat()
        )
        
        print(f"📝 测试推文: {test_tweet.full_text}")
        
        # 模拟用户数据
        user_data_map = {
            "mock_user": {
                "id_str": "mock_user",
                "screen_name": "test_user"
            }
        }
        
        # 执行推文增强
        enriched_tweet = tweet_enricher.enrich_single_tweet(test_tweet, user_data_map)
        
        if enriched_tweet:
            print(f"\n✅ 推文增强成功:")
            print(f"   推文ID: {enriched_tweet.id_str}")
            print(f"   是否有效: {enriched_tweet.is_valid}")
            print(f"   情绪分析: {enriched_tweet.sentiment}")
            print(f"   项目ID: {enriched_tweet.project_id}")
            print(f"   话题ID: {enriched_tweet.topic_id}")
            print(f"   实体ID: {enriched_tweet.entity_id}")
            print(f"   推文URL: {enriched_tweet.tweet_url}")
            
            return True
        else:
            print("❌ 推文增强失败")
            return False
            
    except Exception as e:
        print(f"❌ 集成测试出错: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """主函数"""
    print("🎯 智能分类逻辑测试")
    print("=" * 80)
    
    # 1. 测试智能分类功能
    classification_results = test_smart_classification()
    
    # 2. 测试TweetEnricher集成
    integration_success = test_tweet_enricher_integration()
    
    # 总结
    print(f"\n🎉 测试完成!")
    print("=" * 80)
    print(f"智能分类测试: {classification_results['passed']}/{classification_results['total']} 通过")
    print(f"集成测试: {'✅ 通过' if integration_success else '❌ 失败'}")
    
    if classification_results['passed'] == classification_results['total'] and integration_success:
        print("\n🎊 所有测试通过！新的智能分类逻辑工作正常。")
        return True
    else:
        print("\n⚠️ 部分测试失败，请检查相关逻辑。")
        return False


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)