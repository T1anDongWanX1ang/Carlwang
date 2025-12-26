#!/usr/bin/env python3
"""
回填is_retweet字段的脚本
从Twitter API重新获取推文数据，检测转发状态并更新数据库
"""
import sys
import logging
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.database.connection import db_manager
from src.api.twitter_api import twitter_api
from src.utils.simple_tweet_enricher import simple_tweet_enricher
from src.utils.logger import get_logger


class IsRetweetBackfiller:
    """is_retweet字段回填工具"""

    def __init__(self):
        """初始化回填工具"""
        self.logger = get_logger(__name__)
        self.db_manager = db_manager
        self.twitter_api = twitter_api
        self.enricher = simple_tweet_enricher

        # 统计信息
        self.total_processed = 0
        self.total_updated = 0
        self.total_retweets = 0
        self.total_errors = 0

    def backfill_from_database(self, table_name: str = "twitter_tweet_project_new",
                              limit: int = None) -> bool:
        """
        从数据库查询推文ID，通过API重新获取数据并更新is_retweet字段

        Args:
            table_name: 表名
            limit: 限制处理的数量，None表示处理全部

        Returns:
            是否成功
        """
        try:
            self.logger.info(f"开始回填{table_name}表的is_retweet字段...")

            # 1. 从数据库查询需要更新的推文ID
            tweet_ids = self._fetch_tweet_ids(table_name, limit)

            if not tweet_ids:
                self.logger.warning("没有找到需要更新的推文")
                return False

            self.logger.info(f"找到{len(tweet_ids)}条推文需要回填")

            # 2. 通过API批量获取推文数据
            self.logger.info("通过Twitter API获取推文详情...")
            api_data_list = self._fetch_tweets_from_api(tweet_ids)

            if not api_data_list:
                self.logger.error("无法从API获取推文数据")
                return False

            self.logger.info(f"成功从API获取{len(api_data_list)}条推文数据")

            # 3. 检测转发状态并更新数据库
            self._update_retweet_status(table_name, api_data_list)

            # 4. 显示统计信息
            self._print_statistics()

            return True

        except Exception as e:
            self.logger.error(f"回填失败: {e}", exc_info=True)
            return False

    def backfill_by_ids(self, table_name: str, tweet_ids: List[str]) -> bool:
        """
        回填指定ID的推文

        Args:
            table_name: 表名
            tweet_ids: 推文ID列表

        Returns:
            是否成功
        """
        try:
            self.logger.info(f"开始回填{len(tweet_ids)}条指定推文...")

            # 通过API批量获取推文数据
            api_data_list = self._fetch_tweets_from_api(tweet_ids)

            if not api_data_list:
                self.logger.error("无法从API获取推文数据")
                return False

            # 更新数据库
            self._update_retweet_status(table_name, api_data_list)

            # 显示统计信息
            self._print_statistics()

            return True

        except Exception as e:
            self.logger.error(f"回填失败: {e}", exc_info=True)
            return False

    def _fetch_tweet_ids(self, table_name: str, limit: int = None) -> List[str]:
        """
        从数据库查询推文ID

        Args:
            table_name: 表名
            limit: 限制数量

        Returns:
            推文ID列表
        """
        try:
            # 查询is_retweet为NULL或False的推文（需要重新检测）
            if limit:
                sql = f"""
                SELECT id_str
                FROM {table_name}
                WHERE is_retweet IS NULL OR is_retweet = false
                ORDER BY created_at_datetime DESC
                LIMIT %s
                """
                results = self.db_manager.execute_query(sql, (limit,))
            else:
                sql = f"""
                SELECT id_str
                FROM {table_name}
                WHERE is_retweet IS NULL OR is_retweet = false
                ORDER BY created_at_datetime DESC
                """
                results = self.db_manager.execute_query(sql)

            tweet_ids = [row['id_str'] for row in results]
            self.logger.info(f"从数据库查询到{len(tweet_ids)}条推文ID")

            return tweet_ids

        except Exception as e:
            self.logger.error(f"查询推文ID失败: {e}")
            return []

    def _fetch_tweets_from_api(self, tweet_ids: List[str]) -> List[Dict[str, Any]]:
        """
        通过Twitter API获取推文详情

        注意: 此方法需要Twitter API支持批量查询推文详情
        如果API不支持，需要逐个查询或从缓存/日志中获取

        Args:
            tweet_ids: 推文ID列表

        Returns:
            API数据列表
        """
        try:
            # 方案1: 如果Twitter API支持批量查询
            # api_data_list = self.twitter_api.get_tweets_by_ids(tweet_ids)

            # 方案2: 由于TweetScout API可能不支持直接查询推文详情
            # 我们提供一个简化方案：只检查数据库中的字段
            self.logger.warning("注意: Twitter API可能不支持批量查询推文详情")
            self.logger.info("建议: 从原始API日志或缓存中获取推文数据")

            # 返回空列表，让用户提供API数据
            return []

        except Exception as e:
            self.logger.error(f"从API获取推文失败: {e}")
            return []

    def _update_retweet_status(self, table_name: str, api_data_list: List[Dict[str, Any]]) -> None:
        """
        检测转发状态并批量更新数据库

        Args:
            table_name: 表名
            api_data_list: API数据列表
        """
        try:
            for api_data in api_data_list:
                self.total_processed += 1

                try:
                    tweet_id = api_data.get('id_str')
                    if not tweet_id:
                        self.logger.warning(f"API数据缺少id_str字段: {api_data}")
                        self.total_errors += 1
                        continue

                    # 检测转发状态
                    is_retweet = self.enricher._detect_retweet_status(api_data)

                    if is_retweet:
                        self.total_retweets += 1
                        self.logger.info(f"检测到转发推文: {tweet_id}")

                    # 更新数据库
                    success = self._update_single_tweet(table_name, tweet_id, is_retweet)

                    if success:
                        self.total_updated += 1
                    else:
                        self.total_errors += 1

                except Exception as e:
                    self.logger.error(f"处理推文失败: {e}")
                    self.total_errors += 1
                    continue

            self.logger.info(f"批量更新完成: 处理{self.total_processed}条，更新{self.total_updated}条")

        except Exception as e:
            self.logger.error(f"批量更新失败: {e}")

    def _update_single_tweet(self, table_name: str, tweet_id: str, is_retweet: bool) -> bool:
        """
        更新单条推文的is_retweet字段

        Args:
            table_name: 表名
            tweet_id: 推文ID
            is_retweet: 是否为转发

        Returns:
            是否成功
        """
        try:
            sql = f"""
            UPDATE {table_name}
            SET is_retweet = %s, update_time = %s
            WHERE id_str = %s
            """

            params = (is_retweet, datetime.now(), tweet_id)
            affected_rows = self.db_manager.execute_update(sql, params)

            if affected_rows > 0:
                self.logger.debug(f"成功更新推文 {tweet_id}: is_retweet={is_retweet}")
                return True
            else:
                self.logger.warning(f"更新推文 {tweet_id} 失败，可能不存在")
                return False

        except Exception as e:
            self.logger.error(f"更新推文 {tweet_id} 失败: {e}")
            return False

    def update_by_manual_data(self, table_name: str, manual_data: List[Dict[str, Any]]) -> bool:
        """
        使用手动提供的API数据更新is_retweet字段

        适用于无法通过API重新获取数据的情况

        Args:
            table_name: 表名
            manual_data: 手动提供的API数据列表，格式如下：
                [
                    {'id_str': '123456', 'retweeted_status': {...}},  # 转发推文
                    {'id_str': '789012'},  # 非转发推文
                ]

        Returns:
            是否成功
        """
        try:
            self.logger.info(f"使用手动数据更新{len(manual_data)}条推文...")

            self._update_retweet_status(table_name, manual_data)
            self._print_statistics()

            return True

        except Exception as e:
            self.logger.error(f"手动更新失败: {e}")
            return False

    def _print_statistics(self) -> None:
        """打印统计信息"""
        self.logger.info("=" * 50)
        self.logger.info("回填统计信息:")
        self.logger.info(f"  处理总数: {self.total_processed}")
        self.logger.info(f"  成功更新: {self.total_updated}")
        self.logger.info(f"  转发推文: {self.total_retweets}")
        self.logger.info(f"  错误数量: {self.total_errors}")

        if self.total_updated > 0:
            retweet_rate = (self.total_retweets / self.total_updated) * 100
            self.logger.info(f"  转发比例: {retweet_rate:.2f}%")

        self.logger.info("=" * 50)


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description='回填is_retweet字段')
    parser.add_argument('--table', default='twitter_tweet_project_new',
                       help='表名 (默认: twitter_tweet_project_new)')
    parser.add_argument('--limit', type=int, help='限制处理的数量')
    parser.add_argument('--ids', nargs='+', help='指定要更新的推文ID列表')
    parser.add_argument('--test', action='store_true', help='测试模式，仅显示统计信息')

    args = parser.parse_args()

    # 创建回填工具
    backfiller = IsRetweetBackfiller()
    logger = backfiller.logger

    logger.info("=" * 50)
    logger.info("is_retweet字段回填工具")
    logger.info("=" * 50)

    if args.test:
        logger.info("测试模式: 连接数据库...")
        if backfiller.db_manager.test_connection():
            logger.info("✓ 数据库连接成功")
        else:
            logger.error("✗ 数据库连接失败")
            sys.exit(1)
        return

    # 执行回填
    if args.ids:
        # 指定ID回填
        logger.info(f"回填指定的{len(args.ids)}条推文...")
        success = backfiller.backfill_by_ids(args.table, args.ids)
    else:
        # 从数据库查询回填
        logger.info(f"从数据库查询并回填...")
        success = backfiller.backfill_from_database(args.table, args.limit)

    if success:
        logger.info("回填完成")
        sys.exit(0)
    else:
        logger.error("回填失败")
        sys.exit(1)


if __name__ == '__main__':
    main()
