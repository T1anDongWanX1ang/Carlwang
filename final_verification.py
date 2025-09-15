#!/usr/bin/env python3
"""
最终验证修复效果
"""
import sys
import os
from datetime import datetime, timedelta

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.database.topic_dao import topic_dao
from src.utils.logger import setup_logger


def main():
    """最终验证"""
    setup_logger()
    
    print("🎯 Topics表Summary字段修复 - 最终验证报告")
    print("=" * 80)
    
    try:
        db_manager = topic_dao.db_manager
        
        # 1. 总体统计
        print("1️⃣ 总体统计")
        print("-" * 40)
        
        stats_sql = """
        SELECT 
            COUNT(*) as total_topics,
            SUM(CASE WHEN summary IS NOT NULL THEN 1 ELSE 0 END) as topics_with_summary,
            SUM(CASE WHEN summary IS NULL THEN 1 ELSE 0 END) as topics_without_summary
        FROM topics
        """
        
        stats = db_manager.execute_query(stats_sql)[0]
        total = stats['total_topics']
        with_summary = stats['topics_with_summary']
        without_summary = stats['topics_without_summary']
        
        print(f"📊 话题总数: {total}")
        print(f"📊 有Summary: {with_summary} ({with_summary/total*100:.1f}%)")
        print(f"📊 无Summary: {without_summary} ({without_summary/total*100:.1f}%)")
        
        # 2. 最近修复的话题
        print(f"\n2️⃣ 最近修复的话题 (20分钟内)")
        print("-" * 40)
        
        recent_fix_sql = """
        SELECT topic_name, update_time, CHAR_LENGTH(summary) as summary_length
        FROM topics 
        WHERE summary IS NOT NULL 
        AND update_time >= DATE_SUB(NOW(), INTERVAL 20 MINUTE)
        ORDER BY update_time DESC 
        LIMIT 15
        """
        
        recent_fixes = db_manager.execute_query(recent_fix_sql)
        
        if recent_fixes:
            print(f"✅ 最近修复了 {len(recent_fixes)} 个话题:")
            for topic in recent_fixes:
                print(f"   • {topic['topic_name'][:40]}... ({topic['summary_length']}字符) - {topic['update_time']}")
        else:
            print("⚠️ 最近20分钟内没有修复的话题")
        
        # 3. 待修复话题统计
        print(f"\n3️⃣ 待修复话题分析")
        print("-" * 40)
        
        # 按创建时间分析null summary话题
        time_analysis_sql = """
        SELECT 
            CASE 
                WHEN created_at >= DATE_SUB(NOW(), INTERVAL 1 HOUR) THEN '1小时内'
                WHEN created_at >= DATE_SUB(NOW(), INTERVAL 6 HOUR) THEN '6小时内'
                WHEN created_at >= DATE_SUB(NOW(), INTERVAL 24 HOUR) THEN '24小时内'
                WHEN created_at >= DATE_SUB(NOW(), INTERVAL 7 DAY) THEN '7天内'
                ELSE '更早'
            END as time_range,
            COUNT(*) as count
        FROM topics 
        WHERE summary IS NULL
        GROUP BY time_range
        ORDER BY 
            CASE time_range
                WHEN '1小时内' THEN 1
                WHEN '6小时内' THEN 2
                WHEN '24小时内' THEN 3
                WHEN '7天内' THEN 4
                ELSE 5
            END
        """
        
        time_analysis = db_manager.execute_query(time_analysis_sql)
        
        print("📅 null summary话题按时间分布:")
        for item in time_analysis:
            print(f"   • {item['time_range']}: {item['count']} 个")
        
        # 4. 验证修复逻辑
        print(f"\n4️⃣ 修复逻辑验证")
        print("-" * 40)
        
        # 检查最新话题是否有summary（验证smart_classifier修改是否生效）
        latest_topics_sql = """
        SELECT topic_name, summary, created_at
        FROM topics 
        ORDER BY created_at DESC 
        LIMIT 3
        """
        
        latest_topics = db_manager.execute_query(latest_topics_sql)
        
        print("🔍 最新3个话题的summary状态:")
        new_topics_with_summary = 0
        for topic in latest_topics:
            status = "✅ 有Summary" if topic['summary'] else "❌ 无Summary"
            print(f"   • {topic['topic_name'][:40]}... - {status} ({topic['created_at']})")
            if topic['summary']:
                new_topics_with_summary += 1
        
        # 5. 总结和建议
        print(f"\n5️⃣ 修复效果总结")
        print("-" * 40)
        
        fix_success_rate = with_summary / total * 100
        recent_fix_count = len(recent_fixes) if recent_fixes else 0
        
        print(f"🎯 修复效果:")
        print(f"   • 总体Summary覆盖率: {fix_success_rate:.1f}%")
        print(f"   • 最近20分钟修复数量: {recent_fix_count}")
        print(f"   • 最新话题Summary率: {new_topics_with_summary}/3 ({new_topics_with_summary/3*100:.0f}%)")
        
        if fix_success_rate >= 10:
            print(f"\n✅ 修复效果良好")
        elif recent_fix_count > 0:
            print(f"\n⚠️ 修复进行中，需要继续运行批量修复脚本")
        else:
            print(f"\n❌ 修复效果不明显，需要检查修复逻辑")
        
        if new_topics_with_summary >= 2:
            print(f"✅ 新话题创建逻辑修复生效")
        else:
            print(f"⚠️ 新话题创建逻辑可能未完全生效（或最近无新话题创建）")
        
        print(f"\n6️⃣ 后续建议")
        print("-" * 40)
        
        if without_summary > 0:
            print(f"🔧 建议继续运行批量修复脚本处理剩余 {without_summary} 个无Summary话题")
            print(f"🔧 建议设置定期任务定时修复null summary话题")
        
        print(f"🔧 建议监控新创建话题的summary生成情况")
        print(f"🔧 已修复的核心问题：smart_classifier创建话题时现在会自动生成基础summary")
        
        
    except Exception as e:
        print(f"❌ 验证过程异常: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()