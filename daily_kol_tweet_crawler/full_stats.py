"""
全面统计回填脚本的执行情况
"""
import sys
from pathlib import Path
from datetime import datetime, timedelta

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.database.connection import DatabaseManager

db = DatabaseManager()

print("\n" + "=" * 80)
print("📊 回填脚本执行情况全面统计")
print("=" * 80)

# 1. 按日期统计（使用正确的日期格式）
print("\n1️⃣ 按日期统计入库数据:")
print("-" * 80)

dates_check = [
    ('2026-01-01', 'Wed Jan 01%2026'),
    ('2026-01-02', 'Thu Jan 02%2026'),
    ('2026-01-03', 'Fri Jan 03%2026'),
    ('2026-01-04', 'Sat Jan 04%2026'),
]

total_count = 0
for date_label, pattern in dates_check:
    query = 'SELECT COUNT(*) as count FROM twitter_tweet WHERE created_at LIKE %s'
    results = db.execute_query(query, (f'%{pattern}',))
    count = results[0]['count'] if results else 0
    total_count += count
    status = "✅" if count > 0 else "⚠️ "
    print(f"   {status} {date_label}: {count:,} 条")

print(f"\n   📊 过去4天总计: {total_count:,} 条\n")

# 2. 按update_time统计最近入库的数据
print("2️⃣ 按入库时间统计（最近24小时）:")
print("-" * 80)

time_ranges = [
    ('最近1小时', 1),
    ('最近3小时', 3),
    ('最近6小时', 6),
    ('最近12小时', 12),
    ('最近24小时', 24),
]

for label, hours in time_ranges:
    query = f'''
    SELECT COUNT(*) as count
    FROM twitter_tweet
    WHERE update_time >= DATE_SUB(NOW(), INTERVAL {hours} HOUR)
    '''
    results = db.execute_query(query)
    count = results[0]['count'] if results else 0
    print(f"   {label}: {count:,} 条")

# 3. 查看正在处理的推文ID范围
print("\n3️⃣ 最新入库的10条推文信息:")
print("-" * 80)

query = '''
SELECT id_str, created_at, update_time, kol_id, full_text
FROM twitter_tweet
ORDER BY update_time DESC
LIMIT 10
'''
results = db.execute_query(query)

if results:
    for i, row in enumerate(results, 1):
        # 解析created_at
        created_str = row['created_at']
        text = row['full_text'][:40] if row['full_text'] else 'N/A'

        print(f"{i:2d}. ID: {row['id_str']}")
        print(f"     推文时间: {created_str}")
        print(f"     入库时间: {row['update_time']}")

        # 计算入库延迟
        if row['update_time']:
            delay = datetime.now() - row['update_time']
            hours_ago = delay.total_seconds() / 3600
            print(f"     入库延迟: {hours_ago:.1f}小时前")

        print(f"     内容: {text}...")
        print()

# 4. 统计总数
print("4️⃣ 数据库总览:")
print("-" * 80)

query = 'SELECT COUNT(*) as total FROM twitter_tweet'
results = db.execute_query(query)
print(f"   数据库总推文数: {results[0]['total']:,} 条\n")

# 5. 查看2026年数据
query = '''
SELECT
    COUNT(*) as count,
    MIN(created_at) as earliest,
    MAX(created_at) as latest
FROM twitter_tweet
WHERE created_at LIKE '%2026'
'''
results = db.execute_query(query)
if results and results[0]['count'] > 0:
    row = results[0]
    print(f"   2026年数据: {row['count']:,} 条")
    print(f"   时间范围: {row['earliest']} ~ {row['latest']}")
else:
    print(f"   2026年数据: 0 条")

print("\n" + "=" * 80)
print("✅ 统计完成")
print("=" * 80)

# 结论
print("\n📝 结论:")
if total_count > 0:
    print(f"✅ 过去4天已入库 {total_count:,} 条推文")
    print(f"⚠️  回填脚本正在运行，但AI处理速度较慢")
    print(f"💡 建议：让脚本继续运行，等待AI处理完成")
else:
    print(f"⚠️  过去4天(1月1-4日)几乎无数据")
    print(f"💡 建议：检查回填脚本的日期范围设置")
