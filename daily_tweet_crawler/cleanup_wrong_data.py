#!/usr/bin/env python3
"""
清理错误保存到 twitter_tweet 表的项目推文数据
"""
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.database.connection import db_manager
from src.utils.logger import get_logger

logger = get_logger(__name__)

def check_wrong_data():
    """检查错误保存的数据"""
    try:
        sql = """
        SELECT COUNT(*) as count,
               MIN(created_at_datetime) as earliest,
               MAX(created_at_datetime) as latest,
               MIN(update_time) as first_update,
               MAX(update_time) as last_update
        FROM twitter_tweet
        WHERE update_time >= '2025-12-26 21:40:00'
          AND update_time <= '2025-12-26 21:45:00'
        """
        results = db_manager.execute_query(sql)

        if results:
            row = results[0]
            logger.info(f"发现错误数据: {row['count']} 条")
            logger.info(f"推文时间范围: {row['earliest']} ~ {row['latest']}")
            logger.info(f"入库时间范围: {row['first_update']} ~ {row['last_update']}")
            return row['count']

        return 0

    except Exception as e:
        logger.error(f"检查错误数据失败: {e}")
        return 0


def delete_wrong_data():
    """删除错误保存的数据"""
    try:
        # 先检查要删除的数据
        count = check_wrong_data()

        if count == 0:
            logger.info("没有找到需要删除的错误数据")
            return True

        logger.info(f"准备删除 {count} 条错误数据...")

        # 执行删除
        sql = """
        DELETE FROM twitter_tweet
        WHERE update_time >= '2025-12-26 21:40:00'
          AND update_time <= '2025-12-26 21:45:00'
        """

        affected_rows = db_manager.execute_update(sql)
        logger.info(f"成功删除 {affected_rows} 条错误数据")

        # 再次检查
        remaining = check_wrong_data()
        if remaining == 0:
            logger.info("✅ 错误数据已全部清理完成")
            return True
        else:
            logger.warning(f"⚠️ 仍有 {remaining} 条数据未清理")
            return False

    except Exception as e:
        logger.error(f"删除错误数据失败: {e}")
        return False


if __name__ == '__main__':
    logger.info("=" * 50)
    logger.info("开始清理错误数据")
    logger.info("=" * 50)

    success = delete_wrong_data()

    if success:
        logger.info("数据清理完成")
        sys.exit(0)
    else:
        logger.error("数据清理失败")
        sys.exit(1)
