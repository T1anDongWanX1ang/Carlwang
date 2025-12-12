#!/usr/bin/env python3
"""
检查项目推文表中的数据
"""
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.database.connection import db_manager

def check_project_tweets():
    """检查项目推文数据"""
    try:
        # 查询最新的10条项目推文
        sql = """
        SELECT id_str, created_at, full_text 
        FROM twitter_tweet_project_new 
        ORDER BY created_at DESC 
        LIMIT 10
        """
        
        results = db_manager.execute_query(sql)
        
        print("最新的10条项目推文:")
        print("=" * 80)
        for i, row in enumerate(results, 1):
            print(f"{i}. ID: {row['id_str']}")
            print(f"   时间: {row['created_at']}")
            print(f"   内容: {row['full_text'][:100]}...")
            print()
        
        # 统计不同日期的推文数量
        sql_stats = """
        SELECT 
            DATE(created_at) as tweet_date,
            COUNT(*) as count
        FROM twitter_tweet_project_new 
        WHERE created_at >= '2025-12-09'
        GROUP BY DATE(created_at)
        ORDER BY tweet_date DESC
        """
        
        stats = db_manager.execute_query(sql_stats)
        
        print("最近推文数量统计:")
        print("=" * 30)
        for stat in stats:
            print(f"{stat['tweet_date']}: {stat['count']} 条")
            
    except Exception as e:
        print(f"查询失败: {e}")

if __name__ == '__main__':
    check_project_tweets()