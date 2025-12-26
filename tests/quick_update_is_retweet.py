#!/usr/bin/env python3
"""
快速更新指定推文的is_retweet字段
适用于少量推文的手动更新
"""
import sys
from pathlib import Path
from datetime import datetime

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.database.connection import db_manager
from src.utils.logger import get_logger


def update_is_retweet(tweet_id: str, is_retweet: bool, table_name: str = "twitter_tweet_project_new"):
    """
    更新单条推文的is_retweet字段

    Args:
        tweet_id: 推文ID
        is_retweet: 是否为转发 (True/False)
        table_name: 表名

    Returns:
        是否成功
    """
    logger = get_logger(__name__)

    try:
        sql = f"""
        UPDATE {table_name}
        SET is_retweet = %s, update_time = %s
        WHERE id_str = %s
        """

        params = (is_retweet, datetime.now(), tweet_id)
        affected_rows = db_manager.execute_update(sql, params)

        if affected_rows > 0:
            logger.info(f"✓ 成功更新推文 {tweet_id}: is_retweet={is_retweet}")
            return True
        else:
            logger.warning(f"✗ 推文 {tweet_id} 不存在或未更新")
            return False

    except Exception as e:
        logger.error(f"✗ 更新推文 {tweet_id} 失败: {e}")
        return False


def batch_update(updates: list, table_name: str = "twitter_tweet_project_new"):
    """
    批量更新推文的is_retweet字段

    Args:
        updates: 更新列表，格式为 [{'tweet_id': 'xxx', 'is_retweet': True/False}, ...]
        table_name: 表名
    """
    logger = get_logger(__name__)

    logger.info("=" * 50)
    logger.info(f"开始批量更新{len(updates)}条推文的is_retweet字段")
    logger.info(f"目标表: {table_name}")
    logger.info("=" * 50)

    success_count = 0
    fail_count = 0

    for update in updates:
        tweet_id = update.get('tweet_id')
        is_retweet = update.get('is_retweet')

        if not tweet_id:
            logger.warning(f"跳过无效记录: {update}")
            fail_count += 1
            continue

        # 转换is_retweet为布尔值
        if isinstance(is_retweet, str):
            is_retweet = is_retweet.lower() in ['true', '1', 'yes', 'y']

        success = update_is_retweet(tweet_id, is_retweet, table_name)

        if success:
            success_count += 1
        else:
            fail_count += 1

    # 显示统计信息
    logger.info("=" * 50)
    logger.info("更新统计:")
    logger.info(f"  总数: {len(updates)}")
    logger.info(f"  成功: {success_count}")
    logger.info(f"  失败: {fail_count}")
    logger.info("=" * 50)

    return success_count, fail_count


def verify_updates(tweet_ids: list, table_name: str = "twitter_tweet_project_new"):
    """
    验证更新结果

    Args:
        tweet_ids: 推文ID列表
        table_name: 表名
    """
    logger = get_logger(__name__)

    logger.info("=" * 50)
    logger.info("验证更新结果:")
    logger.info("=" * 50)

    for tweet_id in tweet_ids:
        try:
            sql = f"""
            SELECT id_str, full_text, is_retweet, is_quote_status, update_time
            FROM {table_name}
            WHERE id_str = %s
            """

            results = db_manager.execute_query(sql, (tweet_id,))

            if results:
                row = results[0]
                logger.info(f"推文ID: {row['id_str']}")
                logger.info(f"  is_retweet: {row.get('is_retweet', 'NULL')}")
                logger.info(f"  is_quote_status: {row.get('is_quote_status', 'NULL')}")
                logger.info(f"  update_time: {row.get('update_time', 'NULL')}")
                logger.info(f"  内容: {row.get('full_text', '')[:50]}...")
                logger.info("-" * 50)
            else:
                logger.warning(f"推文 {tweet_id} 不存在")

        except Exception as e:
            logger.error(f"查询推文 {tweet_id} 失败: {e}")


def main():
    """主函数 - 示例用法"""
    logger = get_logger(__name__)

    # ===== 配置区域 - 在这里修改你的数据 =====

    # 方案1: 批量更新（推荐）
    updates = [
        # 格式: {'tweet_id': '推文ID', 'is_retweet': True/False}
        # 示例：
        # {'tweet_id': '1866383947028394466', 'is_retweet': False},
        # {'tweet_id': '1866383947028394467', 'is_retweet': True},
        # {'tweet_id': '1866383947028394468', 'is_retweet': False},
    ]

    # 目标表名
    table_name = "twitter_tweet_project_new"

    # ===== 配置结束 =====

    # 测试数据库连接
    logger.info("测试数据库连接...")
    if not db_manager.test_connection():
        logger.error("数据库连接失败，请检查配置")
        sys.exit(1)

    logger.info("✓ 数据库连接成功")

    if not updates:
        logger.warning("没有配置需要更新的数据")
        logger.info("请编辑此文件，在 updates 列表中添加需要更新的推文")
        logger.info("示例:")
        logger.info("  updates = [")
        logger.info("      {'tweet_id': '1866383947028394466', 'is_retweet': False},")
        logger.info("      {'tweet_id': '1866383947028394467', 'is_retweet': True},")
        logger.info("  ]")
        sys.exit(0)

    # 执行批量更新
    success_count, fail_count = batch_update(updates, table_name)

    # 验证更新结果
    tweet_ids = [u['tweet_id'] for u in updates if u.get('tweet_id')]
    verify_updates(tweet_ids, table_name)

    if fail_count == 0:
        logger.info("✓ 所有推文更新成功")
        sys.exit(0)
    else:
        logger.warning(f"⚠ 部分推文更新失败 (失败: {fail_count})")
        sys.exit(1)


if __name__ == '__main__':
    # 命令行快速更新（无需修改代码）
    import argparse

    parser = argparse.ArgumentParser(description='快速更新推文的is_retweet字段')
    parser.add_argument('--tweet-id', help='推文ID')
    parser.add_argument('--is-retweet', choices=['true', 'false', '1', '0'],
                       help='是否为转发 (true/false/1/0)')
    parser.add_argument('--table', default='twitter_tweet_project_new',
                       help='表名 (默认: twitter_tweet_project_new)')
    parser.add_argument('--verify', nargs='+', help='验证指定推文ID的更新结果')

    args = parser.parse_args()

    if args.verify:
        # 验证模式
        verify_updates(args.verify, args.table)
    elif args.tweet_id and args.is_retweet:
        # 单条更新模式
        is_retweet = args.is_retweet.lower() in ['true', '1']
        logger = get_logger(__name__)

        logger.info("测试数据库连接...")
        if not db_manager.test_connection():
            logger.error("数据库连接失败")
            sys.exit(1)

        success = update_is_retweet(args.tweet_id, is_retweet, args.table)
        verify_updates([args.tweet_id], args.table)

        sys.exit(0 if success else 1)
    else:
        # 批量更新模式（使用配置）
        main()
