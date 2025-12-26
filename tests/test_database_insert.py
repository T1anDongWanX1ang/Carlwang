#!/usr/bin/env python3
"""
测试数据库JSON存储
"""
import sys
import os
from datetime import datetime

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.database.topic_dao import topic_dao
from src.models.topic import Topic
from src.utils.logger import setup_logger


def test_json_storage():
    """测试JSON格式summary的数据库存储"""
    setup_logger()
    
    print("🔍 测试JSON格式summary的数据库存储")
    print("=" * 60)
    
    try:
        # 创建测试JSON数据
        json_summary = '''{"topic_id": "test_topic", "summary": [{"viewpoint": "测试观点", "related_tweets": ["test_tweet_1"]}]}'''
        
        # 创建测试Topic对象
        test_topic = Topic(
            topic_name="测试JSON存储",
            brief="测试JSON格式的summary存储是否正常",
            created_at=datetime.now(),
            popularity=10,
            summary=json_summary  # JSON格式的summary
        )
        
        print(f"📊 测试数据:")
        print(f"   Topic名称: {test_topic.topic_name}")
        print(f"   Summary长度: {len(json_summary)}")
        print(f"   Summary内容: {json_summary[:100]}...")
        
        # 尝试插入数据库
        print(f"\n🧪 尝试插入数据库...")
        result = topic_dao.insert_topic(test_topic)
        
        if result:
            print(f"   ✅ 插入成功！")
            
            # 立即查询验证
            print(f"\n🔍 验证存储结果...")
            retrieved_topic = topic_dao.get_topic_by_name("测试JSON存储")
            
            if retrieved_topic and retrieved_topic.summary:
                print(f"   ✅ 查询成功，summary存在")
                print(f"   存储的summary: {retrieved_topic.summary[:100]}...")
                
                # 尝试解析JSON
                import json
                try:
                    parsed = json.loads(retrieved_topic.summary)
                    print(f"   ✅ JSON解析成功")
                    print(f"   观点数量: {len(parsed.get('summary', []))}")
                except json.JSONDecodeError as e:
                    print(f"   ❌ JSON解析失败: {e}")
                    
            elif retrieved_topic:
                print(f"   ❌ 查询到话题但summary为空")
                print(f"   Summary值: {retrieved_topic.summary}")
            else:
                print(f"   ❌ 查询不到话题")
                
            # 清理测试数据
            print(f"\n🧹 清理测试数据...")
            cleanup_sql = "DELETE FROM topics WHERE topic_name = '测试JSON存储'"
            topic_dao.db_manager.execute_update(cleanup_sql)
            print(f"   ✅ 测试数据已清理")
            
        else:
            print(f"   ❌ 插入失败")
            
        return result
        
    except Exception as e:
        print(f"❌ 测试异常: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_current_storage_logic():
    """测试当前的存储逻辑"""
    print("\n🔧 测试当前存储逻辑")
    print("=" * 60)
    
    try:
        # 查看最近插入的topics的summary情况
        db_manager = topic_dao.db_manager
        
        sql = """
        SELECT topic_name, summary, created_at
        FROM topics 
        WHERE created_at >= DATE_SUB(NOW(), INTERVAL 2 HOUR)
        ORDER BY created_at DESC 
        LIMIT 5
        """
        
        recent_topics = db_manager.execute_query(sql)
        
        if recent_topics:
            print(f"📊 最近2小时内的topics:")
            for topic in recent_topics:
                summary_status = "有内容" if topic['summary'] else "NULL"
                summary_length = len(topic['summary']) if topic['summary'] else 0
                print(f"   - {topic['topic_name']}: {summary_status} ({summary_length}字符)")
                
                if topic['summary']:
                    # 检查是否是JSON
                    try:
                        import json
                        json.loads(topic['summary'])
                        print(f"     ✅ JSON格式正确")
                    except:
                        print(f"     ⚠️ 非JSON格式")
        else:
            print("📊 最近2小时内没有新的topics")
            
    except Exception as e:
        print(f"❌ 检查当前存储逻辑异常: {e}")


if __name__ == '__main__':
    success = test_json_storage()
    test_current_storage_logic()
    print(f"\n🎯 JSON存储测试结果: {'✅ 正常' if success else '❌ 异常'}")
