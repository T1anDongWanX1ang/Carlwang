"""
简化检查：查看数据库中的数据情况
"""
import sys
from pathlib import Path
from datetime import datetime, timedelta

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.database.connection import DatabaseManager

def simple_check():
    print("\n" + "=" * 80)
    print("🔍 简化检查 - 数据库推文数据总览")
    print("=" * 80)

    db_manager = DatabaseManager()

    # 1. 查询总数
    print("\n1️⃣ 推文总数:")
    query = "SELECT COUNT(*) as total FROM twitter_tweet"
    results = db_manager.execute_query(query)
    if results:
        print(f"   总计: {results[0]['total']:,} 条")

    # 2. 查询最新数据
    print("\n2️⃣ 最新推文:")
    query = """
    SELECT created_at, full_text, kol_id
    FROM twitter_tweet
    ORDER BY created_at DESC
    LIMIT 5
    """
    results = db_manager.execute_query(query)
    if results:
        for i, row in enumerate(results, 1):
            text = row['full_text'][:50] if row['full_text'] else 'N/A'
            print(f"   {i}. {row['created_at']} - KOL ID: {row['kol_id']} - {text}...")
    else:
        print("   无数据")

    # 3. 查询最旧数据
    print("\n3️⃣ 最旧推文:")
    query = """
    SELECT created_at, full_text, kol_id
    FROM twitter_tweet
    ORDER BY created_at ASC
    LIMIT 5
    """
    results = db_manager.execute_query(query)
    if results:
        for i, row in enumerate(results, 1):
            text = row['full_text'][:50] if row['full_text'] else 'N/A'
            print(f"   {i}. {row['created_at']} - KOL ID: {row['kol_id']} - {text}...")

    # 4. 按日期统计最近30天
    print("\n4️⃣ 最近30天每天数据量:")
    query = """
    SELECT DATE(created_at) as date, COUNT(*) as count
    FROM twitter_tweet
    WHERE created_at >= DATE_SUB(NOW(), INTERVAL 30 DAY)
    GROUP BY DATE(created_at)
    ORDER BY date DESC
    LIMIT 30
    """
    results = db_manager.execute_query(query)
    if results:
        print(f"   找到 {len(results)} 天有数据:\n")
        for row in results:
            print(f"   {row['date']}: {row['count']:,} 条")
    else:
        print("   ⚠️  最近30天无数据")

    # 5. 检查是否有今年的数据
    print("\n5️⃣ 2026年数据检查:")
    query = """
    SELECT COUNT(*) as count
    FROM twitter_tweet
    WHERE YEAR(created_at) = 2026
    """
    results = db_manager.execute_query(query)
    if results:
        count_2026 = results[0]['count']
        print(f"   2026年数据: {count_2026:,} 条")

        if count_2026 == 0:
            print("\n   ⚠️  2026年没有数据！")
            print("   可能原因：")
            print("   1. 爬虫服务未运行或已停止")
            print("   2. 回填脚本未执行")
            print("   3. 数据入库失败")

    # 6. 检查最近插入的数据（按update_time或insert_time）
    print("\n6️⃣ 检查最近入库时间:")
    try:
        query = """
        SELECT MAX(update_time) as latest_update, COUNT(*) as count
        FROM twitter_tweet
        WHERE update_time IS NOT NULL
        """
        results = db_manager.execute_query(query)
        if results and results[0]['latest_update']:
            print(f"   最新入库时间: {results[0]['latest_update']}")
            time_diff = datetime.now() - results[0]['latest_update']
            hours_ago = time_diff.total_seconds() / 3600
            print(f"   距现在: {hours_ago:.1f} 小时前")

            if hours_ago > 24:
                print(f"\n   ⚠️  数据已超过24小时未更新！")
    except Exception as e:
        print(f"   无法查询update_time字段: {e}")

    print("\n" + "=" * 80)
    print("✅ 检查完成")
    print("=" * 80)

if __name__ == "__main__":
    try:
        simple_check()
    except Exception as e:
        print(f"\n❌ 检查失败: {e}")
        import traceback
        traceback.print_exc()
