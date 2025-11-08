#!/usr/bin/env python3
"""
批量提取推文的token_tag
针对最近一周的非项目推文进行token符号提取
"""
import sys
from pathlib import Path
from datetime import datetime, timedelta

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.database.tweet_dao import tweet_dao
from src.api.chatgpt_client import chatgpt_client
from src.utils.token_extractor import token_extractor
from src.utils.logger import get_logger


def batch_extract_token_tags(days: int = 7):
    """
    批量提取推文的token_tag

    Args:
        days: 处理最近几天的数据，默认7天
    """
    logger = get_logger(__name__)
    logger.info(f"开始批量提取token_tag（最近{days}天的非项目推文）...")

    try:
        # 查询最近N天的非项目推文
        sql = """
        SELECT id_str, full_text, token_tag
        FROM twitter_tweet
        WHERE project_id IS NULL
        AND update_time >= DATE_SUB(NOW(), INTERVAL %s DAY)
        AND full_text IS NOT NULL
        AND LENGTH(full_text) >= 10
        ORDER BY update_time DESC
        """

        tweets_result = tweet_dao.db_manager.execute_query(sql, [days])

        if not tweets_result:
            logger.warning(f"没有找到符合条件的推文数据（最近{days}天，非项目推文）")
            return

        logger.info(f"找到 {len(tweets_result)} 条推文需要处理")

        updated_count = 0
        skipped_count = 0
        error_count = 0
        no_token_count = 0

        for i, tweet_row in enumerate(tweets_result, 1):
            tweet_id = tweet_row['id_str']
            full_text = tweet_row['full_text']
            current_token_tag = tweet_row.get('token_tag')

            # 显示进度（每100条）
            if i % 100 == 0:
                logger.info(f"进度: {i}/{len(tweets_result)} ({updated_count}个更新, {skipped_count}个跳过, {no_token_count}个无token, {error_count}个失败)")

            try:
                # 如果已经有token_tag，跳过（除非你想重新提取）
                # 如果要强制重新提取，注释掉下面这段
                if current_token_tag:
                    logger.debug(f"[{i}/{len(tweets_result)}] 推文 {tweet_id} 已有token_tag: {current_token_tag}，跳过")
                    skipped_count += 1
                    continue

                logger.debug(f"[{i}/{len(tweets_result)}] 处理推文 {tweet_id}: {full_text[:60]}...")

                # 1. 使用AI提取token symbols
                ai_symbols = None
                try:
                    ai_symbols = chatgpt_client.extract_token_symbols_from_tweet(full_text)
                    if ai_symbols:
                        logger.debug(f"  AI提取: {ai_symbols}")
                except Exception as e:
                    logger.warning(f"  AI提取失败，将使用规则提取: {e}")

                # 2. 使用token_extractor验证和规范化
                token_tag = token_extractor.extract_symbols_from_text(full_text, ai_symbols)

                if token_tag:
                    # 更新数据库
                    update_sql = """
                    UPDATE twitter_tweet
                    SET token_tag = %s,
                        update_time = NOW()
                    WHERE id_str = %s
                    """

                    affected_rows = tweet_dao.db_manager.execute_update(update_sql, [token_tag, tweet_id])

                    if affected_rows > 0:
                        updated_count += 1
                        logger.info(f"  ✅ 更新成功: {tweet_id} -> {token_tag}")
                    else:
                        logger.warning(f"  ⚠️ 更新失败: {tweet_id}")
                        error_count += 1
                else:
                    no_token_count += 1
                    logger.debug(f"  ⊘ 未提取到token: {tweet_id}")

            except Exception as e:
                error_count += 1
                logger.error(f"  ❌ 处理推文 {tweet_id} 失败: {e}")
                continue

        logger.info("=" * 60)
        logger.info(f"批量提取完成！")
        logger.info(f"  总计处理: {len(tweets_result)} 条")
        logger.info(f"  ✅ 成功更新: {updated_count} 条")
        logger.info(f"  ⊘ 跳过（已有token_tag）: {skipped_count} 条")
        logger.info(f"  ⊘ 无token: {no_token_count} 条")
        logger.info(f"  ❌ 失败: {error_count} 条")
        logger.info("=" * 60)

        # 验证更新结果
        verify_update_results(logger, days)

    except Exception as e:
        logger.error(f"批量提取失败: {e}")
        import traceback
        traceback.print_exc()


def verify_update_results(logger, days: int = 7):
    """验证更新结果"""
    logger.info("验证更新结果...")

    try:
        # 统计最近N天非项目推文的token_tag情况
        stats_sql = """
        SELECT
            COUNT(*) as total_tweets,
            COUNT(CASE WHEN token_tag IS NOT NULL AND token_tag != '' THEN 1 END) as has_token_tag,
            COUNT(CASE WHEN token_tag IS NULL OR token_tag = '' THEN 1 END) as no_token_tag
        FROM twitter_tweet
        WHERE project_id IS NULL
        AND update_time >= DATE_SUB(NOW(), INTERVAL %s DAY)
        """

        stats_result = tweet_dao.db_manager.execute_query(stats_sql, [days])

        if stats_result:
            stats = stats_result[0]
            logger.info(f"验证结果（最近{days}天非项目推文）:")
            logger.info(f"  总推文数: {stats['total_tweets']}")
            logger.info(f"  有token_tag: {stats['has_token_tag']}")
            logger.info(f"  无token_tag: {stats['no_token_tag']}")

            coverage_rate = (stats['has_token_tag'] / stats['total_tweets']) * 100 if stats['total_tweets'] > 0 else 0
            logger.info(f"  覆盖率: {coverage_rate:.1f}%")

        # 显示最近提取的token样本
        sample_sql = """
        SELECT id_str, full_text, token_tag, update_time
        FROM twitter_tweet
        WHERE project_id IS NULL
        AND token_tag IS NOT NULL
        AND token_tag != ''
        ORDER BY update_time DESC
        LIMIT 10
        """

        sample_result = tweet_dao.db_manager.execute_query(sample_sql)

        if sample_result:
            logger.info("最近提取的token样本:")
            for row in sample_result:
                logger.info(f"  [{row['token_tag']}] {row['full_text'][:50]}...")

        # 统计最常见的token
        token_stats_sql = """
        SELECT token_tag, COUNT(*) as count
        FROM twitter_tweet
        WHERE project_id IS NULL
        AND token_tag IS NOT NULL
        AND token_tag != ''
        AND update_time >= DATE_SUB(NOW(), INTERVAL %s DAY)
        GROUP BY token_tag
        ORDER BY count DESC
        LIMIT 10
        """

        token_stats_result = tweet_dao.db_manager.execute_query(token_stats_sql, [days])

        if token_stats_result:
            logger.info(f"最常见的token（最近{days}天）:")
            for row in token_stats_result:
                logger.info(f"  {row['token_tag']}: {row['count']} 条推文")

    except Exception as e:
        logger.error(f"验证结果失败: {e}")


if __name__ == '__main__':
    # 可以通过命令行参数指定天数
    import argparse

    parser = argparse.ArgumentParser(description='批量提取推文的token_tag')
    parser.add_argument('--days', type=int, default=7, help='处理最近几天的数据（默认7天）')
    parser.add_argument('--force', action='store_true', help='强制重新提取（即使已有token_tag）')

    args = parser.parse_args()

    if args.force:
        print("⚠️ 警告: 强制模式未实现，请修改代码注释掉跳过逻辑")

    batch_extract_token_tags(days=args.days)
