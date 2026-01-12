"""
检查特定推文ID的入库情况
"""
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.database.connection import DatabaseManager

db_manager = DatabaseManager()

# 检查最近正在处理的推文ID
tweet_id = "2007708108089647498"

print(f"\n🔍 检查推文 ID: {tweet_id}\n")

query = """
SELECT id_str, created_at, full_text, update_time, kol_id
FROM twitter_tweet
WHERE id_str = %s
"""
results = db_manager.execute_query(query, (tweet_id,))

if results:
    row = results[0]
    print(f"✅ 找到推文:")
    print(f"   ID: {row['id_str']}")
    print(f"   创建时间: {row['created_at']}")
    print(f"   入库时间: {row['update_time']}")
    print(f"   KOL ID: {row['kol_id']}")
    print(f"   内容: {row['full_text'][:100]}...")
else:
    print(f"⚠️  推文尚未入库或ID不存在")

# 查看最近入库的10条推文
print(f"\n\n📊 最近入库的10条推文（按update_time排序）:\n")

query = """
SELECT id_str, created_at, update_time, kol_id, full_text
FROM twitter_tweet
ORDER BY update_time DESC
LIMIT 10
"""
results = db_manager.execute_query(query)

if results:
    for i, row in enumerate(results, 1):
        text = row['full_text'][:40] if row['full_text'] else 'N/A'
        print(f"{i:2d}. ID: {row['id_str']}")
        print(f"     推文时间: {row['created_at']}")
        print(f"     入库时间: {row['update_time']}")
        print(f"     内容: {text}...")
        print()
