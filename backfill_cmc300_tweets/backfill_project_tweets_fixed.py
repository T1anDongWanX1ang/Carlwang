#!/usr/bin/env python3
"""
项目推文回填脚本（CMC300）- 修复版
一次性拉取指定日期范围的数据，避免重复API调用
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
from src.database.tweet_dao import tweet_dao

logger = get_logger(__name__)


def backfill_once(start_date: str, max_pages: int = 200, page_size: int = 100):
    """
    一次性回填项目推文数据（推荐方式）

    从start_date到现在的所有数据一次性拉取，避免重复API调用

    Args:
        start_date: 开始日期 (YYYY-MM-DD)，例如 "2024-12-22"
        max_pages: 总最大页数，默认200页
        page_size: 每页大小，默认100条

    Returns:
        是否成功
    """
    logger.info("=" * 80)
    logger.info("🔄 开始项目推文回填（一次性拉取模式）")
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
        # 计算时间范围
        start = datetime.strptime(start_date, '%Y-%m-%d')
        now = datetime.now()
        days = (now - start).days + 1
        hours_limit = days * 24

        logger.info("")
        logger.info(f"📅 回填日期范围: {start_date} 到 {now.strftime('%Y-%m-%d')}")
        logger.info(f"⏰ 时间窗口: {hours_limit}小时 ({days}天)")
        logger.info(f"🔢 最多拉取{max_pages}页，每页{page_size}条")
        logger.info(f"💡 一次性拉取，数据库自动去重")
        logger.info("")

        # 一次性执行项目推文爬取
        logger.info("🚀 开始拉取数据...")
        success = crawler.crawl_project_tweets(
            max_pages=max_pages,
            page_size=page_size,
            hours_limit=hours_limit
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
            logger.info(f"📅 日期范围: {start_date} 到 {now.strftime('%Y-%m-%d')} ({days}天)")
            logger.info(f"📝 保存推文数: {stats.get('database_tweet_count', 0)}条")
            logger.info(f"🔗 API调用次数: {api_stats.get('total_requests', 0)}次")
            logger.info(f"📥 API获取推文: {api_stats.get('tweets_fetched', 0)}条")
            logger.info(f"✔️  成功率: {api_stats.get('success_rate', 0):.2f}%")
            logger.info(f"💰 总成本: ${api_stats.get('total_cost_usd', 0):.4f} USD")
            logger.info(f"📈 平均每条成本: ${api_stats.get('total_cost_usd', 0) / max(stats.get('database_tweet_count', 1), 1):.6f} USD")
        else:
            logger.error(f"❌ 回填失败")

        logger.info("=" * 80)

        return success

    except ValueError as e:
        logger.error(f"❌ 日期格式错误: {e}")
        logger.error("   正确格式: YYYY-MM-DD，例如 2024-12-22")
        return False
    except Exception as e:
        logger.error(f"❌ 回填出错: {e}")
        import traceback
        traceback.print_exc()
        return False


def backfill_by_date_range(start_date: str, end_date: str = None, max_pages: int = 200, page_size: int = 100):
    """
    按日期范围回填（内部调用一次性拉取）

    Args:
        start_date: 开始日期 (YYYY-MM-DD)
        end_date: 结束日期 (YYYY-MM-DD)，不指定则默认到今天
        max_pages: 总最大页数
        page_size: 每页大小

    Returns:
        是否成功
    """
    if end_date:
        logger.info(f"🗓️  按日期范围回填: {start_date} 到 {end_date}")
        # 验证日期范围
        try:
            start = datetime.strptime(start_date, '%Y-%m-%d')
            end = datetime.strptime(end_date, '%Y-%m-%d')
            if start > end:
                logger.error("❌ 开始日期不能晚于结束日期")
                return False
            if end > datetime.now():
                logger.warning(f"⚠️  结束日期 {end_date} 晚于今天，将使用今天作为结束日期")
        except ValueError as e:
            logger.error(f"❌ 日期格式错误: {e}")
            return False

    # 调用一次性拉取
    return backfill_once(start_date, max_pages, page_size)


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description='项目推文回填脚本（CMC300）- 修复版',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例：
  # 补充12月22日到今天的数据（推荐）
  %(prog)s --start-date 2024-12-22

  # 指定最大页数
  %(prog)s --start-date 2024-12-22 --max-pages 300

  # 指定日期范围
  %(prog)s --start-date 2024-12-22 --end-date 2024-12-28
        """
    )

    parser.add_argument('--start-date', type=str, required=True,
                       help='开始日期 (YYYY-MM-DD)，例如 2024-12-22')
    parser.add_argument('--end-date', type=str,
                       help='结束日期 (YYYY-MM-DD)，不指定则默认到今天')
    parser.add_argument('--max-pages', type=int, default=200,
                       help='总最大页数，默认200页（约可拉取4000条推文）')
    parser.add_argument('--page-size', type=int, default=100,
                       help='每页大小，默认100条')

    args = parser.parse_args()

    try:
        logger.info("=" * 80)
        logger.info("项目推文回填工具 - 修复版")
        logger.info("=" * 80)
        logger.info(f"⚡ 使用一次性拉取模式，避免重复API调用")
        logger.info("")

        # 执行回填
        if args.end_date:
            success = backfill_by_date_range(
                args.start_date,
                args.end_date,
                args.max_pages,
                args.page_size
            )
        else:
            success = backfill_once(
                args.start_date,
                args.max_pages,
                args.page_size
            )

        if success:
            logger.info("")
            logger.info("✅ 回填任务完成")
            sys.exit(0)
        else:
            logger.error("")
            logger.error("❌ 回填任务失败")
            sys.exit(1)

    except KeyboardInterrupt:
        logger.info("\n⚠️  接收到中断信号，停止回填...")
        sys.exit(1)
    except Exception as e:
        logger.error(f"❌ 回填出错: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        # 清理资源
        try:
            crawler.close()
        except:
            pass


if __name__ == '__main__':
    main()
