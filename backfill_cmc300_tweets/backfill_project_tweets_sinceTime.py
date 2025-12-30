#!/usr/bin/env python3
"""
项目推文回填脚本（使用API的sinceTime参数）
使用TwitterAPI的sinceTime/untilTime参数进行服务端时间过滤
"""
import argparse
import sys
from pathlib import Path
from datetime import datetime, timedelta
import time as time_module

# 添加父目录到Python路径
parent_dir = Path(__file__).parent.parent
sys.path.insert(0, str(parent_dir))

from src.crawler import crawler
from src.utils.logger import get_logger
from src.utils.config_manager import config
from src.database.tweet_dao import tweet_dao

logger = get_logger(__name__)


def backfill_with_sinceTime(start_date: str, end_date: str = None, max_pages: int = 200, page_size: int = 100):
    """
    使用sinceTime参数回填项目推文数据

    Args:
        start_date: 开始日期 (YYYY-MM-DD)
        end_date: 结束日期 (YYYY-MM-DD)，默认为今天
        max_pages: 最大页数
        page_size: 每页大小

    Returns:
        是否成功
    """
    logger.info("=" * 80)
    logger.info("🔄 开始项目推文回填（使用API sinceTime参数）")
    logger.info("=" * 80)

    # 设置使用项目推文专用表
    tweet_dao.table_name = 'twitter_tweet_back_test_cmc300'
    logger.info(f"使用数据表: {tweet_dao.table_name}")

    # 获取配置中的list_ids_project
    list_ids_project = config.get('api_twitterapi', {}).get('default_params', {}).get('list_ids_project', [])
    if not list_ids_project:
        logger.error("配置文件中未找到list_ids_project")
        return False

    logger.info(f"📋 将回填以下{len(list_ids_project)}个项目list:")
    for i, list_id in enumerate(list_ids_project, 1):
        logger.info(f"   {i}. {list_id}")

    try:
        # 解析日期
        start_dt = datetime.strptime(start_date, '%Y-%m-%d')
        if end_date:
            end_dt = datetime.strptime(end_date, '%Y-%m-%d')
        else:
            end_dt = datetime.now()

        # 转换为Unix时间戳（秒）
        since_timestamp = int(start_dt.timestamp())
        until_timestamp = int(end_dt.timestamp())

        days = (end_dt - start_dt).days + 1

        logger.info("")
        logger.info(f"📅 回填日期范围: {start_date} 到 {end_dt.strftime('%Y-%m-%d')}")
        logger.info(f"⏰ 时间戳范围: {since_timestamp} 到 {until_timestamp}")
        logger.info(f"📆 时间跨度: {days} 天")
        logger.info(f"🔢 最多拉取{max_pages}页，每页{page_size}条")
        logger.info(f"💡 使用API的sinceTime参数进行服务端过滤")
        logger.info("")

        # 修改API客户端，添加sinceTime参数
        from src.api.twitter_api_twitterapi import twitter_api

        # 保存原始的fetch_tweets方法
        original_fetch_tweets = twitter_api.fetch_tweets

        def fetch_tweets_with_time_filter(list_id=None, **kwargs):
            """包装fetch_tweets，自动添加sinceTime/untilTime参数"""
            # 添加时间过滤参数
            kwargs['sinceTime'] = since_timestamp
            kwargs['untilTime'] = until_timestamp
            return original_fetch_tweets(list_id=list_id, **kwargs)

        # 临时替换方法
        twitter_api.fetch_tweets = fetch_tweets_with_time_filter

        try:
            logger.info("🚀 开始拉取数据...")
            success = crawler.crawl_project_tweets(
                max_pages=max_pages,
                page_size=page_size,
                hours_limit=days * 24  # 保留hours_limit参数以兼容现有代码
            )

            # 获取统计信息
            stats = crawler.get_statistics()
            api_stats = stats.get('api_stats', {})

            logger.info("")
            logger.info("=" * 80)
            logger.info("📊 回填完成统计")
            logger.info("=" * 80)

            if success:
                logger.info(f"✅ 回填成功")
                logger.info(f"📅 日期范围: {start_date} 到 {end_dt.strftime('%Y-%m-%d')} ({days}天)")
                logger.info(f"📝 保存推文数: {stats.get('database_tweet_count', 0)}条")
                logger.info(f"🔗 API调用次数: {api_stats.get('total_requests', 0)}次")
                logger.info(f"📥 API获取推文: {api_stats.get('tweets_fetched', 0)}条")
                logger.info(f"✔️  成功率: {api_stats.get('success_rate', 0):.2f}%")
                logger.info(f"💰 总成本: ${api_stats.get('total_cost_usd', 0):.4f} USD")
                if stats.get('database_tweet_count', 0) > 0:
                    logger.info(f"📈 平均每条成本: ${api_stats.get('total_cost_usd', 0) / max(stats.get('database_tweet_count', 1), 1):.6f} USD")
            else:
                logger.error(f"❌ 回填失败")

            logger.info("=" * 80)

            return success

        finally:
            # 恢复原始方法
            twitter_api.fetch_tweets = original_fetch_tweets

    except ValueError as e:
        logger.error(f"❌ 日期格式错误: {e}")
        logger.error("   正确格式: YYYY-MM-DD，例如 2025-12-22")
        return False
    except Exception as e:
        logger.error(f"❌ 回填出错: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    parser = argparse.ArgumentParser(description='项目推文回填工具（使用sinceTime参数）')
    parser.add_argument('--start-date', required=True, help='开始日期 (YYYY-MM-DD)，例如: 2025-12-22')
    parser.add_argument('--end-date', help='结束日期 (YYYY-MM-DD)，默认为今天')
    parser.add_argument('--max-pages', type=int, default=200, help='最大页数，默认200')
    parser.add_argument('--page-size', type=int, default=100, help='每页大小，默认100')

    args = parser.parse_args()

    logger.info("=" * 80)
    logger.info("   项目推文回填工具 (CMC300) - sinceTime版")
    logger.info("=" * 80)
    logger.info("")
    logger.info(f"⚡ 使用API的sinceTime参数进行服务端时间过滤")
    logger.info(f"⚡ 只会拉取指定时间范围内的推文，不会浪费API成本")
    logger.info("")

    success = backfill_with_sinceTime(
        start_date=args.start_date,
        end_date=args.end_date,
        max_pages=args.max_pages,
        page_size=args.page_size
    )

    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
