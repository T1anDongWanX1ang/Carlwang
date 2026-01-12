import pymysql
import requests
import json
import sys
from datetime import datetime, timedelta

# --- 配置部分 ---
DB_CONFIG = {
    'host': '35.215.99.34', 
    'port': 13216, 
    'user': 'tele', 
    'password': 'tele_sb268fg@cg5wH9dgW',
    'database': 'public_data',
    'charset': 'utf8mb4'
}

# 从 config.json 中提取的 API Key
API_KEY = "new1_038536908c7f4960812ee7d601f620a1"
API_URL = "https://api.twitterapi.io/twitter/tweets"
TABLE_NAME = "twitter_tweet_back_test_cmc300"

def get_db_connection():
    return pymysql.connect(**DB_CONFIG)

def fetch_sample_tweets(conn):
    """从数据库获取 20 条样本"""
    cursor = conn.cursor(pymysql.cursors.DictCursor)
    # 选取过去 7 天的 20 条，按 favorite_count 倒序，这样更容易观察到数据变化（热门推文变化快）
    sql = f"""
        SELECT id_str, favorite_count, retweet_count, reply_count, quote_count, view_count, created_at_datetime
        FROM {TABLE_NAME} 
        WHERE created_at_datetime >= NOW() - INTERVAL 7 DAY
        ORDER BY favorite_count DESC
        LIMIT 20
    """
    cursor.execute(sql)
    return cursor.fetchall()

def fetch_latest_metrics(tweet_ids):
    """调用 API 获取最新数据"""
    headers = {
        "X-API-Key": API_KEY,
        "Accept": "application/json"
    }
    # 参数名 tweet_ids
    params = {"tweet_ids": ",".join(tweet_ids)}
    
    print(f"正在请求 API: {API_URL} (IDs count: {len(tweet_ids)})")
    try:
        response = requests.get(API_URL, headers=headers, params=params, timeout=30)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"API 请求失败: {e}")
        if 'response' in locals():
            print(f"Response: {response.text}")
        return None

def update_db(conn, updates):
    """更新数据库"""
    cursor = conn.cursor()
    updated_count = 0
    
    # 准备 SQL 语句
    sql = f"""
        UPDATE {TABLE_NAME}
        SET favorite_count=%s, retweet_count=%s, reply_count=%s, quote_count=%s, view_count=%s
        WHERE id_str=%s
    """
    
    for item in updates:
        try:
            cursor.execute(sql, (
                item['favorite_count'], item['retweet_count'], item['reply_count'], 
                item['quote_count'], item['view_count'], item['id_str']
            ))
            updated_count += 1
        except Exception as e:
            print(f"更新失败 ID {item['id_str']}: {e}")
            
    conn.commit()
    return updated_count

def main():
    try:
        conn = get_db_connection()
        print("✅ 数据库连接成功")
        
        # 1. 获取样本
        old_tweets = fetch_sample_tweets(conn)
        if not old_tweets:
            print("❌ 未找到符合条件的推文")
            return
            
        print(f"📦 获取到 {len(old_tweets)} 条样本推文 (过去 7 天)")
        tweet_ids = [t['id_str'] for t in old_tweets]
        old_map = {t['id_str']: t for t in old_tweets}
        
        # 2. 调用 API
        print(f"🚀 正在获取最新互动数据...")
        api_data = fetch_latest_metrics(tweet_ids)
        
        if not api_data or 'tweets' not in api_data:
            print("❌ API 返回数据异常")
            # 尝试打印调试信息
            if api_data:
                print(json.dumps(api_data, indent=2))
            return
            
        new_tweets = api_data['tweets']
        print(f"📡 API 返回 {len(new_tweets)} 条数据")
        
        # 3. 对比变化
        updates = []
        print("\n" + "="*90)
        print(f"{ 'ID':<19} | { '字段':<10} | { '旧值':<8} | { '新值':<8} | {'变化量'}")
        print("="*90)
        
        changed_tweets_count = 0
        
        for new_t in new_tweets:
            tid = new_t.get('id')
            if tid not in old_map:
                continue
                
            old_t = old_map[tid]
            
            # 提取新指标 (注意 API 字段名)
            new_metrics = {
                'favorite_count': new_t.get('likeCount', 0),
                'retweet_count': new_t.get('retweetCount', 0),
                'reply_count': new_t.get('replyCount', 0),
                'quote_count': new_t.get('quoteCount', 0),
                'view_count': new_t.get('viewCount', 0)
            }
            
            # 对比
            has_change = False
            
            # 我们只把有变化的字段打印出来
            row_changes = []
            for field, new_val in new_metrics.items():
                old_val = old_t.get(field, 0)
                if old_val is None: old_val = 0
                new_val = int(new_val)
                old_val = int(old_val)
                
                if new_val != old_val:
                    diff = new_val - old_val
                    diff_str = f"+{diff}" if diff > 0 else f"{diff}"
                    print(f"{tid:<19} | {field:<10} | {old_val:<8} | {new_val:<8} | {diff_str}")
                    has_change = True
            
            if has_change:
                changed_tweets_count += 1
                # 准备更新数据
                update_item = new_metrics.copy()
                update_item['id_str'] = tid
                updates.append(update_item)
        
        print("="*90)
        print(f"📊 统计: 共检测到 {changed_tweets_count} 条推文有数据变化")
        
        # 4. 执行更新
        if updates:
            print(f"💾 正在将 {len(updates)} 条更新写入数据库...")
            count = update_db(conn, updates)
            print(f"✅ 成功更新 {count} 条记录")
        else:
            print("😴 数据无变化，无需更新")
            
        conn.close()
        
    except Exception as e:
        print(f"❌ 发生严重错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
