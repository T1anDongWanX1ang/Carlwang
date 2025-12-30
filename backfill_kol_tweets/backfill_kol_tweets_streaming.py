#!/usr/bin/env python3
"""
KOL推文回填脚本 - 流式处理版本
采用边拉边存模式，避免中断导致API浪费
"""
import argparse
import sys
from pathlib import Path
from datetime import datetime, timedelta
import time

# 添加父目录到Python路径
parent_dir = Path(__file__).parent.parent
sys.path.insert(0, str(parent_dir))

from src.utils.logger import get_logger
from src.utils.config_manager import config
from src.api.twitter_api_twitterapi import TwitterAPITwitterAPIClient
from src.utils.data_mapper import DataMapper
from src.utils.tweet_enricher import TweetEnricher
from src.database.tweet_dao import tweet_dao
from src.database.user_dao import user_dao

logger = get_logger(__name__)


class StreamingBackfill:
    """流式回填处理器 - 边拉边存模式"""

    def __init__(self):
        self.logger = logger
        self.api_client = TwitterAPITwitterAPIClient()
        self.data_mapper = DataMapper()
        self.tweet_enricher = TweetEnricher()

        # 统计信息
        self.stats = {
            'total_api_calls': 0,
            'total_tweets_fetched': 0,
            'total_tweets_saved': 0,
            'total_users_saved': 0,
            'total_cost': 0.0,
            'lists_processed': {},
            'errors': []
        }

    def backfill_by_days(self, days: int = 7, list_ids: list = None):
        """
        按天回填，边拉边存模式

        Args:
            days: 回填天数
            list_ids: 要回填的list ID列表
        """
        # 获取list_ids
        if not list_ids:
            list_ids = config.get('api_twitterapi', {}).get('default_params', {}).get('list_ids_kol', [])

        self.logger.info("=" * 80)
        self.logger.info(f"🔄 开始流式回填KOL推文数据 - 回填{days}天")
        self.logger.info("=" * 80)
        self.logger.info(f"📋 将回填以下{len(list_ids)}个list:")
        for i, list_id in enumerate(list_ids, 1):
            self.logger.info(f"   {i}. {list_id}")
        self.logger.info("")
        self.logger.info("✨ 采用边拉边存模式：")
        self.logger.info("   - 拉取1页 → 立即处理并存储 → 拉取下一页")
        self.logger.info("   - 中断后可继续，不会浪费已拉取的数据")
        self.logger.info("   - 根据推文时间自动停止（智能早停）")
        self.logger.info("=" * 80)

        # 计算时间窗口
        time_cutoff = datetime.now() - timedelta(days=days)
        self.logger.info(f"⏰ 时间窗口: {time_cutoff.strftime('%Y-%m-%d %H:%M:%S')} 之后的推文")
        self.logger.info("")

        # 逐个list处理
        for list_idx, list_id in enumerate(list_ids, 1):
            self.logger.info("=" * 80)
            self.logger.info(f"📋 处理 List {list_idx}/{len(list_ids)}: {list_id}")
            self.logger.info("=" * 80)

            try:
                list_stats = self._process_single_list_streaming(
                    list_id=list_id,
                    time_cutoff=time_cutoff
                )

                self.stats['lists_processed'][list_id] = list_stats
                self.logger.info(f"✅ List {list_id} 处理完成")
                self.logger.info(f"   - 拉取推文: {list_stats['tweets_fetched']}条")
                self.logger.info(f"   - 保存推文: {list_stats['tweets_saved']}条")
                self.logger.info(f"   - API调用: {list_stats['api_calls']}次")
                self.logger.info(f"   - 成本: ${list_stats['cost']:.4f}")

            except KeyboardInterrupt:
                self.logger.warning(f"\n⚠️  用户中断！已保存的数据不会丢失。")
                self.logger.info(f"   当前进度: List {list_idx}/{len(list_ids)}")
                raise
            except Exception as e:
                self.logger.error(f"❌ List {list_id} 处理失败: {e}")
                self.stats['errors'].append(f"List {list_id}: {str(e)}")
                continue

            self.logger.info("")

        # 显示总体统计
        self._show_final_stats()

        return len(self.stats['errors']) == 0

    def _process_single_list_streaming(self, list_id: str, time_cutoff: datetime):
        """
        流式处理单个list - 边拉边存

        Args:
            list_id: List ID
            time_cutoff: 时间截止点

        Returns:
            该list的统计信息
        """
        list_stats = {
            'tweets_fetched': 0,
            'tweets_saved': 0,
            'users_saved': 0,
            'api_calls': 0,
            'cost': 0.0,
            'pages_processed': 0
        }

        page = 1
        pagination_token = None
        should_stop = False

        while not should_stop:
            try:
                self.logger.info(f"   📄 拉取第 {page} 页...")

                # 拉取一页数据
                page_data, next_token, page_cost = self._fetch_single_page(
                    list_id=list_id,
                    pagination_token=pagination_token
                )

                list_stats['api_calls'] += 1
                list_stats['cost'] += page_cost
                self.stats['total_api_calls'] += 1
                self.stats['total_cost'] += page_cost

                if not page_data:
                    self.logger.info(f"   ⚠️  第 {page} 页无数据，停止翻页")
                    break

                list_stats['tweets_fetched'] += len(page_data)
                self.stats['total_tweets_fetched'] += len(page_data)

                # 检查最后一条推文时间（智能早停）
                last_tweet = page_data[-1] if page_data else None
                if last_tweet:
                    # 注意：fetch_tweets已经转换格式，字段名是'created_at'而非'createdAt'
                    last_tweet_time_str = last_tweet.get('created_at')
                    if last_tweet_time_str:
                        try:
                            # Twitter日期格式: 'Mon Dec 29 18:54:00 +0000 2025'
                            from datetime import datetime
                            last_tweet_time = datetime.strptime(last_tweet_time_str, '%a %b %d %H:%M:%S %z %Y')
                            # 转为本地时间（移除时区信息）
                            last_tweet_time = last_tweet_time.replace(tzinfo=None)

                            if last_tweet_time < time_cutoff:
                                self.logger.info(f"   ⏱️  智能早停触发：第 {page} 页最后推文时间 "
                                               f"{last_tweet_time.strftime('%Y-%m-%d %H:%M:%S')} "
                                               f"早于截止时间，停止翻页")
                                should_stop = True
                        except Exception as e:
                            self.logger.warning(f"   解析推文时间失败: {e}")

                # 立即处理并存储这一页数据
                saved_count, users_count = self._process_and_save_page(page_data)

                list_stats['tweets_saved'] += saved_count
                list_stats['users_saved'] += users_count
                self.stats['total_tweets_saved'] += saved_count
                self.stats['total_users_saved'] += users_count

                self.logger.info(f"   ✅ 第 {page} 页处理完成: 拉取{len(page_data)}条, 保存{saved_count}条推文, {users_count}个用户")

                list_stats['pages_processed'] += 1

                # 检查是否有下一页
                if not next_token:
                    self.logger.info(f"   ✅ 没有更多数据，停止翻页")
                    break

                # 准备下一页
                pagination_token = next_token
                page += 1

                # 短暂延迟，避免API限流
                time.sleep(0.5)

            except Exception as e:
                self.logger.error(f"   ❌ 第 {page} 页处理失败: {e}")
                self.stats['errors'].append(f"List {list_id} Page {page}: {str(e)}")
                break

        return list_stats

    def _fetch_single_page(self, list_id: str, pagination_token: str = None):
        """
        拉取单页数据

        Returns:
            (page_data, next_token, cost)
        """
        try:
            # 记录拉取前的成本
            cost_before = self.api_client.total_cost

            # 调用API获取单页（使用cursor参数进行分页）
            page_data, next_token = self.api_client.fetch_tweets(
                list_id=list_id,
                cursor=pagination_token
            )

            # 计算本次请求的实际成本
            cost = self.api_client.total_cost - cost_before

            return page_data, next_token, cost

        except Exception as e:
            self.logger.error(f"拉取单页数据失败: {e}")
            return [], None, 0.0

    def _process_and_save_page(self, page_data: list):
        """
        处理并存储一页数据

        Returns:
            (saved_tweets_count, saved_users_count)
        """
        try:
            if not page_data:
                return 0, 0

            # 1. 提取用户数据
            users = self.data_mapper.extract_users_from_tweets(page_data)

            # 2. 映射推文数据
            tweets = self.data_mapper.map_api_data_list_to_tweets(page_data)

            if not tweets:
                return 0, 0

            # 3. 构建用户数据映射
            user_data_map = {}
            for api_data in page_data:
                try:
                    # 注意：fetch_tweets已经转换格式，字段名是'id_str'而非'id'
                    tweet_id = api_data.get('id_str')
                    user_data = api_data.get('author')
                    if tweet_id and user_data:
                        user_data_map[tweet_id] = user_data
                except:
                    continue

            # 4. 增强推文数据
            enriched_tweets = self.tweet_enricher.enrich_tweets(tweets, user_data_map)

            # 5. 先保存用户
            users_saved = 0
            if users:
                try:
                    user_dao.batch_upsert_users(users)
                    users_saved = len(users)
                except Exception as e:
                    self.logger.warning(f"保存用户失败: {e}")

            # 6. 再保存推文
            tweets_saved = 0
            if enriched_tweets:
                try:
                    tweet_dao.batch_upsert_tweets(enriched_tweets)
                    tweets_saved = len(enriched_tweets)
                except Exception as e:
                    self.logger.warning(f"保存推文失败: {e}")

            return tweets_saved, users_saved

        except Exception as e:
            self.logger.error(f"处理并保存页面数据失败: {e}")
            return 0, 0

    def _show_final_stats(self):
        """显示最终统计"""
        self.logger.info("")
        self.logger.info("=" * 80)
        self.logger.info("📊 流式回填总体统计")
        self.logger.info("=" * 80)
        self.logger.info(f"📋 处理List数: {len(self.stats['lists_processed'])}")
        self.logger.info(f"📝 拉取推文: {self.stats['total_tweets_fetched']}条")
        self.logger.info(f"✅ 保存推文: {self.stats['total_tweets_saved']}条")
        self.logger.info(f"👥 保存用户: {self.stats['total_users_saved']}个")
        self.logger.info(f"🔗 API调用: {self.stats['total_api_calls']}次")
        self.logger.info(f"💰 总成本: ${self.stats['total_cost']:.4f}")

        if self.stats['errors']:
            self.logger.warning(f"\n⚠️  错误列表 ({len(self.stats['errors'])}个):")
            for error in self.stats['errors']:
                self.logger.warning(f"   - {error}")

        self.logger.info("=" * 80)


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='KOL推文流式回填脚本（边拉边存）')
    parser.add_argument('--days', type=int, default=7, help='回填天数，默认7天')
    parser.add_argument('--test', action='store_true', help='测试模式，只处理1个list的1页')

    args = parser.parse_args()

    backfiller = StreamingBackfill()

    try:
        if args.test:
            # 测试模式：只处理1个list
            logger.info("🧪 测试模式：只处理1个list的少量数据")
            list_ids = config.get('api_twitterapi', {}).get('default_params', {}).get('list_ids_kol', [])[:1]
            success = backfiller.backfill_by_days(days=1, list_ids=list_ids)
        else:
            # 正常模式
            success = backfiller.backfill_by_days(days=args.days)

        if success:
            logger.info("✅ 回填任务全部完成")
            sys.exit(0)
        else:
            logger.error("❌ 回填任务失败或部分失败")
            sys.exit(1)

    except KeyboardInterrupt:
        logger.info("\n⚠️  接收到中断信号，停止回填...")
        logger.info("💾 已保存的数据不会丢失，可以重新运行继续回填")
        sys.exit(1)
    except Exception as e:
        logger.error(f"❌ 回填出错: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
