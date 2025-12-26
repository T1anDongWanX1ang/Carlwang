#!/usr/bin/env python3
"""
检查最近的推文数据
"""
import sys
import os
from datetime import datetime, timedelta

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.database.tweet_dao import tweet_dao
from src.utils.logger import setup_logger


def check_recent_tweets():
    """检查最近推文数据"""
    setup_logger()
    
    print("🔍 检查最近推文数据")
    print("=" * 60)
    
    try:
        # 检查不同时间范围的推文数量
        now = datetime.now()
        time_ranges = [
            ("1小时", 1),
            ("6小时", 6), 
            ("24小时", 24),
            ("3天", 72),
            ("7天", 168)
        ]
        
        for label, hours in time_ranges:
            start_time = now - timedelta(hours=hours)
            tweets = tweet_dao.get_tweets_by_date_range(
                start_date=start_time,
                end_date=now,
                limit=1000
            )
            print(f"📊 最近{label}: {len(tweets)} 条推文")
        
        # 查看最新的几条推文
        print("\n📋 最新推文样本:")
        latest_tweets = tweet_dao.get_tweets_by_date_range(
            start_date=now - timedelta(days=7),
            end_date=now,
            limit=10
        )
        
        if latest_tweets:
            for i, tweet in enumerate(latest_tweets[:5], 1):
                created_at = getattr(tweet, 'created_at', 'Unknown')
                kol_info = f"KOL:{tweet.kol_id}" if hasattr(tweet, 'kol_id') and tweet.kol_id else "非KOL"
                print(f"   {i}. [{created_at}] [{kol_info}] {tweet.full_text[:80]}...")
        else:
            print("   ❌ 没有找到任何推文")
            
        # 检查KOL推文
        print(f"\n🎯 KOL推文统计:")
        kol_tweets = [t for t in latest_tweets if hasattr(t, 'kol_id') and t.kol_id]
        print(f"   总推文数: {len(latest_tweets)}")
        print(f"   KOL推文数: {len(kol_tweets)}")
        print(f"   KOL比例: {len(kol_tweets)/len(latest_tweets)*100:.1f}%" if latest_tweets else "0%")
        
    except Exception as e:
        print(f"❌ 检查推文数据异常: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    check_recent_tweets()
