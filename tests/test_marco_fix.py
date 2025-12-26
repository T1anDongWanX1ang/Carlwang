#!/usr/bin/env python3
"""
测试修复后的Marco处理器
"""
import sys
import os
from datetime import datetime, timedelta

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.database.tweet_dao import tweet_dao
from src.utils.marco_processor import MarcoProcessor
from src.utils.logger import setup_logger


def test_marco_time_query():
    """测试Marco的时间查询修复"""
    setup_logger()
    
    print("🔍 测试Marco处理器时间查询修复")
    print("=" * 60)
    
    try:
        db_manager = tweet_dao.db_manager
        
        # 1. 检查update_time字段的数据范围
        print("1️⃣ 检查update_time字段数据")
        print("-" * 40)
        
        update_time_sql = """
        SELECT 
            MIN(update_time) as min_update_time,
            MAX(update_time) as max_update_time,
            COUNT(*) as count_with_update_time
        FROM twitter_tweet
        WHERE update_time IS NOT NULL
        AND kol_id IS NOT NULL
        """
        
        update_time_result = db_manager.execute_query(update_time_sql)[0]
        
        print(f"📊 update_time字段统计:")
        print(f"   最早update_time: {update_time_result['min_update_time']}")
        print(f"   最晚update_time: {update_time_result['max_update_time']}")
        print(f"   有update_time的KOL推文数: {update_time_result['count_with_update_time']}")
        
        # 2. 使用修复后的查询逻辑测试
        print(f"\n2️⃣ 测试修复后的查询逻辑")
        print("-" * 40)
        
        # 使用最近4小时的时间窗口
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=4)
        
        print(f"🕐 测试时间范围: {start_time} 到 {end_time}")
        
        # 使用修复后的SQL查询
        fixed_sql = """
        SELECT 
            t.id_str,
            t.full_text,
            t.created_at_datetime,
            t.update_time,
            t.retweet_count,
            t.favorite_count,
            t.reply_count,
            t.kol_id,
            u.followers_count,
            u.screen_name,
            u.name
        FROM twitter_tweet t
        LEFT JOIN twitter_user u ON t.kol_id = u.id_str
        WHERE t.full_text IS NOT NULL
        AND LENGTH(t.full_text) > 20
        AND t.kol_id IS NOT NULL
        AND t.update_time >= %s
        AND t.update_time <= %s
        AND t.is_valid = 1
        ORDER BY t.update_time DESC
        LIMIT 10
        """
        
        results = db_manager.execute_query(fixed_sql, [start_time, end_time])
        
        if results:
            print(f"✅ 找到 {len(results)} 条符合条件的推文:")
            for i, tweet in enumerate(results[:3], 1):
                print(f"   {i}. 推文ID: {tweet['id_str']}")
                print(f"      KOL: {tweet['kol_id']} (粉丝: {tweet.get('followers_count', 'N/A')})")
                print(f"      更新时间: {tweet['update_time']}")
                print(f"      内容: {tweet['full_text'][:60]}...")
                print()
        else:
            print("❌ 仍然没有找到符合条件的推文")
            
            # 尝试更大的时间窗口
            print("🔍 尝试更大的时间窗口 (24小时):")
            start_time_24h = end_time - timedelta(hours=24)
            results_24h = db_manager.execute_query(fixed_sql, [start_time_24h, end_time])
            print(f"📊 24小时窗口结果: {len(results_24h) if results_24h else 0} 条")
        
        # 3. 测试Marco处理器
        print(f"\n3️⃣ 测试Marco处理器")
        print("-" * 40)
        
        marco_processor = MarcoProcessor()
        
        # 使用当前时间（30分钟对齐）
        current_time = datetime.now()
        # 对齐到30分钟
        aligned_minutes = (current_time.minute // 30) * 30
        marco_timestamp = current_time.replace(minute=aligned_minutes, second=0, microsecond=0)
        
        print(f"🕐 Marco目标时间: {marco_timestamp}")
        
        # 调用Marco处理器
        marco_data = marco_processor.process_tweets_to_marco(marco_timestamp, lookback_hours=4)
        
        if marco_data:
            print(f"✅ Marco数据生成成功!")
            print(f"   时间戳: {marco_data.timestamp}")
            print(f"   情感指数: {marco_data.sentiment_index}")
            print(f"   总结长度: {len(marco_data.summary) if marco_data.summary else 0}")
            if marco_data.summary:
                print(f"   总结预览: {marco_data.summary[:100]}...")
        else:
            print("❌ Marco数据生成失败")
        
        return bool(results) and bool(marco_data)
        
    except Exception as e:
        print(f"❌ 测试异常: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_fallback_logic():
    """测试回退逻辑（如果最近4小时没有数据，使用更大窗口）"""
    print(f"\n4️⃣ 测试回退逻辑")
    print("-" * 40)
    
    try:
        db_manager = tweet_dao.db_manager
        
        # 查找最新的update_time
        latest_sql = """
        SELECT MAX(update_time) as latest_update_time
        FROM twitter_tweet
        WHERE kol_id IS NOT NULL
        AND is_valid = 1
        """
        
        latest_result = db_manager.execute_query(latest_sql)[0]
        latest_time = latest_result['latest_update_time']
        
        if latest_time:
            print(f"📊 最新推文update_time: {latest_time}")
            
            # 计算时间差
            time_diff = datetime.now() - latest_time
            print(f"📊 距离现在: {time_diff}")
            
            if time_diff.total_seconds() > 4 * 3600:  # 超过4小时
                print("⚠️ 最新推文超过4小时，建议Marco使用自适应时间窗口")
            else:
                print("✅ 最新推文在4小时内，时间窗口正常")
        else:
            print("❌ 没有找到有效的推文update_time")
            
    except Exception as e:
        print(f"❌ 回退逻辑测试异常: {e}")


def main():
    """主函数"""
    print("🚀 Marco处理器修复测试")
    print("=" * 80)
    
    success = test_marco_time_query()
    test_fallback_logic()
    
    print("\n" + "=" * 80)
    print("🎯 修复验证结果:")
    
    if success:
        print("✅ Marco处理器修复成功")
        print("✅ 使用update_time字段进行时间查询")
        print("✅ 能够正确找到并处理KOL推文")
        print("✅ Marco数据生成正常")
    else:
        print("❌ Marco处理器仍有问题")
        print("💡 建议:")
        print("   1. 检查数据库中是否有足够新的推文数据")
        print("   2. 考虑调整Marco的时间窗口策略")
        print("   3. 检查其他查询条件是否过于严格")


if __name__ == '__main__':
    main()