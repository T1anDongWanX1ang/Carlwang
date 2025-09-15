#!/usr/bin/env python3
"""
检查修复结果
"""
import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.database.topic_dao import topic_dao
from src.utils.logger import setup_logger


def check_fix_results():
    """检查修复结果"""
    setup_logger()
    
    print("🔍 检查summary修复结果")
    print("=" * 60)
    
    try:
        db_manager = topic_dao.db_manager
        
        # 统计summary情况
        stats_sql = """
        SELECT 
            COUNT(*) as total_topics,
            SUM(CASE WHEN summary IS NOT NULL THEN 1 ELSE 0 END) as topics_with_summary,
            SUM(CASE WHEN summary IS NULL THEN 1 ELSE 0 END) as topics_without_summary
        FROM topics
        """
        
        stats = db_manager.execute_query(stats_sql)
        
        if stats:
            stat = stats[0]
            total = stat['total_topics']
            with_summary = stat['topics_with_summary']
            without_summary = stat['topics_without_summary']
            
            print(f"📊 总体统计:")
            print(f"   总话题数: {total}")
            print(f"   有summary: {with_summary} ({with_summary/total*100:.1f}%)")
            print(f"   无summary: {without_summary} ({without_summary/total*100:.1f}%)")
        
        # 查看最近生成的summary
        recent_sql = """
        SELECT topic_name, summary, update_time
        FROM topics 
        WHERE summary IS NOT NULL 
        AND update_time >= DATE_SUB(NOW(), INTERVAL 10 MINUTE)
        ORDER BY update_time DESC 
        LIMIT 10
        """
        
        recent_topics = db_manager.execute_query(recent_sql)
        
        if recent_topics:
            print(f"\n📋 最近10分钟内更新的话题 ({len(recent_topics)}个):")
            for topic in recent_topics:
                summary_preview = topic['summary'][:100] + "..." if len(topic['summary']) > 100 else topic['summary']
                print(f"   - {topic['topic_name']}: 更新于 {topic['update_time']}")
                print(f"     Summary: {summary_preview}")
                print()
        else:
            print(f"\n📋 最近10分钟内没有更新的话题")
            
        # 检查最新的空summary话题
        null_sql = """
        SELECT topic_name, created_at
        FROM topics 
        WHERE summary IS NULL 
        ORDER BY created_at DESC 
        LIMIT 5
        """
        
        null_topics = db_manager.execute_query(null_sql)
        
        if null_topics:
            print(f"\n⚠️ 仍有空summary的话题 (最新5个):")
            for topic in null_topics:
                print(f"   - {topic['topic_name']}: 创建于 {topic['created_at']}")
        else:
            print(f"\n✅ 所有话题都已有summary")
            
    except Exception as e:
        print(f"❌ 检查修复结果失败: {e}")


if __name__ == '__main__':
    check_fix_results()
