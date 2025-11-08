#!/usr/bin/env python3
"""
回填推文的project_tag字段
用于对历史推文数据重新提取project_tag
"""
import sys
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any

# 添加项目根目录到路径
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.database.connection import db_manager
from src.utils.smart_classifier import SmartClassifier
from src.api.chatgpt_client import ChatGPTClient


# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('backfill_project_tags.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def get_tweets_from_last_week(limit: int = None) -> List[Dict[str, Any]]:
    """
    获取过去一周的推文数据

    Args:
        limit: 限制返回数量，None表示不限制

    Returns:
        推文数据列表
    """
    try:
        # 计算一周前的时间
        one_week_ago = datetime.now() - timedelta(days=7)

        # 查询推文（只查询有效推文，且有full_text的）
        sql = """
        SELECT
            id_str,
            full_text,
            created_at_datetime,
            project_id,
            project_tag,
            token_tag
        FROM twitter_tweet
        WHERE created_at_datetime >= %s
        AND is_valid = 1
        AND full_text IS NOT NULL
        AND LENGTH(full_text) > 10
        ORDER BY created_at_datetime DESC
        """

        if limit:
            sql += f" LIMIT {limit}"

        results = db_manager.execute_query(sql, (one_week_ago,))

        logger.info(f"查询到 {len(results)} 条推文（过去7天）")
        return results

    except Exception as e:
        logger.error(f"查询推文失败: {e}")
        return []


def update_tweet_project_tag(id_str: str, project_tag: str) -> bool:
    """
    更新推文的project_tag字段

    由于Doris不支持更新包含主键的字段，这里使用DELETE + INSERT策略

    Args:
        id_str: 推文ID
        project_tag: 项目标签

    Returns:
        是否更新成功
    """
    try:
        # 1. 先查询完整的推文数据
        select_sql = "SELECT * FROM twitter_tweet WHERE id_str = %s"
        results = db_manager.execute_query(select_sql, (id_str,))

        if not results:
            logger.warning(f"未找到推文: {id_str}")
            return False

        tweet_data = results[0]

        # 2. 删除旧记录
        delete_sql = "DELETE FROM twitter_tweet WHERE id_str = %s"
        db_manager.execute_update(delete_sql, (id_str,))

        # 3. 插入新记录（更新project_tag）
        insert_sql = """
        INSERT INTO twitter_tweet (
            id_str, conversation_id_str, in_reply_to_status_id_str,
            full_text, created_at, created_at_datetime,
            bookmark_count, favorite_count, quote_count, reply_count,
            retweet_count, view_count, engagement_total, update_time,
            kol_id, entity_id, project_id, topic_id, is_valid, sentiment,
            tweet_url, link_url, token_tag, project_tag, isAnnounce, summary
        ) VALUES (
            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
        )
        """

        params = (
            tweet_data['id_str'],
            tweet_data.get('conversation_id_str'),
            tweet_data.get('in_reply_to_status_id_str'),
            tweet_data.get('full_text'),
            tweet_data.get('created_at'),
            tweet_data.get('created_at_datetime'),
            tweet_data.get('bookmark_count', 0),
            tweet_data.get('favorite_count', 0),
            tweet_data.get('quote_count', 0),
            tweet_data.get('reply_count', 0),
            tweet_data.get('retweet_count', 0),
            tweet_data.get('view_count', 0),
            tweet_data.get('engagement_total', 0),
            datetime.now(),  # 更新update_time
            tweet_data.get('kol_id'),
            tweet_data.get('entity_id'),
            tweet_data.get('project_id'),
            tweet_data.get('topic_id'),
            tweet_data.get('is_valid', 1),
            tweet_data.get('sentiment'),
            tweet_data.get('tweet_url'),
            tweet_data.get('link_url'),
            tweet_data.get('token_tag'),
            project_tag,  # 使用新的project_tag
            tweet_data.get('isAnnounce', 0),
            tweet_data.get('summary')
        )

        affected_rows = db_manager.execute_update(insert_sql, params)

        if affected_rows > 0:
            logger.debug(f"成功更新推文 {id_str} 的project_tag: {project_tag}")
            return True
        else:
            logger.warning(f"更新推文 {id_str} 失败")
            return False

    except Exception as e:
        logger.error(f"更新推文 {id_str} 的project_tag失败: {e}")
        return False


def backfill_project_tags(tweets: List[Dict[str, Any]], batch_size: int = 50) -> Dict[str, int]:
    """
    批量回填推文的project_tag

    Args:
        tweets: 推文列表
        batch_size: 批处理大小

    Returns:
        统计信息字典
    """
    chatgpt_client = ChatGPTClient()
    classifier = SmartClassifier(chatgpt_client)

    stats = {
        'total': len(tweets),
        'updated': 0,
        'failed': 0,
        'skipped': 0,
        'matched_rootdata': 0,
        'not_project': 0
    }

    logger.info(f"开始处理 {len(tweets)} 条推文...")

    for i, tweet in enumerate(tweets):
        try:
            id_str = tweet['id_str']
            full_text = tweet['full_text']
            current_project_tag = tweet.get('project_tag')

            # 如果已经有project_tag，可以选择跳过
            # if current_project_tag:
            #     logger.debug(f"推文 {id_str} 已有project_tag: {current_project_tag}，跳过")
            #     stats['skipped'] += 1
            #     continue

            # 使用智能分类器进行分类
            logger.info(f"处理推文 {i+1}/{len(tweets)}: {id_str}")
            classification_result = classifier.classify_content(full_text, id_str)

            if not classification_result:
                logger.debug(f"推文 {id_str} 分类失败，跳过")
                stats['skipped'] += 1
                continue

            # 只处理项目类型的推文
            if classification_result.content_type != 'project':
                logger.debug(f"推文 {id_str} 不是项目类型，是 {classification_result.content_type}")
                stats['not_project'] += 1

                # 如果当前有project_tag但分类结果不是项目，清空project_tag
                if current_project_tag:
                    if update_tweet_project_tag(id_str, None):
                        stats['updated'] += 1
                        logger.info(f"推文 {id_str} 清空project_tag（非项目类型）")
                    else:
                        stats['failed'] += 1

                continue

            # 获取新的project_tag
            new_project_tag = classification_result.project_tag

            # 如果project_tag没有变化，跳过
            if new_project_tag == current_project_tag:
                logger.debug(f"推文 {id_str} project_tag未变化: {new_project_tag}")
                stats['skipped'] += 1
                continue

            # 更新project_tag
            if update_tweet_project_tag(id_str, new_project_tag):
                stats['updated'] += 1
                if new_project_tag:
                    stats['matched_rootdata'] += 1
                    logger.info(f"✓ 推文 {id_str} 更新project_tag: {current_project_tag} -> {new_project_tag}")
                else:
                    logger.info(f"✓ 推文 {id_str} project_tag未匹配到RootData")
            else:
                stats['failed'] += 1
                logger.error(f"✗ 推文 {id_str} 更新失败")

            # 每处理batch_size条输出一次进度
            if (i + 1) % batch_size == 0:
                logger.info(f"进度: {i+1}/{len(tweets)} ({(i+1)*100//len(tweets)}%)")
                logger.info(f"统计: 更新={stats['updated']}, 失败={stats['failed']}, "
                           f"跳过={stats['skipped']}, RootData匹配={stats['matched_rootdata']}, "
                           f"非项目={stats['not_project']}")

        except Exception as e:
            logger.error(f"处理推文 {tweet.get('id_str')} 时出错: {e}")
            stats['failed'] += 1
            continue

    return stats


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description='回填推文的project_tag字段')
    parser.add_argument('--days', type=int, default=7, help='回填最近N天的数据（默认7天）')
    parser.add_argument('--limit', type=int, default=None, help='限制处理的推文数量')
    parser.add_argument('--batch-size', type=int, default=50, help='批处理大小（默认50）')

    args = parser.parse_args()

    logger.info("=" * 80)
    logger.info("开始回填推文project_tag")
    logger.info(f"参数: days={args.days}, limit={args.limit}, batch_size={args.batch_size}")
    logger.info("=" * 80)

    # 获取推文数据
    tweets = get_tweets_from_last_week(limit=args.limit)

    if not tweets:
        logger.warning("没有找到需要处理的推文")
        return

    # 执行回填
    stats = backfill_project_tags(tweets, batch_size=args.batch_size)

    # 输出最终统计
    logger.info("=" * 80)
    logger.info("回填完成！")
    logger.info(f"总数: {stats['total']}")
    logger.info(f"更新成功: {stats['updated']}")
    logger.info(f"更新失败: {stats['failed']}")
    logger.info(f"跳过: {stats['skipped']}")
    logger.info(f"匹配到RootData: {stats['matched_rootdata']}")
    logger.info(f"非项目类型: {stats['not_project']}")
    logger.info(f"成功率: {stats['updated']*100/stats['total']:.2f}%")
    logger.info("=" * 80)


if __name__ == '__main__':
    main()
