#!/usr/bin/env python3
"""
测试活动数据提取和JSON结构化功能
"""
import sys
import json
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.api.chatgpt_client import chatgpt_client
from src.utils.logger import get_logger


def test_activity_extraction():
    """测试活动数据提取"""
    logger = get_logger(__name__)

    logger.info("=" * 60)
    logger.info("测试活动数据提取和JSON结构化功能")
    logger.info("=" * 60)

    # 测试推文示例
    test_tweet = """
    🎁 BIG AIRDROP ALERT! 🎁

    Join our exclusive campaign and win $10,000 in $TOKEN rewards!

    How to participate:
    ✅ Follow @ProjectX
    ✅ Retweet & Like this post
    ✅ Join our Discord: discord.gg/projectx
    ✅ Complete KYC on our platform

    Campaign ends: Dec 31, 2024
    Winners announced: Jan 5, 2025

    Don't miss out! 🚀
    """

    test_url = "https://twitter.com/projectx/status/1234567890"
    test_time = "2024-12-01 10:00:00"

    logger.info("\n测试推文内容:")
    logger.info(test_tweet)
    logger.info("")

    # 1. 测试活动检测
    logger.info("步骤 1: 检测是否为活动推文...")
    is_activity = chatgpt_client.detect_campaign_announcement([test_tweet])
    logger.info(f"结果: {'是活动推文' if is_activity else '非活动推文'}")

    if is_activity:
        # 2. 测试结构化数据提取
        logger.info("\n步骤 2: 提取结构化数据...")
        activity_data = chatgpt_client.extract_activity_structured_data(
            tweet_text=test_tweet,
            tweet_url=test_url,
            tweet_time=test_time
        )

        if activity_data:
            logger.info("✓ 成功提取结构化数据")
            logger.info("\n提取的JSON数据:")
            logger.info(json.dumps(activity_data, indent=2, ensure_ascii=False))

            # 验证字段
            logger.info("\n字段验证:")
            required_fields = ['title', 'status', 'summary', 'time', 'url']
            for field in required_fields:
                if field in activity_data:
                    logger.info(f"  ✓ {field}: {activity_data[field]}")
                else:
                    logger.error(f"  ✗ 缺少字段: {field}")

            logger.info("\n=" * 60)
            logger.info("测试成功！")
            logger.info("=" * 60)
            return True
        else:
            logger.error("✗ 无法提取结构化数据")
            return False
    else:
        logger.warning("推文未被识别为活动，测试终止")
        return False


if __name__ == '__main__':
    success = test_activity_extraction()
    sys.exit(0 if success else 1)
