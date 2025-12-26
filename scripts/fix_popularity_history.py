#!/usr/bin/env python3
"""
修复topics表popularity_history时序问题
"""
import sys
import os
import json
from datetime import datetime

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.database.connection import db_manager
from src.utils.logger import setup_logger


def fix_popularity_history():
    """修复popularity_history时序问题"""
    setup_logger()
    
    print("🔧 修复topics表popularity_history时序问题")
    print("=" * 60)
    
    try:
        # 1. 获取所有topics记录
        topics_sql = """
        SELECT 
            topic_id, 
            topic_name, 
            popularity,
            popularity_history,
            created_at,
            update_time
        FROM topics
        ORDER BY created_at DESC
        """
        
        topics = db_manager.execute_query(topics_sql)
        
        print(f"1️⃣ 找到 {len(topics)} 条topic记录")
        
        if len(topics) == 0:
            print("❌ topics表为空")
            return False
        
        fixed_count = 0
        
        # 2. 处理每条记录
        for topic in topics:
            topic_id = topic['topic_id']
            topic_name = topic['topic_name']
            popularity = topic['popularity'] or 0
            popularity_history = topic['popularity_history']
            created_at = topic['created_at']
            update_time = topic['update_time']
            
            print(f"\n处理话题: {topic_name[:30]}...")
            print(f"   当前热度: {popularity}")
            print(f"   创建时间: {created_at}")
            print(f"   更新时间: {update_time}")
            
            needs_fix = False
            
            # 解析现有的热度历史
            try:
                if isinstance(popularity_history, str):
                    history_data = json.loads(popularity_history)
                else:
                    history_data = popularity_history or []
                
                print(f"   当前历史记录数: {len(history_data)}")
                
                # 如果热度历史为空或记录数不足，需要修复
                if len(history_data) == 0:
                    # 添加创建时的热度记录
                    initial_record = {
                        "popularity": popularity,
                        "timestamp": created_at.isoformat() if isinstance(created_at, datetime) else str(created_at)
                    }
                    history_data.append(initial_record)
                    needs_fix = True
                    print(f"   ✅ 添加初始热度记录: {popularity} @ {created_at}")
                
                # 如果更新时间和创建时间不同，且只有一条记录，添加更新记录
                if (update_time and created_at and update_time != created_at 
                    and len(history_data) == 1):
                    
                    update_record = {
                        "popularity": popularity,
                        "timestamp": update_time.isoformat() if isinstance(update_time, datetime) else str(update_time)
                    }
                    history_data.append(update_record)
                    needs_fix = True
                    print(f"   ✅ 添加更新热度记录: {popularity} @ {update_time}")
                
                # 如果需要修复，更新数据库
                if needs_fix:
                    fixed_history_json = json.dumps(history_data, ensure_ascii=False)
                    
                    update_sql = "UPDATE topics SET popularity_history = %s WHERE topic_id = %s"
                    affected = db_manager.execute_update(update_sql, (fixed_history_json, topic_id))
                    
                    if affected > 0:
                        fixed_count += 1
                        print(f"   ✅ 修复成功，现有 {len(history_data)} 条历史记录")
                    else:
                        print(f"   ❌ 更新失败")
                else:
                    print(f"   ✅ 无需修复")
                
            except json.JSONDecodeError as e:
                print(f"   ❌ JSON解析失败: {e}")
                
                # 重新创建热度历史
                new_history = [{
                    "popularity": popularity,
                    "timestamp": created_at.isoformat() if isinstance(created_at, datetime) else str(created_at)
                }]
                
                fixed_history_json = json.dumps(new_history, ensure_ascii=False)
                
                update_sql = "UPDATE topics SET popularity_history = %s WHERE topic_id = %s"
                affected = db_manager.execute_update(update_sql, (fixed_history_json, topic_id))
                
                if affected > 0:
                    fixed_count += 1
                    print(f"   ✅ 重新创建热度历史")
                else:
                    print(f"   ❌ 重新创建失败")
            
            except Exception as e:
                print(f"   ❌ 处理异常: {e}")
                continue
        
        # 3. 验证修复结果
        print(f"\n3️⃣ 修复结果:")
        print(f"   成功修复: {fixed_count}/{len(topics)} 条记录")
        
        # 重新检查热度历史状态
        verification_sql = """
        SELECT 
            topic_id, 
            topic_name,
            popularity,
            popularity_history
        FROM topics
        LIMIT 5
        """
        
        sample_topics = db_manager.execute_query(verification_sql)
        
        print(f"\n4️⃣ 修复后示例:")
        for i, topic in enumerate(sample_topics, 1):
            history_data = json.loads(topic['popularity_history']) if isinstance(topic['popularity_history'], str) else (topic['popularity_history'] or [])
            print(f"   {i}. {topic['topic_name'][:25]}...: 热度={topic['popularity']}, 历史记录={len(history_data)}条")
        
        return fixed_count > 0
        
    except Exception as e:
        print(f"❌ 修复失败: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == '__main__':
    success = fix_popularity_history()
    print(f"\n{'🎉 修复完成' if success else '❌ 修复失败'}")
    sys.exit(0 if success else 1)