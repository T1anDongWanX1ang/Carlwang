#!/usr/bin/env python3
"""
测试推文entity_id智能处理逻辑
测试话题和项目的智能识别功能
"""
import sys
import os
from datetime import datetime

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.models.tweet import Tweet
from src.utils.tweet_enricher import tweet_enricher
from src.utils.logger import setup_logger


def test_entity_analysis():
    """测试实体分析功能（话题 vs 项目）"""
    setup_logger()
    
    print("🚀 测试推文entity_id智能处理逻辑")
    
    # 测试用例
    test_cases = [
        {
            "name": "Bitcoin项目相关",
            "text": "Bitcoin price is showing strong support at $65,000. BTC holders should stay strong!",
            "expected_type": "project",
            "expected_name": "Bitcoin",
            "expected_prefix": "project_"
        },
        {
            "name": "Ethereum项目相关", 
            "text": "Ethereum gas fees are high again. ETH needs better scaling solutions.",
            "expected_type": "project",
            "expected_name": "Ethereum",
            "expected_prefix": "project_"
        },
        {
            "name": "DeFi话题讨论",
            "text": "DeFi protocols are revolutionizing finance. The yield farming opportunities are endless.",
            "expected_type": "topic",
            "expected_name": "DeFi生态",
            "expected_prefix": "topic_"
        },
        {
            "name": "NFT话题讨论",
            "text": "NFT market is showing signs of recovery. Digital art collections are trending again.",
            "expected_type": "topic", 
            "expected_name": "NFT市场",
            "expected_prefix": "topic_"
        },
        {
            "name": "Solana项目相关",
            "text": "Solana network performance has improved significantly. SOL is undervalued IMO.",
            "expected_type": "project",
            "expected_name": "Solana", 
            "expected_prefix": "project_"
        },
        {
            "name": "市场分析话题",
            "text": "Market analysis suggests we're in a consolidation phase. Technical indicators are mixed.",
            "expected_type": "topic",
            "expected_name": "市场分析",
            "expected_prefix": "topic_"
        },
        {
            "name": "Layer2话题讨论",
            "text": "Layer2 solutions are the future of Ethereum scaling. Optimistic rollups vs ZK rollups debate continues.", 
            "expected_type": "topic",
            "expected_name": "Layer2扩容",
            "expected_prefix": "topic_"
        }
    ]
    
    print(f"\n=== 测试 {len(test_cases)} 个用例 ===")
    
    success_count = 0
    total_count = len(test_cases)
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n📝 测试用例 {i}: {test_case['name']}")
        print(f"内容: {test_case['text']}")
        
        try:
            # 创建测试推文
            tweet = Tweet(
                id_str=f"entity_test_{i:03d}",
                full_text=test_case['text'],
                created_at_datetime=datetime.now(),
                is_valid=True  # 设为有效推文，确保会进行实体分析
            )
            
            # 使用AI分析实体
            entity_info = tweet_enricher._analyze_entity_with_ai(tweet.full_text)
            
            # 如果AI分析失败，使用关键词模式
            if not entity_info:
                entity_info = tweet_enricher._analyze_entity_with_keywords(tweet.full_text)
                print("  使用关键词模式分析")
            else:
                print("  使用AI模式分析")
            
            if entity_info:
                entity_type = entity_info.get('type')
                entity_name = entity_info.get('name')
                
                print(f"  识别类型: {entity_type}")
                print(f"  识别名称: {entity_name}")
                
                # 生成完整的entity_id
                if entity_type == 'project':
                    entity_id = tweet_enricher._handle_project_entity(entity_name, entity_info.get('brief', ''), tweet.id_str)
                elif entity_type == 'topic':
                    entity_id = tweet_enricher._handle_topic_entity(entity_name, entity_info.get('brief', ''), tweet.id_str)
                else:
                    entity_id = None
                
                print(f"  生成entity_id: {entity_id}")
                
                # 验证结果
                type_correct = entity_type == test_case['expected_type']
                prefix_correct = entity_id and entity_id.startswith(test_case['expected_prefix']) if entity_id else False
                
                if type_correct and prefix_correct:
                    print("✅ 测试通过")
                    success_count += 1
                else:
                    print("❌ 测试失败")
                    if not type_correct:
                        print(f"   类型错误: 期望{test_case['expected_type']}, 实际{entity_type}")
                    if not prefix_correct:
                        print(f"   前缀错误: 期望以{test_case['expected_prefix']}开头, 实际{entity_id}")
            else:
                print("❌ 未识别出实体")
            
        except Exception as e:
            print(f"❌ 测试用例执行失败: {e}")
    
    print(f"\n=== 测试结果 ===")
    print(f"成功: {success_count}/{total_count}")
    print(f"成功率: {success_count/total_count*100:.1f}%")
    
    return success_count == total_count


def test_same_entity_same_id():
    """测试同一实体使用相同ID"""
    print("\n🔄 测试同一实体使用相同ID")
    
    # 测试相同项目的不同推文应该得到相同的project_id
    bitcoin_tweets = [
        "Bitcoin is breaking resistance at $70k! BTC to the moon!",
        "Just bought more Bitcoin. BTC is the future of money.",
        "Bitcoin analysis: Strong support at $65k level."
    ]
    
    print(f"测试Bitcoin项目的3条推文是否使用相同project_id...")
    
    entity_ids = []
    for i, text in enumerate(bitcoin_tweets, 1):
        try:
            tweet = Tweet(
                id_str=f"bitcoin_test_{i}",
                full_text=text,
                created_at_datetime=datetime.now(),
                is_valid=True
            )
            
            # 分析实体
            entity_info = tweet_enricher._analyze_entity_with_keywords(text)  # 使用关键词模式确保一致性
            
            if entity_info and entity_info.get('type') == 'project':
                entity_id = tweet_enricher._handle_project_entity(
                    entity_info['name'], 
                    entity_info.get('brief', ''), 
                    tweet.id_str
                )
                entity_ids.append(entity_id)
                print(f"  推文{i}: {entity_id}")
            
        except Exception as e:
            print(f"  推文{i}处理失败: {e}")
    
    # 检查所有entity_id是否相同
    if len(entity_ids) >= 2 and len(set(entity_ids)) == 1:
        print("✅ 同一项目使用相同ID测试通过")
        return True
    else:
        print("❌ 同一项目使用相同ID测试失败")
        print(f"   得到的entity_ids: {entity_ids}")
        return False


def test_full_enrichment_flow():
    """测试完整的推文增强流程"""
    print("\n🔄 测试完整推文增强流程")
    
    # 创建测试推文
    test_tweet = Tweet(
        id_str="full_entity_test_001",
        full_text="Ethereum DeFi ecosystem is booming! New protocols launching daily with innovative yield farming strategies.",
        created_at_datetime=datetime.now()
    )
    
    # 用户数据映射
    user_data_map = {
        "full_entity_test_001": {
            "id_str": "test_user_123",
            "screen_name": "crypto_analyst",
            "name": "Crypto Analyst"
        }
    }
    
    try:
        print(f"原始推文: {test_tweet.full_text}")
        print(f"初始entity_id: {test_tweet.entity_id}")
        
        # 执行完整增强
        enriched_tweet = tweet_enricher.enrich_single_tweet(test_tweet, user_data_map)
        
        if enriched_tweet:
            print(f"\n✅ 完整增强成功!")
            print(f"KOL ID: {enriched_tweet.kol_id}")
            print(f"Is Valid: {enriched_tweet.is_valid}")
            print(f"Sentiment: {enriched_tweet.sentiment}")
            print(f"Entity ID: {enriched_tweet.entity_id}")
            
            # 验证entity_id格式
            if enriched_tweet.entity_id:
                if enriched_tweet.entity_id.startswith('topic_') or enriched_tweet.entity_id.startswith('project_'):
                    print("✅ Entity ID格式正确")
                    return True
                else:
                    print(f"❌ Entity ID格式错误: {enriched_tweet.entity_id}")
                    return False
            else:
                print("❌ 未生成Entity ID")
                return False
        else:
            print("❌ 完整增强失败")
            return False
            
    except Exception as e:
        print(f"❌ 完整增强流程出错: {e}")
        return False


def main():
    """主函数"""
    print("🎯 推文entity_id智能处理逻辑测试")
    
    # 测试实体分析
    if test_entity_analysis():
        print("\n✅ 实体分析测试通过")
    else:
        print("\n❌ 实体分析测试失败")
        return
    
    # 测试同一实体相同ID
    if test_same_entity_same_id():
        print("\n✅ 同一实体相同ID测试通过")
    else:
        print("\n❌ 同一实体相同ID测试失败")
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
✅ 智能实体识别：AI+关键词双重识别机制
✅ 话题vs项目：准确区分讨论话题和具体项目
✅ ID格式规范：topic_xxx 和 project_xxx 格式
✅ 一致性保证：同一实体使用相同ID
✅ 数据规范化：项目和话题名称标准化

=== 实现特点 ===
- AI优先分析：使用ChatGPT智能判断
- 关键词备选：AI失败时使用关键词匹配
- 名称规范化：确保同一实体使用标准名称
- 数据库集成：自动创建和关联话题/项目记录
- 向下兼容：保持原有topic系统兼容性
    """)


if __name__ == '__main__':
    main()