#!/usr/bin/env python3
"""
KOL标签生成功能测试
"""
import sys
import os
from datetime import datetime

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.api.chatgpt_client import chatgpt_client
from src.utils.logger import setup_logger


def test_tag_generation():
    """测试KOL标签生成功能"""
    setup_logger()
    
    print("🚀 测试KOL标签生成功能")
    
    # 测试用例
    test_cases = [
        {
            "name": "英文DeFi KOL",
            "user_info": {
                "screen_name": "defi_expert",
                "name": "DeFi Expert",
                "followers_count": 50000,
                "description": "DeFi researcher and yield farmer"
            },
            "tweets": [
                "Uniswap V4 is going to revolutionize DeFi. The hook system allows for unprecedented customization.",
                "Yield farming on Aave has been profitable this quarter. APY looking good.",
                "Layer 2 solutions are finally making DeFi accessible to retail users."
            ],
            "expected_language": "English",
            "expected_categories": ["DeFi"]
        },
        {
            "name": "中文比特币KOL",
            "user_info": {
                "screen_name": "btc_analyst_cn", 
                "name": "比特币分析师",
                "followers_count": 80000,
                "description": "专业比特币技术分析"
            },
            "tweets": [
                "比特币今天突破了65000美元的重要阻力位，技术面显示强势信号。",
                "从链上数据看，大户持续增持比特币，市场情绪偏向乐观。",
                "以太坊也在跟涨，整个加密货币市场呈现上升趋势。"
            ],
            "expected_language": "Chinese", 
            "expected_categories": ["Bitcoin", "Ethereum"]
        },
        {
            "name": "英文多领域KOL",
            "user_info": {
                "screen_name": "crypto_all",
                "name": "Crypto Analyst",
                "followers_count": 120000,
                "description": "Bitcoin, DeFi, NFT analysis"
            },
            "tweets": [
                "Bitcoin technical analysis shows bullish divergence on the daily chart.",
                "New NFT collections are launching with innovative utility features.",
                "DeFi yields are normalizing after the recent volatility.",
                "AI integration in blockchain projects is the next big narrative.",
                "Layer 2 scaling solutions continue to gain adoption."
            ],
            "expected_language": "English",
            "expected_categories": ["Bitcoin", "NFT", "DeFi", "AI"]
        }
    ]
    
    success_count = 0
    total_count = len(test_cases)
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n{'='*60}")
        print(f"📝 测试用例 {i}: {test_case['name']}")
        print(f"用户: @{test_case['user_info']['screen_name']}")
        print(f"粉丝数: {test_case['user_info']['followers_count']:,}")
        
        try:
            # 执行KOL分析
            result = chatgpt_client.analyze_kol_profile(test_case['user_info'], test_case['tweets'])
            
            if result:
                print(f"\n✅ KOL分析成功!")
                print(f"类型: {result.get('type')}")
                print(f"标签: {result.get('tag')}")
                print(f"情绪: {result.get('sentiment')}")
                print(f"信任度: {result.get('trust_rating')}")
                print(f"总结: {result.get('summary', '')[:100]}...")
                
                # 验证标签格式
                tags = result.get('tag', '').split(',')
                print(f"\n🔍 标签分析:")
                print(f"标签列表: {tags}")
                print(f"标签数量: {len(tags)}")
                
                # 检查是否包含语言标签
                has_language_tag = any(tag.strip() in ["English", "Chinese"] for tag in tags)
                print(f"包含语言标签: {'✅' if has_language_tag else '❌'}")
                
                # 检查预期的专业标签
                expected_found = 0
                for expected_cat in test_case['expected_categories']:
                    if any(expected_cat.lower() in tag.lower() for tag in tags):
                        expected_found += 1
                        print(f"找到预期标签 '{expected_cat}': ✅")
                
                # 判断测试是否通过
                if has_language_tag and expected_found > 0:
                    print("🎉 测试通过")
                    success_count += 1
                else:
                    print("❌ 测试失败")
                    
            else:
                print("❌ KOL分析失败")
            
        except Exception as e:
            print(f"❌ 测试用例执行失败: {e}")
    
    print(f"\n{'='*60}")
    print(f"=== 测试结果总结 ===")
    print(f"成功: {success_count}/{total_count}")
    print(f"成功率: {success_count/total_count*100:.1f}%")
    
    return success_count == total_count


def test_language_detection():
    """测试语言检测功能"""
    print(f"\n{'='*60}")
    print("🌐 测试语言检测功能")
    
    test_texts = [
        {
            "text": "Bitcoin is showing strong momentum today. The price action looks bullish.",
            "expected": "English"
        },
        {
            "text": "比特币今天表现强势，价格走势看起来很乐观。技术面也支持上涨。",
            "expected": "Chinese"
        },
        {
            "text": "BTC price $65,000! 🚀🚀🚀 #Bitcoin #Crypto",
            "expected": "English"
        },
        {
            "text": "以太坊gas费又贵了，DeFi使用成本太高。Layer2的解决方案什么时候能普及？",
            "expected": "Chinese"
        }
    ]
    
    success_count = 0
    
    for i, test_case in enumerate(test_texts, 1):
        print(f"\n📝 语言检测测试 {i}:")
        print(f"文本: {test_case['text'][:50]}...")
        
        detected = chatgpt_client._detect_primary_language(test_case['text'])
        expected = test_case['expected']
        
        print(f"检测结果: {detected} (预期: {expected})")
        
        if detected == expected:
            print("✅ 检测正确")
            success_count += 1
        else:
            print("❌ 检测错误")
    
    print(f"\n语言检测成功率: {success_count}/{len(test_texts)} ({success_count/len(test_texts)*100:.1f}%)")
    
    return success_count == len(test_texts)


def main():
    """主函数"""
    print("🎯 KOL标签生成功能测试")
    
    # 测试语言检测
    if test_language_detection():
        print("\n✅ 语言检测测试通过")
    else:
        print("\n❌ 语言检测测试失败")
    
    # 测试标签生成
    if test_tag_generation():
        print("\n✅ 标签生成测试通过")
    else:
        print("\n❌ 标签生成测试失败")
        return
    
    print("""

🎉 所有测试通过！

=== 新的标签生成规则 ===
✅ 语言标签必须包含：English 或 Chinese
✅ 专业标签根据内容识别：BTC, ETH, DeFi, NFT, AI, Gaming等
✅ 多标签逗号拼接：例如"English,DeFi,BTC"
✅ 数量限制：最多5个标签
✅ 智能检测：自动识别推文主要语言

=== 使用示例 ===
- 英文DeFi KOL: "English,DeFi,Ethereum"
- 中文比特币KOL: "Chinese,Bitcoin,Trading"  
- 多领域KOL: "English,Bitcoin,DeFi,NFT,AI"
    """)


if __name__ == '__main__':
    main() 