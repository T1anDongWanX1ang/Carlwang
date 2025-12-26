#!/usr/bin/env python3
"""
更新数据库中推文的活动标记和摘要
扫描过去48小时的推文，检测活动并更新数据库的 is_activity 和 summary 字段

活动类型包括：campaign, airdrop, quest, reward, giveaway

使用方法：
    # 基本用法 - 更新过去48小时的推文
    python update_campaign_tweets.py

    # 指定时间范围
    python update_campaign_tweets.py --hours 24

    # 先模拟运行看效果（不会真正修改数据库）
    python update_campaign_tweets.py --dry-run
"""
import sys
from pathlib import Path
from datetime import datetime, timedelta
from typing import List
import time

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.database.tweet_dao import tweet_dao
from src.database.connection import db_manager
from src.api.chatgpt_client import chatgpt_client
from src.utils.logger import get_logger
from src.models.tweet import Tweet


class CampaignTweetUpdater:
    """活动推文数据库更新器"""

    def __init__(self):
        """初始化更新器"""
        self.logger = get_logger(__name__)
        self.tweet_dao = tweet_dao
        self.db_manager = db_manager
        self.chatgpt_client = chatgpt_client

        # 活动关键词
        self.campaign_keywords = [
            'campaign', 'airdrop', 'quest', 'reward', 'giveaway',
            'bounty', 'contest', 'prize', 'distribution', 'incentive',
            '空投', '活动', '奖励', '赠送'
        ]

        # 统计信息
        self.total_checked = 0
        self.campaigns_found = 0
        self.updated_count = 0
        self.error_count = 0

    def update_campaign_tweets(self, hours: int = 48, batch_size: int = 5,
                               dry_run: bool = False) -> bool:
        """
        更新活动推文数据

        Args:
            hours: 扫描最近多少小时的推文
            batch_size: 每批处理的推文数量
            dry_run: 是否为模拟运行（不实际更新数据库）

        Returns:
            是否成功
        """
        try:
            self.logger.info("=" * 60)
            self.logger.info(f"开始更新活动推文数据 (过去 {hours} 小时)")
            if dry_run:
                self.logger.info("【模拟运行模式 - 不会修改数据库】")
            self.logger.info("=" * 60)

            # 1. 获取最近推文
            cutoff_time = datetime.now() - timedelta(hours=hours)
            recent_tweets = self.tweet_dao.get_recent_tweets(
                since_time=cutoff_time,
                limit=2000
            )

            self.logger.info(f"获取到 {len(recent_tweets)} 条推文")

            if not recent_tweets:
                self.logger.warning("没有找到推文")
                return False

            # 2. 过滤包含关键词的推文
            filtered_tweets = [
                t for t in recent_tweets
                if t.full_text and any(kw in t.full_text.lower() for kw in self.campaign_keywords)
            ]

            self.logger.info(f"关键词过滤后剩余 {len(filtered_tweets)} 条推文")

            # 3. 批量处理
            for i in range(0, len(filtered_tweets), batch_size):
                batch = filtered_tweets[i:i + batch_size]
                batch_num = i // batch_size + 1
                total_batches = (len(filtered_tweets) - 1) // batch_size + 1

                self.logger.info(f"\n处理批次 {batch_num}/{total_batches}")

                for tweet in batch:
                    self._process_tweet(tweet, dry_run)

                # 避免API请求过快
                if i + batch_size < len(filtered_tweets):
                    time.sleep(2)

            # 4. 显示统计
            self.logger.info("\n" + "=" * 60)
            self.logger.info("更新完成！")
            self.logger.info(f"检查的推文数: {self.total_checked}")
            self.logger.info(f"发现的活动推文: {self.campaigns_found}")
            self.logger.info(f"成功更新: {self.updated_count}")
            self.logger.info(f"失败: {self.error_count}")
            self.logger.info("=" * 60)

            return True

        except Exception as e:
            self.logger.error(f"更新活动推文失败: {e}")
            import traceback
            self.logger.error(traceback.format_exc())
            return False

    def _process_tweet(self, tweet: Tweet, dry_run: bool = False):
        """
        处理单条推文

        Args:
            tweet: 推文对象
            dry_run: 是否为模拟运行
        """
        try:
            self.total_checked += 1

            # 检测是否为活动
            is_campaign = self.chatgpt_client.detect_campaign_announcement([tweet.full_text])

            if is_campaign:
                self.campaigns_found += 1
                self.logger.info(f"✓ 发现活动推文: {tweet.id_str}")

                # 生成摘要
                project_info = {
                    'name': tweet.project_tag or 'Unknown',
                    'symbol': tweet.token_tag or 'Unknown',
                    'category': 'Crypto'
                }

                summary = self.chatgpt_client.generate_campaign_summary(
                    project_info,
                    [tweet.full_text]
                )

                if summary:
                    self.logger.info(f"  摘要: {summary[:100]}...")

                # 更新数据库
                if not dry_run:
                    success = self._update_tweet_in_db(tweet.id_str, summary)
                    if success:
                        self.updated_count += 1
                    else:
                        self.error_count += 1
                else:
                    self.logger.info(f"  [模拟] 将更新推文 {tweet.id_str}")
            else:
                self.logger.debug(f"✗ 非活动推文: {tweet.id_str}")

        except Exception as e:
            self.logger.error(f"处理推文 {tweet.id_str} 失败: {e}")
            self.error_count += 1

    def _update_tweet_in_db(self, tweet_id: str, summary: str) -> bool:
        """
        更新数据库中的推文

        Args:
            tweet_id: 推文ID
            summary: 活动摘要

        Returns:
            是否成功
        """
        try:
            table_name = self.db_manager.db_config.get('tables', {}).get('tweet', 'twitter_tweet')

            # 更新 is_activity 字段和 summary 字段
            sql = f"""
            UPDATE {table_name}
            SET is_activity = 1, summary = %s
            WHERE id_str = %s
            """

            affected_rows = self.db_manager.execute_update(sql, (summary, tweet_id))

            if affected_rows > 0:
                self.logger.info(f"  数据库更新成功: {tweet_id}")
                return True
            else:
                self.logger.warning(f"  数据库更新失败（无影响行）: {tweet_id}")
                return False

        except Exception as e:
            self.logger.error(f"更新数据库失败 {tweet_id}: {e}")
            return False


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description='更新数据库中的活动推文标记')
    parser.add_argument('--hours', type=int, default=48,
                        help='扫描最近多少小时的推文 (默认: 48)')
    parser.add_argument('--batch-size', type=int, default=5,
                        help='每批处理的推文数量 (默认: 5)')
    parser.add_argument('--dry-run', action='store_true',
                        help='模拟运行，不实际修改数据库')

    args = parser.parse_args()

    # 创建更新器
    updater = CampaignTweetUpdater()

    # 执行更新
    success = updater.update_campaign_tweets(
        hours=args.hours,
        batch_size=args.batch_size,
        dry_run=args.dry_run
    )

    if success:
        print("\n✓ 更新完成")
        sys.exit(0)
    else:
        print("\n✗ 更新失败")
        sys.exit(1)


if __name__ == '__main__':
    main()
