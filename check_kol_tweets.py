#!/usr/bin/env python3
"""
检查KOL推文数据
"""
import sys
import os
from datetime import datetime, timedelta

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.database.tweet_dao import tweet_dao
from src.utils.logger import setup_logger


def check_kol_tweets():
    """检查KOL推文数据"""
    setup_logger()
    
    print("🔍 检查KOL推文数据")
    print("=" * 60)
    
    try:
        # 使用tweet_dao查询KOL推文
        db_manager = tweet_dao.db_manager
        
        # 查询有kol_id的推文
        sql = """
        SELECT id_str, full_text, created_at, kol_id 
        FROM twitter_tweet 
        WHERE kol_id IS NOT NULL AND kol_id != '' 
        ORDER BY created_at DESC 
        LIMIT 10
        """
        
        kol_tweets = db_manager.execute_query(sql)
        
        print(f"📊 数据库中的KOL推文数量: {len(kol_tweets) if kol_tweets else 0}")
        
        if kol_tweets:
            print("\n📋 KOL推文样本:")
            for i, tweet in enumerate(kol_tweets[:5], 1):
                print(f"   {i}. [{tweet['created_at']}] KOL:{tweet['kol_id']}")
                print(f"      {tweet['full_text'][:100]}...")
                print()
        else:
            print("❌ 数据库中没有找到KOL推文")
            
        # 查询总推文数
        total_sql = "SELECT COUNT(*) as count FROM twitter_tweet"
        total_result = db_manager.execute_query(total_sql)
        total_count = total_result[0]['count'] if total_result else 0
        
        print(f"📈 推文统计:")
        print(f"   总推文数: {total_count}")
        print(f"   KOL推文数: {len(kol_tweets) if kol_tweets else 0}")
        print(f"   KOL比例: {len(kol_tweets)/total_count*100:.2f}%" if total_count > 0 else "0%")
        
        return len(kol_tweets) if kol_tweets else 0
        
    except Exception as e:
        print(f"❌ 检查KOL推文数据异常: {e}")
        import traceback
        traceback.print_exc()
        return 0


if __name__ == '__main__':
    check_kol_tweets()
