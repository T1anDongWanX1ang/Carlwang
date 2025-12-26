#!/usr/bin/env python3
"""
测试 TwitterAPI 返回的转发推文字段名
"""
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.api.twitter_api_twitterapi import TwitterAPIClient
from src.utils.logger import get_logger
import json

logger = get_logger(__name__)

# 初始化 TwitterAPI 客户端
api_client = TwitterAPIClient()

# 获取一页推文
logger.info("开始获取推文样本...")

# 使用项目列表ID
list_ids = ['1996848536520897010', '1996863048959820198', '1996887049027440697']

for list_id in list_ids[:1]:  # 只测试第一个列表
    logger.info(f"从列表 {list_id} 获取推文...")

    tweets, next_token = api_client.fetch_tweets(
        list_id=list_id,
        max_results=10
    )

    if tweets:
        logger.info(f"获取到 {len(tweets)} 条推文")
        logger.info("")

        # 检查每条推文的字段
        for i, tweet in enumerate(tweets[:3], 1):
            logger.info(f"=== 推文 {i} ===")
            logger.info(f"ID: {tweet.get('id_str', 'N/A')}")
            logger.info(f"Text: {tweet.get('full_text', 'N/A')[:50]}...")
            logger.info(f"is_retweet: {tweet.get('is_retweet', 'N/A')}")

            # 列出所有包含 'retweet' 的字段
            retweet_fields = {k: v for k, v in tweet.items() if 'retweet' in k.lower()}
            if retweet_fields:
                logger.info(f"包含 'retweet' 的字段: {list(retweet_fields.keys())}")
                for k, v in retweet_fields.items():
                    if isinstance(v, dict):
                        logger.info(f"  {k}: {{...}} (字典，长度={len(v)})")
                    elif isinstance(v, bool):
                        logger.info(f"  {k}: {v} (布尔)")
                    else:
                        logger.info(f"  {k}: {type(v).__name__}")
            else:
                logger.info("没有包含 'retweet' 的字段")

            # 检查原始数据中是否有 retweeted_tweet 字段
            logger.info("")
            logger.info("原始推文所有字段名:")
            logger.info(str(list(tweet.keys())[:20]))  # 只显示前20个字段
            logger.info("")
    else:
        logger.warning(f"列表 {list_id} 没有获取到推文")

logger.info("测试完成")
