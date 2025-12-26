#!/usr/bin/env python3
"""
测试propagation_speed修正效果
"""
import sys
from pathlib import Path
from datetime import datetime, timedelta

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.database.topic_dao import topic_dao

def test_speed_fix():
    """测试修正效果"""
    print("=== 测试Propagation Speed修正效果 ===")
    
    # 获取最近创建但没有速度的话题
    sql = """
    SELECT topic_id, topic_name, created_at, propagation_speed_5m, propagation_speed_1h, propagation_speed_4h
    FROM topics 
    WHERE topic_name IS NOT NULL
    AND created_at >= DATE_SUB(NOW(), INTERVAL 2 HOUR)
    AND (propagation_speed_5m IS NULL OR propagation_speed_5m = 0)
    ORDER BY created_at DESC
    LIMIT 3
    """
    
    topics_without_speed = topic_dao.db_manager.execute_query(sql)
    
    if topics_without_speed:
        print(f"找到 {len(topics_without_speed)} 个最近创建但没有传播速度的话题:")
        for topic in topics_without_speed:
            print(f"  - {topic['topic_name']} (创建于: {topic['created_at']})")
        
        # 手动运行一次话题分析
        print("\n正在执行话题分析（包含传播速度计算）...")
        try:
            from src.topic_engine import topic_engine
            success = topic_engine.analyze_recent_tweets(hours=4, max_tweets=50)
            
            if success:
                print("✅ 话题分析完成")
                
                # 重新检查这些话题的传播速度
                print("\n检查修正效果:")
                for topic in topics_without_speed:
                    updated_sql = """
                    SELECT propagation_speed_5m, propagation_speed_1h, propagation_speed_4h, update_time
                    FROM topics 
                    WHERE topic_id = %s
                    """
                    result = topic_dao.db_manager.execute_query(updated_sql, [topic['topic_id']])
                    
                    if result:
                        updated = result[0]
                        print(f"  话题: {topic['topic_name'][:40]}...")
                        print(f"    5m: {updated['propagation_speed_5m']}")
                        print(f"    1h: {updated['propagation_speed_1h']}")
                        print(f"    4h: {updated['propagation_speed_4h']}")
                        print(f"    更新时间: {updated['update_time']}")
                        
                        if (updated['propagation_speed_5m'] or 0) > 0 or (updated['propagation_speed_1h'] or 0) > 0:
                            print("    ✅ 传播速度已更新")
                        else:
                            print("    ❌ 传播速度仍为0")
                        print()
            else:
                print("❌ 话题分析失败")
                
        except Exception as e:
            print(f"❌ 执行话题分析时出错: {e}")
            
    else:
        print("✅ 最近2小时内创建的话题都已有传播速度")
        
        # 显示最近的有速度的话题
        recent_with_speed_sql = """
        SELECT topic_name, propagation_speed_5m, propagation_speed_1h, propagation_speed_4h, update_time
        FROM topics 
        WHERE propagation_speed_5m > 0 OR propagation_speed_1h > 0 OR propagation_speed_4h > 0
        ORDER BY update_time DESC
        LIMIT 5
        """
        
        recent_with_speed = topic_dao.db_manager.execute_query(recent_with_speed_sql)
        if recent_with_speed:
            print("\n最近有传播速度的话题:")
            for topic in recent_with_speed:
                print(f"  {topic['topic_name'][:40]}... -> 5m:{topic['propagation_speed_5m']}, 1h:{topic['propagation_speed_1h']}, 4h:{topic['propagation_speed_4h']}")

if __name__ == '__main__':
    test_speed_fix()