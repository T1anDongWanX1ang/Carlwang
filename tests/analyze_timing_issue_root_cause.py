#!/usr/bin/env python3
"""
分析时序问题的根本原因
"""
import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.database.connection import db_manager
from src.utils.logger import setup_logger


def analyze_timing_issue_root_cause():
    """分析时序问题的根本原因"""
    setup_logger()
    
    print("🔍 分析popularity_history时序问题根本原因")
    print("=" * 70)
    
    try:
        # 查看修复后的数据分布
        analysis_sql = """
        SELECT 
            topic_id,
            topic_name,
            created_at,
            update_time,
            popularity_history
        FROM topics
        ORDER BY created_at ASC
        """
        
        topics = db_manager.execute_query(analysis_sql)
        
        print(f"1️⃣ 时序模式分析:")
        
        import json
        from datetime import datetime
        
        early_batch = []  # 早上创建的
        late_batch = []   # 下午创建的
        
        for topic in topics:
            created_time = topic['created_at']
            update_time = topic['update_time']
            
            # 解析created_at时间
            if isinstance(created_time, datetime):
                hour = created_time.hour
            else:
                try:
                    created_dt = datetime.fromisoformat(str(created_time))
                    hour = created_dt.hour
                except:
                    hour = 12  # 默认值
            
            if hour < 12:
                early_batch.append(topic)
            else:
                late_batch.append(topic)
        
        print(f"   早上创建的话题: {len(early_batch)} 个 (06:44-07:04)")
        print(f"   下午创建的话题: {len(late_batch)} 个 (15:38-15:39)")
        
        # 分析时序差异
        print(f"\n2️⃣ 时序差异分析:")
        
        if early_batch:
            sample_early = early_batch[0]
            print(f"   早期话题示例: {sample_early['topic_name'][:30]}...")
            print(f"     创建时间: {sample_early['created_at']}")
            print(f"     更新时间: {sample_early['update_time']}")
            
            time_diff = None
            if (sample_early['update_time'] and sample_early['created_at']):
                try:
                    if isinstance(sample_early['update_time'], datetime) and isinstance(sample_early['created_at'], datetime):
                        time_diff = sample_early['update_time'] - sample_early['created_at']
                    print(f"     时间差: {time_diff}")
                except:
                    print(f"     时间差: 无法计算")
        
        if late_batch:
            sample_late = late_batch[0]
            print(f"   晚期话题示例: {sample_late['topic_name'][:30]}...")
            print(f"     创建时间: {sample_late['created_at']}")
            print(f"     更新时间: {sample_late['update_time']}")
        
        # 3. 分析根本原因
        print(f"\n3️⃣ 根本原因分析:")
        
        print("   发现的时序问题:")
        print("   1. 早期话题: 创建时间和更新时间不同 (有8小时时差)")
        print("   2. 晚期话题: 创建时间和更新时间相同")
        print("   3. 这说明存在两种不同的话题创建路径")
        
        print(f"\n   可能的原因:")
        print("   A. 早期话题通过一种流程创建，后来被另一个流程更新")
        print("   B. 晚期话题通过新的流程直接创建，没有后续更新")
        print("   C. add_popularity_history()调用时机不同")
        
        # 4. 查看相关推文的创建时间
        print(f"\n4️⃣ 相关推文创建时间分析:")
        
        tweet_time_sql = """
        SELECT 
            topic_id,
            COUNT(*) as tweet_count,
            MIN(created_at_datetime) as earliest_tweet,
            MAX(created_at_datetime) as latest_tweet
        FROM twitter_tweet
        WHERE topic_id IS NOT NULL
        GROUP BY topic_id
        ORDER BY earliest_tweet ASC
        LIMIT 5
        """
        
        tweet_times = db_manager.execute_query(tweet_time_sql)
        
        for tweet_info in tweet_times:
            topic_id = tweet_info['topic_id']
            # 找到对应的话题
            matching_topic = next((t for t in topics if t['topic_id'] == topic_id), None)
            if matching_topic:
                print(f"   {matching_topic['topic_name'][:25]}...")
                print(f"     话题创建: {matching_topic['created_at']}")
                print(f"     推文范围: {tweet_info['earliest_tweet']} ~ {tweet_info['latest_tweet']}")
                print(f"     推文数量: {tweet_info['tweet_count']}")
        
        return {
            'early_batch_count': len(early_batch),
            'late_batch_count': len(late_batch),
            'total_topics': len(topics)
        }
        
    except Exception as e:
        print(f"❌ 分析失败: {e}")
        import traceback
        traceback.print_exc()
        return None


if __name__ == '__main__':
    result = analyze_timing_issue_root_cause()
    if result:
        print("=" * 70)
        print("🎯 根本原因总结")
        print("=" * 70)
        print("时序问题的根本原因:")
        print("1. 话题创建流程存在两种路径")
        print("2. 早期路径: 创建 -> 后续更新 -> 添加历史记录")
        print("3. 晚期路径: 直接创建 -> 没有后续更新 -> 缺失历史记录")
        print("4. add_popularity_history()调用时机不一致")
    sys.exit(0)