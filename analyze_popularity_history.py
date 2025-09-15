#!/usr/bin/env python3
"""
分析topics表popularity_history时序问题
"""
import sys
import os
import json
from datetime import datetime

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.database.connection import db_manager
from src.utils.logger import setup_logger


def analyze_popularity_history():
    """分析popularity_history时序问题"""
    setup_logger()
    
    print("🔍 分析topics表popularity_history时序问题")
    print("=" * 70)
    
    try:
        # 1. 获取所有topics的相关字段
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
        
        print(f"1️⃣ topics表总记录数: {len(topics)}")
        
        if len(topics) == 0:
            print("❌ topics表为空")
            return False
        
        # 2. 分析popularity_history字段情况
        empty_history = []
        has_history = []
        invalid_format = []
        
        print(f"\n2️⃣ 分析popularity_history字段:")
        
        for topic in topics:
            topic_id = topic['topic_id']
            topic_name = topic['topic_name']
            popularity = topic['popularity'] or 0
            popularity_history = topic['popularity_history']
            created_at = topic['created_at']
            update_time = topic['update_time']
            
            print(f"\n   话题: {topic_name[:30]}...")
            print(f"     ID: {topic_id}")
            print(f"     当前热度: {popularity}")
            print(f"     创建时间: {created_at}")
            print(f"     更新时间: {update_time}")
            
            if not popularity_history:
                empty_history.append({
                    'topic_id': topic_id,
                    'topic_name': topic_name,
                    'popularity': popularity,
                    'created_at': created_at
                })
                print(f"     热度历史: ❌ 空")
                
            else:
                try:
                    if isinstance(popularity_history, str):
                        history_data = json.loads(popularity_history)
                    else:
                        history_data = popularity_history
                    
                    if isinstance(history_data, list):
                        has_history.append({
                            'topic_id': topic_id,
                            'topic_name': topic_name,
                            'popularity': popularity,
                            'history_count': len(history_data),
                            'created_at': created_at
                        })
                        print(f"     热度历史: ✅ {len(history_data)} 条记录")
                        
                        # 显示历史记录详情
                        for i, record in enumerate(history_data[:3]):  # 只显示前3条
                            timestamp = record.get('timestamp', 'N/A')
                            value = record.get('popularity', 'N/A')
                            print(f"       {i+1}. {timestamp} - 热度: {value}")
                        
                        if len(history_data) > 3:
                            print(f"       ... 还有 {len(history_data) - 3} 条记录")
                            
                    else:
                        invalid_format.append({
                            'topic_id': topic_id,
                            'topic_name': topic_name,
                            'format': type(history_data).__name__
                        })
                        print(f"     热度历史: ⚠️ 格式错误 ({type(history_data).__name__})")
                        
                except json.JSONDecodeError as e:
                    invalid_format.append({
                        'topic_id': topic_id,
                        'topic_name': topic_name,
                        'format': 'JSON错误'
                    })
                    print(f"     热度历史: ❌ JSON解析失败")
        
        # 3. 统计分析
        print(f"\n3️⃣ 统计分析:")
        print(f"   总话题数: {len(topics)}")
        print(f"   有热度历史: {len(has_history)} 条")
        print(f"   热度历史为空: {len(empty_history)} 条")
        print(f"   格式错误: {len(invalid_format)} 条")
        
        print(f"   热度历史为空比例: {len(empty_history) / len(topics) * 100:.1f}%")
        
        # 4. 分析时序相关性
        print(f"\n4️⃣ 时序分析:")
        
        # 按创建时间排序，看是否有时间规律
        topics_by_time = sorted(topics, key=lambda x: x['created_at'] if x['created_at'] else datetime.min)
        
        print(f"   按时间顺序的热度历史状态:")
        for i, topic in enumerate(topics_by_time[:10]):  # 显示前10个
            has_hist = "有" if topic['popularity_history'] else "无"
            print(f"     {i+1}. {topic['created_at']} - {topic['topic_name'][:25]}... - 热度历史: {has_hist}")
        
        # 5. 查看Topic模型的热度历史添加逻辑
        print(f"\n5️⃣ 可能的问题原因:")
        
        if len(empty_history) > 0:
            print("   发现热度历史为空的情况，可能原因：")
            print("   1. Topic对象创建后未调用add_popularity_history()方法")
            print("   2. 热度计算失败，导致无法添加历史记录")
            print("   3. 数据库保存时popularity_history字段未正确序列化")
            print("   4. 话题分析流程中的时序问题")
        
        # 6. 检查相关推文数量是否影响热度计算
        print(f"\n6️⃣ 热度与推文关联分析:")
        
        for topic in topics[:5]:  # 检查前5个话题
            topic_id = topic['topic_id']
            
            # 查询该话题的推文数量
            tweet_count_sql = "SELECT COUNT(*) as count FROM twitter_tweet WHERE topic_id = %s"
            tweet_result = db_manager.execute_query(tweet_count_sql, (topic_id,))
            tweet_count = tweet_result[0]['count'] if tweet_result else 0
            
            has_hist = "有" if topic['popularity_history'] else "无"
            print(f"   {topic['topic_name'][:25]}...: 推文数={tweet_count}, 热度={topic['popularity']}, 历史={has_hist}")
        
        return {
            'total': len(topics),
            'empty_history': len(empty_history),
            'has_history': len(has_history),
            'invalid_format': len(invalid_format),
            'empty_topics': empty_history,
            'valid_topics': has_history
        }
        
    except Exception as e:
        print(f"❌ 分析失败: {e}")
        import traceback
        traceback.print_exc()
        return None


if __name__ == '__main__':
    result = analyze_popularity_history()
    if result:
        print("=" * 70)
        print("📊 分析总结")
        print("=" * 70)
        print(f"热度历史为空的话题: {result['empty_history']}/{result['total']}")
        
        if result['empty_history'] > 0:
            print("⚠️ 存在时序问题，需要修复")
        else:
            print("✅ 所有话题都有热度历史记录")
    else:
        print("分析失败")
    sys.exit(0)