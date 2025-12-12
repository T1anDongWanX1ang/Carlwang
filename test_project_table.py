#!/usr/bin/env python3
"""测试项目推文表插入"""

import sys
import os
sys.path.append(os.path.dirname(__file__))

from src.database.tweet_dao import TweetDAO
from src.models.tweet import Tweet
from datetime import datetime

def test_project_table_insert():
    """测试项目推文表插入"""
    try:
        # 创建测试推文
        test_tweet = Tweet(
            id_str="test_project_tweet_123",
            full_text="这是一个测试项目推文",
            created_at="Wed Dec 10 17:00:00 +0000 2025",
            kol_id="test_kol_123",
            sentiment="Neutral",
            is_announce=0,
            is_activity=0,
            is_retweet=0
        )
        
        # 测试项目推文表插入
        tweet_dao = TweetDAO()
        project_table = 'twitter_tweet_project_new'
        
        print(f"测试插入到项目推文表: {project_table}")
        result = tweet_dao.batch_upsert_tweets([test_tweet], table_name=project_table)
        
        if result > 0:
            print(f"✅ 成功插入 {result} 条推文到项目表")
        else:
            print("❌ 插入失败")
            
        # 清理测试数据
        try:
            from src.database.connection import db_manager
            db_manager.execute_update(
                f"DELETE FROM {project_table} WHERE id_str = %s", 
                ("test_project_tweet_123",)
            )
            print("🧹 测试数据已清理")
        except Exception as e:
            print(f"⚠️ 清理测试数据失败: {e}")
            
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_project_table_insert()
