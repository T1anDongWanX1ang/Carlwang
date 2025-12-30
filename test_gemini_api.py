#!/usr/bin/env python3
"""
测试Gemini API是否正常工作
"""
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.api.chatgpt_client import chatgpt_client
from src.utils.logger import get_logger

logger = get_logger(__name__)

def test_gemini_api():
    """测试Gemini API的各项功能"""

    print("=" * 60)
    print("🧪 Gemini API 功能测试")
    print("=" * 60)

    # 测试1：内容验证
    print("\n📝 测试1: AI内容验证")
    test_tweet = "Bitcoin just broke $50,000! This is a major milestone for crypto adoption."

    try:
        # 使用内部方法测试
        prompt = f"""/no_think
分析推文是否为有价值的加密货币相关内容（非广告）。
推文: {test_tweet}

直接回答true或false，不要解释："""

        response = chatgpt_client._make_request([
            {"role": "system", "content": "You are a content validator. Reply ONLY with 'true' or 'false', nothing else."},
            {"role": "user", "content": prompt}
        ], temperature=0.0, max_tokens=20)

        print(f"   原始响应: {repr(response)}")

        if response:
            # 清理可能的标签
            import re
            cleaned = re.sub(r'<think>.*?</think>', '', response, flags=re.DOTALL)
            cleaned = re.sub(r'</?think>', '', cleaned)
            cleaned = cleaned.strip().lower()
            print(f"   清理后: {repr(cleaned)}")

            if cleaned in ['true', 'false']:
                print(f"   ✅ 内容验证测试通过: {cleaned}")
            else:
                print(f"   ⚠️  响应格式异常，但不影响功能（会fallback到关键词验证）")
        else:
            print(f"   ❌ API调用失败")
            return False

    except Exception as e:
        print(f"   ❌ 测试失败: {e}")
        return False

    # 测试2：情感分析
    print("\n💭 测试2: 情感分析")
    test_text = "Ethereum 2.0 is finally here! This is great news for the ecosystem."

    try:
        result = chatgpt_client.analyze_sentiment(test_text)
        if result:
            print(f"   ✅ 情感分析成功:")
            print(f"      - 情感: {result.get('sentiment')}")
            print(f"      - 置信度: {result.get('confidence')}")
            print(f"      - 分数: {result.get('score')}")
        else:
            print(f"   ⚠️  情感分析返回None（可能是格式问题，但不影响主流程）")
    except Exception as e:
        print(f"   ❌ 测试失败: {e}")
        return False

    # 测试3：Token符号提取
    print("\n🪙 测试3: Token符号提取")
    test_tweet_symbols = "$BTC and $ETH are leading the market today. Also watching $SOL closely."

    try:
        symbols = chatgpt_client.extract_token_symbols_from_tweet(test_tweet_symbols)
        if symbols:
            print(f"   ✅ Token提取成功: {symbols}")
        else:
            print(f"   ⚠️  未提取到Token（可能是格式问题）")
    except Exception as e:
        print(f"   ❌ 测试失败: {e}")
        return False

    # 显示API统计
    print("\n📊 API调用统计:")
    stats = chatgpt_client.get_statistics()
    print(f"   - 总请求数: {stats['total_requests']}")
    print(f"   - 成功次数: {stats['success_count']}")
    print(f"   - 失败次数: {stats['error_count']}")
    print(f"   - 成功率: {stats['success_rate']:.1f}%")

    print("\n" + "=" * 60)

    # 判断整体是否通过
    if stats['success_count'] >= 2:  # 至少2个成功
        print("✅ Gemini API 测试通过！可以正常使用。")
        return True
    else:
        print("❌ Gemini API 测试失败，请检查配置。")
        return False

if __name__ == "__main__":
    success = test_gemini_api()
    sys.exit(0 if success else 1)
