#!/usr/bin/env python3
"""
回填最近48小时推文的活动数据（使用新的JSON结构化格式）

从推文中检测活动并提取结构化的JSON数据：
{
  "title": "活动标题（5个词以内）",
  "status": "Active",
  "summary": "活动摘要（20个词以内）",
  "time": "推文时间",
  "url": "推文链接"
}

使用方法：
    # 基本用法 - 回填过去48小时的推文
    python backfill_activities_48h.py

    # 指定时间范围（小时）
    python backfill_activities_48h.py --hours 24

    # 先模拟运行看效果（不会真正修改数据库）
    python backfill_activities_48h.py --dry-run

    # 调整批处理大小
    python backfill_activities_48h.py --batch-size 10
"""
import sys
import json
import time
from pathlib import Path
from datetime import datetime, timedelta
from typing import List
import argparse

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.database.tweet_dao import tweet_dao
from src.database.connection import db_manager
from src.api.chatgpt_client import chatgpt_client
from src.utils.logger import get_logger
from src.models.tweet import Tweet


class ActivityBackfiller:
    """活动数据回填器（使用新的JSON结构化格式）"""

    def __init__(self):
        """初始化回填器"""
        self.logger = get_logger(__name__)
        self.tweet_dao = tweet_dao
        self.db_manager = db_manager
        self.chatgpt_client = chatgpt_client

        # 活动关键词
        self.activity_keywords = [
            'campaign', 'airdrop', 'quest', 'reward', 'giveaway',
            'bounty', 'contest', 'prize', 'distribution', 'incentive',
            '空投', '活动', '奖励', '赠送'
        ]

        # 统计信息
        self.total_checked = 0
        self.activities_found = 0
        self.updated_count = 0
        self.error_count = 0

    def backfill_activities(self, hours: int = 48, batch_size: int = 5,
                           dry_run: bool = False) -> bool:
        """
        回填活动数据

        Args:
            hours: 扫描最近多少小时的推文
            batch_size: 每批处理的推文数量
            dry_run: 是否为模拟运行（不实际更新数据库）

        Returns:
            是否成功
        """
        try:
            self.logger.info("=" * 60)
            self.logger.info(f"开始回填活动数据 (过去 {hours} 小时)")
            self.logger.info(f"使用新的JSON结构化格式")
            if dry_run:
                self.logger.info("【模拟运行模式 - 不会修改数据库】")
            self.logger.info("=" * 60)

            # 1. 获取最近推文
            cutoff_time = datetime.now() - timedelta(hours=hours)
            recent_tweets = self.tweet_dao.get_recent_tweets(
                since_time=cutoff_time,
                limit=5000
            )

            self.logger.info(f"获取到 {len(recent_tweets)} 条推文")

            if not recent_tweets:
                self.logger.warning("没有找到推文")
                return False

            # 2. 过滤包含关键词的推文
            filtered_tweets = [
                t for t in recent_tweets
                if t.full_text and any(kw in t.full_text.lower() for kw in self.activity_keywords)
            ]

            self.logger.info(f"关键词过滤后剩余 {len(filtered_tweets)} 条推文")

            if not filtered_tweets:
                self.logger.info("没有找到包含活动关键词的推文")
                return True

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
                    self.logger.info("等待2秒，避免API限流...")
                    time.sleep(2)

            # 4. 显示统计
            self.logger.info("\n" + "=" * 60)
            self.logger.info("回填完成！")
            self.logger.info(f"检查的推文数: {self.total_checked}")
            self.logger.info(f"发现的活动推文: {self.activities_found}")
            self.logger.info(f"成功更新: {self.updated_count}")
            self.logger.info(f"失败: {self.error_count}")
            self.logger.info("=" * 60)

            return True

        except Exception as e:
            self.logger.error(f"回填活动数据失败: {e}")
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

            # 1. 检测是否为活动
            is_activity = self.chatgpt_client.detect_campaign_announcement([tweet.full_text])

            if is_activity:
                self.activities_found += 1
                self.logger.info(f"✓ 发现活动推文: {tweet.id_str}")

                # 2. 生成推文URL（使用通用格式，不需要用户名）
                tweet_url = f"https://twitter.com/i/status/{tweet.id_str}"

                # 3. 提取结构化数据（新JSON格式）
                activity_data = self.chatgpt_client.extract_activity_structured_data(
                    tweet_text=tweet.full_text,
                    tweet_url=tweet_url,
                    tweet_time=str(tweet.created_at) if tweet.created_at else ""
                )

                if activity_data:
                    self.logger.info(f"  标题: {activity_data['title']}")
                    self.logger.info(f"  摘要: {activity_data['summary']}")

                    # 将结构化数据转换为JSON字符串
                    activity_detail_json = json.dumps(activity_data, ensure_ascii=False)

                    # 更新数据库
                    if not dry_run:
                        success = self._update_tweet_in_db(
                            tweet_id=tweet.id_str,
                            activity_detail=activity_detail_json
                        )
                        if success:
                            self.updated_count += 1
                        else:
                            self.error_count += 1
                    else:
                        self.logger.info(f"  [模拟] 将更新推文 {tweet.id_str}")
                        self.logger.info(f"  [模拟] JSON数据: {activity_detail_json}")
                else:
                    self.logger.warning(f"  无法提取活动结构化数据")
                    self.error_count += 1
            else:
                self.logger.debug(f"✗ 非活动推文: {tweet.id_str}")

        except Exception as e:
            self.logger.error(f"处理推文 {tweet.id_str} 失败: {e}")
            self.error_count += 1

    def _update_tweet_in_db(self, tweet_id: str, activity_detail: str) -> bool:
        """
        更新数据库中的推文

        Args:
            tweet_id: 推文ID
            activity_detail: 活动详情（JSON字符串）

        Returns:
            是否成功
        """
        try:
            table_name = self.db_manager.db_config.get('tables', {}).get('tweet', 'twitter_tweet')

            # 更新 is_activity 字段和 activity_detail 字段
            sql = f"""
            UPDATE {table_name}
            SET is_activity = 1, activity_detail = %s
            WHERE id_str = %s
            """

            affected_rows = self.db_manager.execute_update(sql, (activity_detail, tweet_id))

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
    parser = argparse.ArgumentParser(
        description='回填最近推文的活动数据（使用新的JSON结构化格式）'
    )
    parser.add_argument('--hours', type=int, default=48,
                        help='扫描最近多少小时的推文 (默认: 48)')
    parser.add_argument('--batch-size', type=int, default=5,
                        help='每批处理的推文数量 (默认: 5)')
    parser.add_argument('--dry-run', action='store_true',
                        help='模拟运行，不实际修改数据库')

    args = parser.parse_args()

    # 创建回填器
    backfiller = ActivityBackfiller()

    # 执行回填
    success = backfiller.backfill_activities(
        hours=args.hours,
        batch_size=args.batch_size,
        dry_run=args.dry_run
    )

    if success:
        print("\n✓ 回填完成")
        sys.exit(0)
    else:
        print("\n✗ 回填失败")
        sys.exit(1)


if __name__ == '__main__':
    main()
