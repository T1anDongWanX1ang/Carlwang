#!/usr/bin/env python3
"""
删除历史错误数据（2025-12-25 00:00:00 之后的所有数据）
"""
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.database.connection import db_manager
from src.utils.logger import get_logger

logger = get_logger(__name__)

def delete_historical_data():
    """删除历史数据"""
    try:
        # 1. 先检查要删除的数据量
        check_sql = """
        SELECT COUNT(*) as count
        FROM twitter_tweet_back_test_cmc300
        WHERE update_time >= '2025-12-25 00:00:00'
        """

        result = db_manager.execute_query(check_sql)
        if result:
            count = result[0]['count']
            logger.info("=" * 70)
            logger.info("准备删除历史错误数据")
            logger.info("=" * 70)
            logger.info(f"将要删除 {count} 条记录（2025-12-25 00:00:00 之后）")
            logger.info("")

            # 2. 确认删除
            response = input("确认删除？输入 'YES' 继续: ")
            if response != 'YES':
                logger.info("取消删除操作")
                return False

            # 3. 执行删除
            delete_sql = """
            DELETE FROM twitter_tweet_back_test_cmc300
            WHERE update_time >= '2025-12-25 00:00:00'
            """

            affected = db_manager.execute_update(delete_sql)
            logger.info(f"✅ 成功删除 {affected} 条记录")

            # 4. 验证删除
            verify_sql = """
            SELECT COUNT(*) as remaining
            FROM twitter_tweet_back_test_cmc300
            WHERE update_time >= '2025-12-25 00:00:00'
            """

            verify_result = db_manager.execute_query(verify_sql)
            if verify_result:
                remaining = verify_result[0]['remaining']
                if remaining == 0:
                    logger.info("✅ 数据删除验证通过，没有残留数据")
                else:
                    logger.warning(f"⚠️  仍有 {remaining} 条记录未删除")

            return True

    except Exception as e:
        logger.error(f"删除数据失败: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False

if __name__ == '__main__':
    logger.info("开始删除历史错误数据...")
    success = delete_historical_data()

    if success:
        logger.info("=" * 70)
        logger.info("✅ 历史数据删除完成")
        logger.info("=" * 70)
        logger.info("下一步:")
        logger.info("1. 运行重新爬取脚本")
        logger.info("2. 验证新数据质量")
        sys.exit(0)
    else:
        logger.error("❌ 删除失败")
        sys.exit(1)
