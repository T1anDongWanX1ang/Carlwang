#!/usr/bin/env python3
"""
测试Token Symbol提取功能
"""
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.utils.token_extractor import token_extractor
from src.api.chatgpt_client import chatgpt_client
from src.utils.logger import get_logger

logger = get_logger(__name__)


def test_token_extractor():
    """测试TokenExtractor的基本功能"""
    logger.info("=" * 50)
    logger.info("测试TokenExtractor基本功能")
    logger.info("=" * 50)

    # 测试1: 查看缓存的symbols数量
    cached_symbols = token_extractor.get_cached_symbols()
    logger.info(f"缓存的symbol数量: {len(cached_symbols)}")
    logger.info(f"前10个symbols: {cached_symbols[:10]}")

    # 测试2: 验证一些已知的symbols
    test_symbols = ['BTC', 'ETH', 'SOL', 'INVALID_TOKEN']
    logger.info(f"\n验证symbols: {test_symbols}")
    for symbol in test_symbols:
        is_valid = token_extractor.is_valid_symbol(symbol)
        logger.info(f"  {symbol}: {'有效' if is_valid else '无效'}")

    # 测试3: 从文本中提取symbols（不使用AI）
    test_texts = [
        "Bitcoin ($BTC) is up 5% today, Ethereum (ETH) also surging!",
        "Looking at $SOL and $AVAX for potential entries",
        "The crypto market is volatile today"
    ]

    logger.info("\n从文本中提取token symbols（规则匹配）:")
    for text in test_texts:
        result = token_extractor.extract_symbols_from_text(text, ai_extracted_symbols=None)
        logger.info(f"  文本: {text[:60]}...")
        logger.info(f"  提取结果: {result}")


def test_chatgpt_extraction():
    """测试ChatGPT的token提取功能"""
    logger.info("\n" + "=" * 50)
    logger.info("测试ChatGPT Token提取功能")
    logger.info("=" * 50)

    test_tweets = [
        "Bitcoin just broke $45k! Bullish on $BTC and Ethereum too.",
        "Discussing the latest developments in Solana and Avalanche ecosystems",
        "GM! Today's focus: analyzing $LINK, $UNI, and $AAVE performance"
    ]

    logger.info("\n使用ChatGPT提取token symbols:")
    for i, tweet in enumerate(test_tweets, 1):
        logger.info(f"\n推文 {i}: {tweet}")
        try:
            symbols = chatgpt_client.extract_token_symbols_from_tweet(tweet)
            if symbols:
                logger.info(f"  ChatGPT提取结果: {symbols}")
                # 验证提取的symbols
                validated = token_extractor.validate_symbols(symbols)
                logger.info(f"  验证后的symbols: {validated}")
            else:
                logger.info("  未能提取到symbols")
        except Exception as e:
            logger.error(f"  提取失败: {e}")


def test_integrated_extraction():
    """测试集成的token提取流程（模拟tweet_enricher的流程）"""
    logger.info("\n" + "=" * 50)
    logger.info("测试集成提取流程")
    logger.info("=" * 50)

    test_tweets = [
        "Just analyzed $BTC chart - looks like we might see a breakout soon. $ETH also showing strength.",
        "Solana ecosystem is growing fast! Many new projects launching on SOL.",
        "Random crypto discussion without specific tokens mentioned"
    ]

    logger.info("\n模拟完整的token提取流程:")
    for i, tweet_text in enumerate(test_tweets, 1):
        logger.info(f"\n推文 {i}: {tweet_text}")
        try:
            # 1. 使用ChatGPT提取
            ai_symbols = chatgpt_client.extract_token_symbols_from_tweet(tweet_text)
            logger.info(f"  步骤1 - AI提取: {ai_symbols}")

            # 2. 使用token_extractor验证和规范化
            token_tag = token_extractor.extract_symbols_from_text(tweet_text, ai_symbols)
            logger.info(f"  步骤2 - 最终结果: {token_tag}")

        except Exception as e:
            logger.error(f"  提取失败: {e}")


def main():
    """主测试函数"""
    logger.info("开始测试Token提取功能\n")

    try:
        # 测试1: TokenExtractor基本功能
        test_token_extractor()

        # 测试2: ChatGPT提取功能（需要API key）
        # 注意：这会消耗ChatGPT API配额
        # test_chatgpt_extraction()

        # 测试3: 集成提取流程（需要API key）
        # test_integrated_extraction()

        logger.info("\n" + "=" * 50)
        logger.info("测试完成！")
        logger.info("=" * 50)
        logger.info("\n注意：ChatGPT相关测试已注释掉，如需测试请取消注释")
        logger.info("如果要测试完整功能，请取消注释 test_chatgpt_extraction() 和 test_integrated_extraction()")

    except Exception as e:
        logger.error(f"测试失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
