#!/usr/bin/env python3
"""
一次性测试脚本 - 只爬取1条推文，验证字段映射和入库
"""
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.api.twitter_api_twitterapi import TwitterAPITwitterAPIClient
from src.utils.data_mapper import DataMapper
from src.utils.simple_tweet_enricher import SimpleTweetEnricher
from src.database.tweet_dao import TweetDAO
from src.database.user_dao import UserDAO
from src.utils.logger import get_logger
import json

logger = get_logger(__name__)

def main():
    print("=" * 80)
    print("🧪 测试脚本：爬取1条推文验证字段映射")
    print("=" * 80)
    
    # 1. 初始化客户端
    api_client = TwitterAPITwitterAPIClient()
    data_mapper = DataMapper()
    enricher = SimpleTweetEnricher()
    
    # 使用 cmc300 表（直接修改 table_name）
    tweet_dao = TweetDAO()
    tweet_dao.table_name = 'twitter_tweet_back_test_cmc300'
    user_dao = UserDAO()
    
    print(f"📊 使用数据表: {tweet_dao.table_name}")
    
    # 2. 获取1条推文
    list_id = '1996848536520897010'  # 使用第一个项目列表
    
    logger.info(f"从列表 {list_id} 获取1条推文...")
    print(f"\n正在从列表 {list_id} 获取推文...")
    
    tweets, next_token = api_client.fetch_tweets(
        list_id=list_id,
        max_results=1  # 只要1条
    )
    
    if not tweets or len(tweets) == 0:
        print("❌ 没有获取到推文")
        return
    
    # 只取第一条
    tweets = [tweets[0]]
    print(f"✅ 获取到推文")
    
    # 3. 打印原始API响应
    print("\n" + "=" * 80)
    print("📥 API原始响应")
    print("=" * 80)
    raw_tweet = tweets[0]
    
    # 显示关键字段
    key_fields = [
        ('id_str', raw_tweet.get('id_str')),
        ('full_text', raw_tweet.get('full_text', '')[:50] + '...'),
        ('created_at', raw_tweet.get('created_at')),
        ('is_retweet', raw_tweet.get('is_retweet')),
        ('kol_id', raw_tweet.get('kol_id')),
    ]
    
    for field, value in key_fields:
        print(f"{field:20s}: {value}")
    
    # 显示 author 信息
    if 'author' in raw_tweet and isinstance(raw_tweet['author'], dict):
        author = raw_tweet['author']
        print(f"{'author.id_str':20s}: {author.get('id_str')}")
        print(f"{'author.screen_name':20s}: {author.get('screen_name')}")
    
    # 4. 映射为Tweet对象
    print("\n" + "=" * 80)
    print("🔄 映射为Tweet对象")
    print("=" * 80)
    
    tweet_objs = data_mapper.map_api_data_list_to_tweets([raw_tweet])
    if not tweet_objs:
        print("❌ Tweet对象映射失败")
        return
    
    tweet = tweet_objs[0]
    
    # 提取用户
    users = data_mapper.extract_users_from_tweets([raw_tweet])
    
    print(f"✅ Tweet对象创建成功")
    print(f"   - id_str: {tweet.id_str}")
    print(f"   - full_text: {tweet.full_text[:50]}...")
    print(f"   - is_retweet: {tweet.is_retweet}")
    print(f"   - kol_id: {getattr(tweet, 'kol_id', 'Not set yet')}")
    
    if users:
        user = users[0]
        print(f"\n✅ User对象创建成功")
        print(f"   - id_str: {user.id_str}")
        print(f"   - screen_name: {user.screen_name}")
        print(f"   - name: {user.name}")
    
    # 5. AI增强
    print("\n" + "=" * 80)
    print("🤖 AI增强处理")
    print("=" * 80)
    
    # 构建user_data_map
    user_data_map = {}
    if 'author' in raw_tweet:
        user_data_map[tweet.id_str] = raw_tweet['author']
    
    print("正在进行AI增强（sentiment, isAnnounce, summary等）...")
    enriched_tweets = enricher.enrich_project_tweets_simple(
        tweets=tweet_objs,
        user_data_map=user_data_map
    )
    
    if enriched_tweets:
        enriched_tweet = enriched_tweets[0]
        print(f"\n✅ AI增强完成")
        print(f"   - kol_id (映射为user_id): {enriched_tweet.kol_id}")
        print(f"   - user_name: {enriched_tweet.user_name}")
        print(f"   - sentiment: {enriched_tweet.sentiment}")
        print(f"   - isAnnounce: {enriched_tweet.isAnnounce}")
        print(f"   - is_activity: {enriched_tweet.is_activity}")
        if enriched_tweet.summary:
            print(f"   - summary: {enriched_tweet.summary[:80]}...")
        else:
            print(f"   - summary: None")
    
    # 6. 入库测试（先用户，后推文）
    print("\n" + "=" * 80)
    print("💾 数据库入库测试")
    print("=" * 80)
    
    # 保存用户
    if users:
        print(f"正在保存 {len(users)} 个用户...")
        user_count = user_dao.batch_upsert_users(users)
        print(f"✅ 用户入库: {user_count}/{len(users)}")
    
    # 保存推文
    print(f"正在保存 {len(enriched_tweets)} 条推文...")
    tweet_count = tweet_dao.batch_upsert_tweets(enriched_tweets)
    print(f"✅ 推文入库: {tweet_count}/{len(enriched_tweets)}")
    
    # 7. 验证入库数据
    print("\n" + "=" * 80)
    print("🔍 验证入库数据")
    print("=" * 80)
    
    from src.database.connection import DatabaseManager
    db = DatabaseManager()
    
    # 查询刚才入库的推文
    query = f"""
    SELECT 
        id_str, user_id, user_name, sentiment, isAnnounce, 
        summary, is_activity, is_retweet, 
        full_text, created_at
    FROM twitter_tweet_back_test_cmc300
    WHERE id_str = %s
    """
    
    result = db.execute_query(query, (tweet.id_str,))
    
    if result:
        row = result[0]
        print("✅ 数据库查询成功:")
        print(f"   - id_str: {row[0]}")
        print(f"   - user_id: {row[1]}")
        print(f"   - user_name: {row[2]}")
        print(f"   - sentiment: {row[3]}")
        print(f"   - isAnnounce: {row[4]}")
        if row[5]:
            print(f"   - summary: {row[5][:80]}...")
        else:
            print(f"   - summary: None")
        print(f"   - is_activity: {row[6]}")
        print(f"   - is_retweet: {row[7]}")
        print(f"   - full_text: {row[8][:50]}...")
        print(f"   - created_at: {row[9]}")
        
        # 检查关键字段
        print("\n" + "=" * 80)
        print("✅ 字段完整性检查")
        print("=" * 80)
        
        checks = {
            'user_id': row[1],
            'user_name': row[2],
            'sentiment': row[3],
            'isAnnounce': row[4],
            'is_activity': row[6],
            'is_retweet': row[7]
        }
        
        all_ok = True
        for field, value in checks.items():
            if value is None or (isinstance(value, str) and value == ''):
                print(f"❌ {field:15s}: 空值")
                all_ok = False
            else:
                print(f"✅ {field:15s}: {value}")
        
        # summary 可以为空，单独检查
        if row[5]:
            print(f"✅ {'summary':15s}: {row[5][:30]}...")
        else:
            print(f"⚠️  {'summary':15s}: None (可能不是公告类推文)")
        
        if all_ok:
            print("\n" + "=" * 80)
            print("🎉 所有关键字段验证通过！可以部署了！")
            print("=" * 80)
        else:
            print("\n" + "=" * 80)
            print("⚠️  有字段为空，需要修复")
            print("=" * 80)
    else:
        print("❌ 数据库中未找到该推文")
    
    # 清理
    api_client.close()
    db.close()

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  用户中断")
    except Exception as e:
        logger.error(f"测试失败: {e}", exc_info=True)
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
