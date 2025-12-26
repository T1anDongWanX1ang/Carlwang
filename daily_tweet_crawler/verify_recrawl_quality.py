#!/usr/bin/env python3
"""
验证重新爬取后的数据质量
"""
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.database.connection import db_manager
from src.utils.logger import get_logger

logger = get_logger(__name__)

def verify_recrawled_data():
    """验证重新爬取的数据质量"""
    try:
        logger.info("=" * 80)
        logger.info("开始验证重新爬取的数据质量")
        logger.info("=" * 80)
        logger.info("")

        # 1. 总体统计
        sql1 = """
        SELECT
            COUNT(*) as total,
            MIN(update_time) as earliest,
            MAX(update_time) as latest
        FROM twitter_tweet_back_test_cmc300
        WHERE update_time >= '2025-12-25 00:00:00'
        """

        result1 = db_manager.execute_query(sql1)
        if result1:
            r = result1[0]
            logger.info(f"📊 总体统计:")
            logger.info(f"  总记录数: {r['total']} 条")
            logger.info(f"  时间范围: {r['earliest']} 到 {r['latest']}")
            logger.info("")

        # 2. 字段完整性检查
        sql2 = """
        SELECT
            COUNT(*) as total,
            SUM(CASE WHEN user_id IS NULL THEN 1 ELSE 0 END) as null_user_id,
            SUM(CASE WHEN user_name IS NULL THEN 1 ELSE 0 END) as null_user_name,
            SUM(CASE WHEN sentiment IS NULL THEN 1 ELSE 0 END) as null_sentiment,
            SUM(CASE WHEN is_retweet IS NULL THEN 1 ELSE 0 END) as null_is_retweet
        FROM twitter_tweet_back_test_cmc300
        WHERE update_time >= '2025-12-25 00:00:00'
        """

        result2 = db_manager.execute_query(sql2)
        if result2:
            r = result2[0]
            total = r['total']
            logger.info("✅ 字段完整性检查:")
            logger.info(f"  user_id 为空: {r['null_user_id']} 条 ({r['null_user_id']/total*100:.1f}%)")
            logger.info(f"  user_name 为空: {r['null_user_name']} 条 ({r['null_user_name']/total*100:.1f}%)")
            logger.info(f"  sentiment 为空: {r['null_sentiment']} 条 ({r['null_sentiment']/total*100:.1f}%)")
            logger.info(f"  is_retweet 为空: {r['null_is_retweet']} 条 ({r['null_is_retweet']/total*100:.1f}%)")
            logger.info("")

            # 判断是否通过
            if r['null_user_id'] == 0 and r['null_user_name'] == 0:
                logger.info("  ✅ user_id 和 user_name 字段完整性检查通过")
            else:
                logger.warning("  ⚠️  user_id 或 user_name 仍有空值，需要检查")

        # 3. is_retweet 字段分布
        sql3 = """
        SELECT
            is_retweet,
            COUNT(*) as count
        FROM twitter_tweet_back_test_cmc300
        WHERE update_time >= '2025-12-25 00:00:00'
        GROUP BY is_retweet
        ORDER BY is_retweet
        """

        result3 = db_manager.execute_query(sql3)
        if result3:
            logger.info("📊 is_retweet 字段分布:")
            for r in result3:
                logger.info(f"  is_retweet={r['is_retweet']}: {r['count']} 条")
            logger.info("")

            # 判断是否有转发推文
            has_retweets = any(r['is_retweet'] == 1 for r in result3)
            if has_retweets:
                logger.info("  ✅ 检测到转发推文，is_retweet 字段工作正常")
            else:
                logger.info("  ℹ️  未检测到转发推文（可能确实没有转发，或需要进一步检查）")

        # 4. summary 字段统计
        sql4 = """
        SELECT
            COUNT(*) as total,
            SUM(CASE WHEN summary IS NOT NULL THEN 1 ELSE 0 END) as has_summary,
            SUM(CASE WHEN isAnnounce = 1 THEN 1 ELSE 0 END) as announcement_count,
            SUM(CASE WHEN is_activity = 1 THEN 1 ELSE 0 END) as activity_count
        FROM twitter_tweet_back_test_cmc300
        WHERE update_time >= '2025-12-25 00:00:00'
        """

        result4 = db_manager.execute_query(sql4)
        if result4:
            r = result4[0]
            logger.info("📊 AI 分析字段统计:")
            logger.info(f"  有 summary 的推文: {r['has_summary']} 条 ({r['has_summary']/r['total']*100:.1f}%)")
            logger.info(f"  公告类推文 (isAnnounce=1): {r['announcement_count']} 条")
            logger.info(f"  活动类推文 (is_activity=1): {r['activity_count']} 条")
            logger.info("")

            if r['has_summary'] > 0:
                logger.info("  ✅ summary 字段生成正常")
            else:
                logger.warning("  ⚠️  没有生成任何 summary，需要检查 Gemini API")

        # 5. sentiment 字段分布
        sql5 = """
        SELECT
            sentiment,
            COUNT(*) as count
        FROM twitter_tweet_back_test_cmc300
        WHERE update_time >= '2025-12-25 00:00:00'
        GROUP BY sentiment
        ORDER BY count DESC
        """

        result5 = db_manager.execute_query(sql5)
        if result5:
            logger.info("📊 sentiment 字段分布:")
            for r in result5:
                logger.info(f"  {r['sentiment']}: {r['count']} 条")
            logger.info("")

        # 6. 按小时统计
        sql6 = """
        SELECT
            DATE_FORMAT(update_time, '%Y-%m-%d %H:00') as hour_group,
            COUNT(*) as count
        FROM twitter_tweet_back_test_cmc300
        WHERE update_time >= '2025-12-25 00:00:00'
        GROUP BY hour_group
        ORDER BY hour_group
        """

        result6 = db_manager.execute_query(sql6)
        if result6:
            logger.info("📊 按小时入库统计:")
            for r in result6:
                logger.info(f"  {r['hour_group']}: {r['count']} 条")
            logger.info("")

        # 7. 最终评估
        logger.info("=" * 80)
        logger.info("📋 验证总结:")
        logger.info("=" * 80)

        # 获取总体指标
        overall_sql = """
        SELECT
            COUNT(*) as total,
            SUM(CASE WHEN user_id IS NULL THEN 1 ELSE 0 END) as null_user_id,
            SUM(CASE WHEN user_name IS NULL THEN 1 ELSE 0 END) as null_user_name,
            SUM(CASE WHEN is_retweet = 1 THEN 1 ELSE 0 END) as retweet_count,
            SUM(CASE WHEN summary IS NOT NULL THEN 1 ELSE 0 END) as has_summary
        FROM twitter_tweet_back_test_cmc300
        WHERE update_time >= '2025-12-25 00:00:00'
        """

        overall_result = db_manager.execute_query(overall_sql)
        if overall_result:
            o = overall_result[0]

            issues = []
            if o['null_user_id'] > 0 or o['null_user_name'] > 0:
                issues.append("❌ user_id/user_name 存在空值")
            else:
                logger.info("✅ user_id/user_name 字段完整")

            if o['retweet_count'] == 0:
                logger.info("ℹ️  未检测到转发推文（可能正常）")
            else:
                logger.info(f"✅ is_retweet 字段正常（检测到 {o['retweet_count']} 条转发）")

            if o['has_summary'] > 0:
                logger.info(f"✅ summary 字段生成正常（{o['has_summary']} 条）")
            else:
                issues.append("⚠️  summary 未生成")

            if not issues:
                logger.info("")
                logger.info("🎉 所有检查通过！数据质量良好！")
                return True
            else:
                logger.info("")
                logger.warning("存在以下问题:")
                for issue in issues:
                    logger.warning(f"  {issue}")
                return False

    except Exception as e:
        logger.error(f"验证失败: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False

if __name__ == '__main__':
    success = verify_recrawled_data()
    sys.exit(0 if success else 1)
