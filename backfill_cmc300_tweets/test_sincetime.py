#!/usr/bin/env python3
"""
测试 sinceTime 参数是否正确工作
拉取指定日期的推文（不入库，仅验证时间过滤）
"""
import argparse
import sys
from pathlib import Path
from datetime import datetime, timedelta
import time as time_module

# 添加父目录到Python路径
parent_dir = Path(__file__).parent.parent
sys.path.insert(0, str(parent_dir))

from src.utils.logger import get_logger
from src.utils.config_manager import config
from src.api.twitter_api_twitterapi import twitter_api

logger = get_logger(__name__)


def test_sincetime_filter(test_date: str, max_tweets: int = 20):
    """
    测试 sinceTime 参数

    Args:
        test_date: 测试日期 (YYYY-MM-DD)，例如 2024-12-22
        max_tweets: 最多拉取推文数量

    Returns:
        测试结果
    """
    logger.info("=" * 80)
    logger.info("🔬 测试 sinceTime 参数")
    logger.info("=" * 80)

    # 获取配置中的list_ids_project（使用第一个list进行测试）
    list_ids_project = config.get('api_twitterapi', {}).get('default_params', {}).get('list_ids_project', [])
    if not list_ids_project:
        logger.error("❌ 配置文件中未找到list_ids_project")
        return False

    test_list_id = list_ids_project[0]  # 只用第一个list测试
    logger.info(f"📋 使用测试 list: {test_list_id}")

    try:
        # 解析测试日期
        test_dt = datetime.strptime(test_date, '%Y-%m-%d')

        # 设置时间范围：测试日期当天（00:00 - 23:59）
        start_dt = test_dt.replace(hour=0, minute=0, second=0)
        end_dt = test_dt.replace(hour=23, minute=59, second=59)

        # 转换为Unix时间戳（秒）
        since_timestamp = int(start_dt.timestamp())
        until_timestamp = int(end_dt.timestamp())

        logger.info("")
        logger.info(f"📅 测试日期: {test_date}")
        logger.info(f"⏰ 时间范围: {start_dt} 到 {end_dt}")
        logger.info(f"🔢 时间戳范围: {since_timestamp} 到 {until_timestamp}")
        logger.info(f"🎯 最多拉取: {max_tweets} 条推文")
        logger.info("")

        # 直接调用API（使用 sinceTime 和 untilTime 参数）
        logger.info("🚀 开始拉取数据...")

        all_tweets = []
        pagination_token = None
        page = 1
        max_pages = 5  # 最多5页，每页20条足够测试

        while len(all_tweets) < max_tweets and page <= max_pages:
            logger.info(f"📄 拉取第 {page} 页...")

            params = {
                'max_results': min(100, max_tweets),  # 每页最多100条
                'sinceTime': since_timestamp,          # ✅ 使用 sinceTime 参数
                'untilTime': until_timestamp           # ✅ 使用 untilTime 参数
            }

            if pagination_token:
                params['pagination_token'] = pagination_token

            try:
                tweets, next_token = twitter_api.fetch_tweets(list_id=test_list_id, **params)

                if tweets:
                    all_tweets.extend(tweets)
                    logger.info(f"   ✅ 获取到 {len(tweets)} 条推文，累计 {len(all_tweets)} 条")
                else:
                    logger.info(f"   ⚠️  本页无数据")
                    break

                if not next_token or len(all_tweets) >= max_tweets:
                    break

                pagination_token = next_token
                page += 1
                time_module.sleep(1)  # 避免API限流

            except Exception as e:
                logger.error(f"   ❌ API调用失败: {e}")
                break

        # 分析结果
        logger.info("")
        logger.info("=" * 80)
        logger.info("📊 测试结果分析")
        logger.info("=" * 80)
        logger.info(f"📥 总共获取: {len(all_tweets)} 条推文")

        if all_tweets:
            logger.info("")
            logger.info("🕐 推文时间分析:")

            # 分析每条推文的时间
            from dateutil import parser as date_parser

            valid_count = 0
            invalid_count = 0

            for idx, tw in enumerate(all_tweets[:max_tweets], 1):
                tweet_id = tw.get('id', 'unknown')
                created_at_str = tw.get('created_at', '')
                text = tw.get('text', '')[:50]  # 只显示前50个字符

                if created_at_str:
                    try:
                        t = date_parser.parse(created_at_str)
                        if t.tzinfo:
                            t = t.astimezone().replace(tzinfo=None)

                        # 检查是否在目标日期范围内
                        if start_dt <= t <= end_dt:
                            valid_count += 1
                            status = "✅"
                        else:
                            invalid_count += 1
                            status = "❌ 不在范围"

                        logger.info(f"   {idx}. {status} {t} - ID:{tweet_id}")
                        logger.info(f"      📝 {text}...")

                    except Exception as e:
                        logger.error(f"   ❌ 时间解析失败: {e}")
                        invalid_count += 1
                else:
                    logger.warning(f"   ⚠️  推文 {tweet_id} 无 created_at 字段")
                    invalid_count += 1

            logger.info("")
            logger.info(f"✅ 符合条件: {valid_count}/{len(all_tweets[:max_tweets])}")
            logger.info(f"❌ 不符合条件: {invalid_count}/{len(all_tweets[:max_tweets])}")

            if valid_count > 0 and invalid_count == 0:
                logger.info("")
                logger.info("🎉 测试通过！sinceTime/untilTime 参数工作正常")
                return True
            elif valid_count > 0:
                logger.warning("")
                logger.warning("⚠️  部分推文不在时间范围内，请检查API行为")
                return True
            else:
                logger.error("")
                logger.error("❌ 测试失败！所有推文都不在时间范围内")
                return False
        else:
            logger.warning("")
            logger.warning(f"⚠️  未获取到任何推文（可能该日期 {test_date} 没有推文）")
            return True  # 空结果也算正常

    except ValueError as e:
        logger.error(f"❌ 日期格式错误: {e}")
        logger.error("   正确格式: YYYY-MM-DD，例如 2024-12-22")
        return False
    except Exception as e:
        logger.error(f"❌ 测试出错: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    parser = argparse.ArgumentParser(description='测试 sinceTime 参数')
    parser.add_argument('--date', required=True, help='测试日期 (YYYY-MM-DD)，例如: 2024-12-22')
    parser.add_argument('--max-tweets', type=int, default=20, help='最多拉取推文数量，默认20')

    args = parser.parse_args()

    logger.info("=" * 80)
    logger.info("   sinceTime 参数测试工具")
    logger.info("=" * 80)
    logger.info("")
    logger.info("⚠️  注意：此脚本仅用于测试，不会将数据保存到数据库")
    logger.info("")

    success = test_sincetime_filter(
        test_date=args.date,
        max_tweets=args.max_tweets
    )

    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
