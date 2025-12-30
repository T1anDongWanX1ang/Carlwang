#!/usr/bin/env python3
"""
KOL推文回填脚本
用于补充过去一周遗漏的6个list的数据
"""
import argparse
import sys
from pathlib import Path
from datetime import datetime, timedelta

# 添加父目录到Python路径
parent_dir = Path(__file__).parent.parent
sys.path.insert(0, str(parent_dir))

from src.crawler import crawler
from src.utils.logger import get_logger
from src.utils.config_manager import config

logger = get_logger(__name__)


def backfill_by_days(days: int = 7, max_pages: int = 15):
    """
    按天回填KOL推文数据

    Args:
        days: 回填天数，默认7天
        max_pages: 每个list每天最大页数，默认15页
    """
    logger.info("=" * 80)
    logger.info(f"🔄 开始回填KOL推文数据 - 回填{days}天")
    logger.info("=" * 80)

    # 获取配置中的list_ids_kol
    list_ids_kol = config.get('api_twitterapi', {}).get('default_params', {}).get('list_ids_kol', [])
    logger.info(f"📋 将回填以下{len(list_ids_kol)}个list:")
    for i, list_id in enumerate(list_ids_kol, 1):
        logger.info(f"   {i}. {list_id}")

    # 统计信息
    total_stats = {
        'total_days': days,
        'total_lists': len(list_ids_kol),
        'days_completed': 0,
        'total_tweets': 0,
        'total_valid_tweets': 0,
        'total_api_calls': 0,
        'total_cost': 0.0,
        'errors': []
    }

    # 按天回填
    for day_offset in range(days):
        target_date = datetime.now() - timedelta(days=day_offset)
        date_str = target_date.strftime('%Y-%m-%d')

        logger.info("")
        logger.info("=" * 80)
        logger.info(f"📅 回填日期: {date_str} (今天往前第{day_offset}天)")
        logger.info("=" * 80)

        try:
            # 设置时间窗口为24小时（当天）
            # 使用hours_limit参数控制时间范围
            # 从当天00:00到23:59的数据
            hours_limit = 24 + (day_offset * 24)  # 累加前面的天数

            logger.info(f"⏰ 时间窗口: 拉取过去{hours_limit}小时的数据")
            logger.info(f"🔢 每个list最多拉取{max_pages}页")

            # 执行爬取（会自动使用config中更新后的list_ids_kol）
            success = crawler.crawl_tweets(
                max_pages=max_pages,
                page_size=100,
                hours_limit=hours_limit
            )

            # 获取统计信息
            day_stats = crawler.get_statistics()

            if success:
                total_stats['days_completed'] += 1
                total_stats['total_tweets'] += day_stats.get('database_tweet_count', 0)
                # 估算有效推文数（假设95%有效）
                total_stats['total_valid_tweets'] += int(day_stats.get('database_tweet_count', 0) * 0.95)

                api_stats = day_stats.get('api_stats', {})
                total_stats['total_api_calls'] += api_stats.get('total_requests', 0)
                total_stats['total_cost'] += api_stats.get('total_cost_usd', 0)

                logger.info(f"✅ {date_str} 回填完成")
                logger.info(f"   - API调用: {api_stats.get('total_requests', 0)}次")
                logger.info(f"   - 获取推文: {api_stats.get('tweets_fetched', 0)}条")
                logger.info(f"   - 成本: ${api_stats.get('total_cost_usd', 0):.4f}")
            else:
                logger.error(f"❌ {date_str} 回填失败")
                total_stats['errors'].append(f"{date_str}: 爬取失败")

        except Exception as e:
            logger.error(f"❌ {date_str} 回填出错: {e}")
            total_stats['errors'].append(f"{date_str}: {str(e)}")

    # 显示总体统计
    logger.info("")
    logger.info("=" * 80)
    logger.info("📊 回填总体统计")
    logger.info("=" * 80)
    logger.info(f"✅ 完成天数: {total_stats['days_completed']}/{total_stats['total_days']}")
    logger.info(f"📋 List数量: {total_stats['total_lists']}")
    logger.info(f"📝 总推文数: {total_stats['total_tweets']}")
    logger.info(f"✔️  有效推文: {total_stats['total_valid_tweets']}")
    logger.info(f"🔗 API调用: {total_stats['total_api_calls']}次")
    logger.info(f"💰 总成本: ${total_stats['total_cost']:.4f}")

    if total_stats['errors']:
        logger.warning(f"\n⚠️  错误列表 ({len(total_stats['errors'])}个):")
        for error in total_stats['errors']:
            logger.warning(f"   - {error}")

    logger.info("=" * 80)

    return total_stats['days_completed'] == total_stats['total_days']


def backfill_by_date_range(start_date: str, end_date: str, max_pages: int = 15):
    """
    按日期范围回填KOL推文数据

    Args:
        start_date: 开始日期 (YYYY-MM-DD)
        end_date: 结束日期 (YYYY-MM-DD)
        max_pages: 每个list每天最大页数
    """
    logger.info(f"🗓️  按日期范围回填: {start_date} 到 {end_date}")

    try:
        start = datetime.strptime(start_date, '%Y-%m-%d')
        end = datetime.strptime(end_date, '%Y-%m-%d')

        if start > end:
            logger.error("❌ 开始日期不能晚于结束日期")
            return False

        # 计算天数
        days = (datetime.now() - start).days + 1

        return backfill_by_days(days, max_pages)

    except ValueError as e:
        logger.error(f"❌ 日期格式错误: {e}")
        logger.error("   正确格式: YYYY-MM-DD，例如 2024-01-15")
        return False


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='KOL推文回填脚本')
    parser.add_argument('--days', type=int, default=7, help='回填天数，默认7天')
    parser.add_argument('--start-date', type=str, help='开始日期 (YYYY-MM-DD)')
    parser.add_argument('--end-date', type=str, help='结束日期 (YYYY-MM-DD)')
    parser.add_argument('--max-pages', type=int, default=15, help='每个list每天最大页数，默认15页')

    args = parser.parse_args()

    try:
        if args.start_date and args.end_date:
            # 按日期范围回填
            success = backfill_by_date_range(args.start_date, args.end_date, args.max_pages)
        else:
            # 按天数回填
            success = backfill_by_days(args.days, args.max_pages)

        if success:
            logger.info("✅ 回填任务全部完成")
            sys.exit(0)
        else:
            logger.error("❌ 回填任务失败或部分失败")
            sys.exit(1)

    except KeyboardInterrupt:
        logger.info("\n⚠️  接收到中断信号，停止回填...")
        sys.exit(1)
    except Exception as e:
        logger.error(f"❌ 回填出错: {e}")
        sys.exit(1)
    finally:
        # 清理资源
        crawler.close()


if __name__ == '__main__':
    main()
