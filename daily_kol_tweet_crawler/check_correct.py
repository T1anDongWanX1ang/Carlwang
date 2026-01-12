"""
正确的回填数据检查 - 修复时区问题
"""
import sys
from pathlib import Path
from datetime import datetime, timedelta

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.database.connection import DatabaseManager

db_manager = DatabaseManager()

print("\n" + "=" * 80)
print("📊 过去4天回填数据检查（修复版）")
print("=" * 80)

# 查询最近4天的数据（使用LIKE避免时区问题）
dates = ['2026-01-01', '2026-01-02', '2026-01-03', '2026-01-04']

print("\n按日期统计（使用LIKE匹配）:\n")
total = 0
for date_str in dates:
    query = """
    SELECT COUNT(*) as count
    FROM twitter_tweet
    WHERE created_at LIKE %s
    """
    results = db_manager.execute_query(query, (f'{date_str}%',))
    count = results[0]['count'] if results else 0
    total += count
    print(f"📅 {date_str}: {count:,} 条")

print(f"\n✅ **过去4天总计: {total:,} 条推文**\n")

# 详细查看每天的时间范围
print("=" * 80)
print("详细时间范围:\n")
for date_str in dates:
    query = """
    SELECT
        COUNT(*) as count,
        MIN(created_at) as earliest,
        MAX(created_at) as latest,
        MIN(update_time) as first_insert,
        MAX(update_time) as last_insert
    FROM twitter_tweet
    WHERE created_at LIKE %s
    """
    results = db_manager.execute_query(query, (f'{date_str}%',))
    if results and results[0]['count'] > 0:
        row = results[0]
        print(f"📅 {date_str}:")
        print(f"   数量: {row['count']:,} 条")
        print(f"   推文时间: {row['earliest']} ~ {row['latest']}")
        print(f"   入库时间: {row['first_insert']} ~ {row['last_insert']}")
        print()

print("=" * 80)
print("✅ 检查完成")
print("=" * 80)
print("\n📝 结论:")
if total > 0:
    print(f"✅ 回填脚本正常运行，过去4天共入库 {total:,} 条推文")
else:
    print("❌ 回填脚本未运行或数据未入库")
