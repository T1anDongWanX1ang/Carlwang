#!/usr/bin/env python3
"""
验证activity_detail字段映射是否正确工作
"""
import sys
import json
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.database.connection import db_manager
from src.utils.logger import get_logger


def verify_activity_detail_field():
    """验证activity_detail字段"""
    logger = get_logger(__name__)

    logger.info("=" * 60)
    logger.info("验证 activity_detail 字段映射")
    logger.info("=" * 60)

    try:
        # 1. 检查字段是否存在
        logger.info("\n1. 检查数据库表结构...")
        sql = "DESCRIBE twitter_tweet"
        results = db_manager.execute_query(sql)

        field_names = [row['Field'] for row in results]

        if 'activity_detail' in field_names:
            logger.info("✓ activity_detail 字段存在")

            # 获取字段详情
            for row in results:
                if row['Field'] == 'activity_detail':
                    logger.info(f"  类型: {row['Type']}")
                    logger.info(f"  允许NULL: {row['Null']}")
                    logger.info(f"  默认值: {row.get('Default', 'NULL')}")
        else:
            logger.error("✗ activity_detail 字段不存在！")
            return False

        # 2. 检查活动推文统计
        logger.info("\n2. 检查活动推文统计...")
        sql = """
        SELECT
            COUNT(*) as total_activities,
            SUM(CASE WHEN activity_detail IS NOT NULL THEN 1 ELSE 0 END) as with_detail,
            SUM(CASE WHEN activity_detail IS NULL THEN 1 ELSE 0 END) as without_detail
        FROM twitter_tweet
        WHERE is_activity = 1
        """

        results = db_manager.execute_query(sql)
        if results:
            stats = results[0]
            logger.info(f"  活动推文总数: {stats['total_activities']}")
            logger.info(f"  有activity_detail数据: {stats['with_detail']}")
            logger.info(f"  无activity_detail数据: {stats['without_detail']}")

        # 3. 查看activity_detail数据样例
        logger.info("\n3. 查看activity_detail数据样例...")
        sql = """
        SELECT id_str, is_activity, activity_detail
        FROM twitter_tweet
        WHERE is_activity = 1 AND activity_detail IS NOT NULL
        LIMIT 3
        """

        results = db_manager.execute_query(sql)
        if results:
            logger.info(f"  找到 {len(results)} 条样例数据:\n")
            for i, row in enumerate(results, 1):
                logger.info(f"  样例 {i}:")
                logger.info(f"    推文ID: {row['id_str']}")
                logger.info(f"    activity_detail类型: {type(row['activity_detail'])}")

                # 尝试解析JSON
                try:
                    if isinstance(row['activity_detail'], str):
                        data = json.loads(row['activity_detail'])
                    elif isinstance(row['activity_detail'], dict):
                        data = row['activity_detail']
                    else:
                        logger.warning(f"    未知的数据类型: {type(row['activity_detail'])}")
                        continue

                    logger.info(f"    ✓ JSON解析成功")
                    logger.info(f"      标题: {data.get('title', 'N/A')}")
                    logger.info(f"      状态: {data.get('status', 'N/A')}")
                    logger.info(f"      摘要: {data.get('summary', 'N/A')[:50]}...")
                    logger.info(f"      链接: {data.get('url', 'N/A')}")

                except Exception as e:
                    logger.error(f"    ✗ JSON解析失败: {e}")
                    logger.error(f"    原始数据: {row['activity_detail']}")

                logger.info("")
        else:
            logger.warning("  暂无activity_detail数据样例")
            logger.info("  提示: 运行 python backfill_activities_48h.py 来生成数据")

        # 4. 总结
        logger.info("\n" + "=" * 60)
        logger.info("验证完成!")
        logger.info("=" * 60)
        logger.info("\n建议:")
        logger.info("1. 如果没有activity_detail数据，运行回填脚本:")
        logger.info("   python backfill_activities_48h.py --hours 48")
        logger.info("")
        logger.info("2. 启动主爬虫自动处理新推文:")
        logger.info("   python main.py --mode schedule --interval 5")
        logger.info("")

        return True

    except Exception as e:
        logger.error(f"验证失败: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False


if __name__ == '__main__':
    success = verify_activity_detail_field()
    sys.exit(0 if success else 1)
