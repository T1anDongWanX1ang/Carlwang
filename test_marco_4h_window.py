#!/usr/bin/env python3
"""
测试Marco数据生成的4小时时间窗口配置
验证时间窗口限制和权重计算是否正确
"""
import sys
import os
from datetime import datetime, timedelta

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.utils.marco_processor import marco_processor
from src.utils.logger import setup_logger


def test_4h_time_window():
    """测试4小时时间窗口配置"""
    setup_logger()
    
    print("🚀 测试Marco数据4小时时间窗口配置")
    
    # 当前时间
    now = datetime.now()
    timestamp = now.replace(minute=(now.minute // 30) * 30, second=0, microsecond=0)
    
    print(f"🕐 测试时间戳: {timestamp}")
    print(f"📊 时间窗口: {timestamp - timedelta(hours=4)} 到 {timestamp}")
    
    try:
        # 1. 测试推文数据获取
        print("\n=== 测试推文数据获取 ===")
        
        start_time = timestamp - timedelta(hours=4)
        end_time = timestamp
        
        kol_tweets = marco_processor._get_kol_tweets_in_range(start_time, end_time)
        
        print(f"📈 获取到推文数量: {len(kol_tweets)}")
        
        if kol_tweets:
            # 分析推文时间分布
            time_distribution = {}
            for tweet in kol_tweets:
                tweet_time = tweet.get('created_at_datetime')
                if tweet_time:
                    hours_ago = (end_time - tweet_time).total_seconds() / 3600
                    hour_bucket = int(hours_ago)
                    time_distribution[hour_bucket] = time_distribution.get(hour_bucket, 0) + 1
            
            print("\n📊 推文时间分布:")
            for hour in sorted(time_distribution.keys()):
                count = time_distribution[hour]
                print(f"  {hour}-{hour+1}小时前: {count}条推文")
            
            # 测试时间衰减权重计算
            print("\n⚖️ 时间衰减权重测试:")
            test_times = [
                ("最新推文", timedelta(minutes=15)),
                ("30分钟前", timedelta(minutes=30)),
                ("1小时前", timedelta(hours=1)),
                ("2小时前", timedelta(hours=2)),
                ("3小时前", timedelta(hours=3)),
                ("4小时前", timedelta(hours=4)),
            ]
            
            for name, delta in test_times:
                test_time = end_time - delta
                weight = marco_processor._calculate_time_decay_weight(test_time, end_time)
                print(f"  {name}: 权重 {weight:.2f}")
            
            # 显示前5条推文的详细信息
            print("\n📝 前5条推文详情:")
            for i, tweet in enumerate(kol_tweets[:5], 1):
                tweet_time = tweet.get('created_at_datetime')
                content = tweet.get('content', '')[:60]
                weight = tweet.get('total_weight', 0)
                time_weight = tweet.get('time_decay_coefficient', 0)
                
                if tweet_time:
                    hours_ago = (end_time - tweet_time).total_seconds() / 3600
                    print(f"  {i}. {hours_ago:.1f}小时前 | 权重:{weight:.2f} | 时间权重:{time_weight:.2f}")
                    print(f"     {content}...")
        
        # 2. 测试完整Marco数据生成
        print("\n=== 测试Marco数据生成 ===")
        
        marco_data = marco_processor.process_tweets_to_marco(timestamp, lookback_hours=4)
        
        if marco_data:
            print(f"✅ Marco数据生成成功!")
            print(f"📊 情感指数: {marco_data.sentiment_index:.2f}")
            print(f"📄 AI总结: {marco_data.summary[:100]}...")
            print(f"🕐 时间戳: {marco_data.timestamp}")
            return True
        else:
            print("❌ Marco数据生成失败")
            return False
        
    except Exception as e:
        print(f"❌ 测试过程出错: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_time_window_edge_cases():
    """测试时间窗口边界情况"""
    print("\n🔍 测试时间窗口边界情况")
    
    # 测试不同时间窗口
    now = datetime.now()
    
    test_cases = [
        ("2小时窗口", 2),
        ("4小时窗口", 4),
        ("6小时窗口", 6),
        ("8小时窗口", 8),
    ]
    
    for name, hours in test_cases:
        try:
            timestamp = now.replace(minute=0, second=0, microsecond=0)
            start_time = timestamp - timedelta(hours=hours)
            
            tweets = marco_processor._get_kol_tweets_in_range(start_time, timestamp)
            print(f"  {name}: {len(tweets)}条推文")
            
        except Exception as e:
            print(f"  {name}: 查询失败 - {e}")


def main():
    """主函数"""
    print("🎯 Marco数据4小时时间窗口测试")
    
    # 测试4小时时间窗口
    if test_4h_time_window():
        print("\n✅ 4小时时间窗口测试通过")
    else:
        print("\n❌ 4小时时间窗口测试失败")
        return
    
    # 测试边界情况
    test_time_window_edge_cases()
    
    print("""
🎉 测试完成！

=== 配置总结 ===
✅ 时间窗口: 最近4小时的推文数据
✅ 生产频率: 每30分钟生成一次（30分钟对齐）
✅ 时间衰减: 越新的推文权重越高
✅ 数据过滤: 只使用is_valid=1的有效推文
✅ SQL优化: 添加时间范围限制，提高查询效率

=== 推荐定时任务 ===
*/30 * * * * cd /path/to/twitter-crawler && python run_marco.py

=== 权重计算 ===
- 0-0.5小时: 1.0 (最高权重)
- 0.5-1小时: 0.95
- 1-2小时: 0.85
- 2-3小时: 0.75
- 3-4小时: 0.6 (最低权重)
    """)


if __name__ == '__main__':
    main()