"""
检查过去4天的KOL推文数据回填入库情况
"""
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

try:
    from src.database.connection import DatabaseManager
    import pymysql
except ImportError as e:
    print(f"❌ 导入模块失败: {e}")
    print("请确保在项目虚拟环境中运行此脚本")
    sys.exit(1)


def check_backfill_data():
    """检查过去4天的回填数据入库情况"""
    print("\n" + "=" * 80)
    print("📊 KOL推文数据回填入库情况检查 - 过去4天")
    print("=" * 80)
    print(f"检查时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    try:
        # 测试连接
        print("\n1️⃣ 测试数据库连接...")
        db_manager = DatabaseManager()
        print("✅ 数据库连接成功")

        # 获取过去5天的日期范围（包括今天）
        today = datetime.now()
        dates = [(today - timedelta(days=i)).strftime('%Y-%m-%d') for i in range(4, -1, -1)]

        print(f"\n📅 检查日期范围: {dates[0]} 至 {dates[-1]}")
        print("\n2️⃣ 检查每天的数据入库情况...")
        print("-" * 80)

        total_tweets = 0
        daily_stats = []

        for date_str in dates:
            # 查询当天的推文数量
            query = """
            SELECT
                COUNT(*) as tweet_count,
                COUNT(DISTINCT kol_id) as kol_count,
                SUM(CASE WHEN is_valid = 1 THEN 1 ELSE 0 END) as valid_count,
                SUM(CASE WHEN is_valid = 0 THEN 1 ELSE 0 END) as invalid_count,
                MIN(created_at) as earliest_tweet,
                MAX(created_at) as latest_tweet
            FROM twitter_tweet
            WHERE DATE(created_at) = %s
            """

            results = db_manager.execute_query(query, (date_str,))
            result = results[0] if results else None

            if result and result['tweet_count'] > 0:
                stats = {
                    'date': date_str,
                    'tweet_count': result['tweet_count'],
                    'kol_count': result['kol_count'],
                    'valid_count': result['valid_count'],
                    'invalid_count': result['invalid_count'],
                    'earliest': result['earliest_tweet'],
                    'latest': result['latest_tweet']
                }
                daily_stats.append(stats)
                total_tweets += result['tweet_count']

                # 判断是否是今天
                is_today = date_str == today.strftime('%Y-%m-%d')
                day_label = "（今天）" if is_today else ""

                print(f"\n📅 {date_str} {day_label}")
                print(f"   推文总数: {result['tweet_count']:,} 条")
                print(f"   KOL数量: {result['kol_count']:,} 人")
                print(f"   有效推文: {result['valid_count']:,} 条 ({result['valid_count']/result['tweet_count']*100:.1f}%)")
                print(f"   无效推文: {result['invalid_count']:,} 条")
                if result['earliest_tweet']:
                    print(f"   时间范围: {result['earliest_tweet']} ~ {result['latest_tweet']}")
            else:
                print(f"\n📅 {date_str}")
                print(f"   ⚠️  无数据")
                daily_stats.append({
                    'date': date_str,
                    'tweet_count': 0,
                    'kol_count': 0,
                    'valid_count': 0,
                    'invalid_count': 0
                })

        # 汇总统计
        print("\n" + "=" * 80)
        print("📈 汇总统计（过去5天，包括今天）")
        print("=" * 80)
        print(f"总推文数: {total_tweets:,} 条")

        if daily_stats:
            days_with_data = [s for s in daily_stats if s['tweet_count'] > 0]
            if days_with_data:
                avg_per_day = total_tweets / len(days_with_data)
                print(f"有数据天数: {len(days_with_data)} 天")
                print(f"平均每天: {avg_per_day:,.0f} 条")

        # 检查每个KOL的数据
        print("\n3️⃣ 检查各KOL的数据分布（过去5天）...")
        print("-" * 80)

        # 查询过去5天每个KOL的推文数
        query = """
        SELECT
            k.name as kol_name,
            k.handle as kol_handle,
            COUNT(*) as tweet_count,
            MIN(t.created_at) as earliest,
            MAX(t.created_at) as latest,
            SUM(CASE WHEN t.is_valid = 1 THEN 1 ELSE 0 END) as valid_count
        FROM twitter_tweet t
        LEFT JOIN twitter_kol k ON t.kol_id = k.id
        WHERE DATE(t.created_at) >= %s
        GROUP BY t.kol_id, k.name, k.handle
        HAVING tweet_count > 0
        ORDER BY tweet_count DESC
        LIMIT 20
        """

        earliest_date = (today - timedelta(days=4)).strftime('%Y-%m-%d')
        kol_stats = db_manager.execute_query(query, (earliest_date,))

        if kol_stats:
            print(f"\nTop 20 KOL推文数:\n")
            for i, stat in enumerate(kol_stats, 1):
                kol_name = stat['kol_name'] or '未知'
                kol_handle = stat['kol_handle'] or '未知'
                valid_pct = stat['valid_count']/stat['tweet_count']*100 if stat['tweet_count'] > 0 else 0
                print(f"{i:2d}. @{kol_handle:20s} ({kol_name:15s}) - {stat['tweet_count']:4d} 条 (有效{valid_pct:.0f}%)")
                if i <= 5 and stat['earliest']:  # 只显示前5个的时间范围
                    print(f"     时间: {stat['earliest']} ~ {stat['latest']}")

        # 检查是否有缺失的日期
        print("\n4️⃣ 数据完整性检查...")
        print("-" * 80)

        missing_days = [s['date'] for s in daily_stats if s['tweet_count'] == 0]
        if missing_days:
            print(f"⚠️  以下日期无数据: {', '.join(missing_days)}")
            print(f"   可能原因：")
            print(f"   1. 爬虫服务未运行")
            print(f"   2. API调用失败")
            print(f"   3. 数据库连接问题")
        else:
            print("✅ 所有日期都有数据")

        # 检查数据更新时间
        print("\n5️⃣ 最近更新时间...")
        print("-" * 80)

        query = """
        SELECT
            MAX(created_at) as latest_tweet_time,
            MAX(update_time) as latest_update_time,
            COUNT(*) as total_count
        FROM twitter_tweet
        WHERE DATE(created_at) >= %s
        """
        results = db_manager.execute_query(query, (earliest_date,))
        result = results[0] if results else None

        if result:
            print(f"过去5天总计: {result['total_count']:,} 条推文")

            if result['latest_tweet_time']:
                print(f"\n最新推文时间: {result['latest_tweet_time']}")
                time_diff = datetime.now() - result['latest_tweet_time']
                hours_ago = time_diff.total_seconds() / 3600

                if hours_ago < 24:
                    print(f"距现在: {hours_ago:.1f} 小时前")
                else:
                    days_ago = hours_ago / 24
                    print(f"距现在: {days_ago:.1f} 天前")

                if hours_ago > 2:
                    print(f"⚠️  最新数据距现在已超过 {hours_ago:.1f} 小时")
                    print(f"   建议检查爬虫服务状态:")
                    print(f"   cd /Users/qmk/Documents/QC/twitter/Carlwang/daily_kol_tweet_crawler")
                    print(f"   ./start_service_kol_tweet.sh status")
                else:
                    print("✅ 数据更新及时")

            if result['latest_update_time']:
                print(f"\n最新入库时间: {result['latest_update_time']}")

        # 检查项目分类情况
        print("\n6️⃣ 项目分类统计（过去5天）...")
        print("-" * 80)

        query = """
        SELECT
            project_tag,
            COUNT(*) as count
        FROM twitter_tweet
        WHERE DATE(created_at) >= %s
            AND project_tag IS NOT NULL
            AND project_tag != ''
        GROUP BY project_tag
        ORDER BY count DESC
        LIMIT 10
        """
        project_stats = db_manager.execute_query(query, (earliest_date,))

        if project_stats:
            print(f"\nTop 10 项目提及次数:\n")
            for i, stat in enumerate(project_stats, 1):
                print(f"{i:2d}. {stat['project_tag']:20s} - {stat['count']:4d} 次")
        else:
            print("暂无项目标签数据")

        print("\n" + "=" * 80)
        print("✅ 检查完成")
        print("=" * 80)

        # 返回汇总信息
        return {
            'total_tweets': total_tweets,
            'daily_stats': daily_stats,
            'missing_days': missing_days
        }

    except Exception as e:
        print(f"\n❌ 检查失败: {e}")
        import traceback
        traceback.print_exc()
        return None


if __name__ == "__main__":
    result = check_backfill_data()

    if result:
        # 简单的结论
        print("\n📝 结论:")
        if result['total_tweets'] > 0:
            print(f"✅ 过去5天共入库 {result['total_tweets']:,} 条推文数据")
            if result['missing_days']:
                print(f"⚠️  有 {len(result['missing_days'])} 天数据缺失: {', '.join(result['missing_days'])}")
            else:
                print("✅ 数据完整，无缺失")
        else:
            print("❌ 无数据入库，请检查爬虫服务状态")
