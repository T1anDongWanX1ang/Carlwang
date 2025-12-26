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

from src.models.tweet import Tweet
from src.utils.topic_analyzer import TopicAnalyzer

def create_test_tweets():
    """创建测试推文数据"""
    base_time = datetime.now()
    tweets = []
    
    # 模拟5分钟内的推文
    for i in range(10):
        tweet = Tweet(
            id_str=f"tweet_{i}",
            created_at_datetime=base_time - timedelta(minutes=i),
            favorite_count=10 + i * 5,
            retweet_count=5 + i * 2,
            reply_count=3 + i,
            full_text=f"测试推文内容 {i}"
        )
        tweets.append(tweet)
    
    return tweets

def test_propagation_speed():
    """测试传播速度计算"""
    print("=== 测试Propagation Speed修正 ===")
    
    # 创建测试数据
    tweets = create_test_tweets()
    print(f"创建了 {len(tweets)} 条测试推文")
    
    # 打印推文信息
    for i, tweet in enumerate(tweets):
        print(f"推文{i}: 时间={tweet.created_at_datetime}, 互动={tweet.favorite_count}+{tweet.retweet_count}+{tweet.reply_count}")
    
    # 创建分析器
    analyzer = TopicAnalyzer()
    
    # 计算传播速度
    print("\n=== 计算传播速度 ===")
    speeds = analyzer.calculate_propagation_speeds(tweets)
    
    print(f"5分钟传播速度: {speeds['5m']}")
    print(f"1小时传播速度: {speeds['1h']}")
    print(f"4小时传播速度: {speeds['4h']}")
    
    # 验证结果
    if all(speed > 0 for speed in speeds.values()):
        print("\n✅ 修正成功！所有传播速度都大于0")
    else:
        print("\n❌ 仍有问题，某些速度为0")
        
    return speeds

def test_edge_cases():
    """测试边界情况"""
    print("\n=== 测试边界情况 ===")
    
    analyzer = TopicAnalyzer()
    
    # 测试空推文列表
    empty_speeds = analyzer.calculate_propagation_speeds([])
    print(f"空推文列表: {empty_speeds}")
    
    # 测试单条推文
    single_tweet = [Tweet(
        id_str="single_tweet",
        created_at_datetime=datetime.now(),
        favorite_count=10,
        retweet_count=5,
        reply_count=3,
        full_text="单条推文"
    )]
    single_speeds = analyzer.calculate_propagation_speeds(single_tweet)
    print(f"单条推文: {single_speeds}")
    
    # 测试无互动推文
    no_engagement_tweets = []
    for i in range(5):
        tweet = Tweet(
            id_str=f"no_eng_{i}",
            created_at_datetime=datetime.now() - timedelta(minutes=i),
            favorite_count=0,
            retweet_count=0,
            reply_count=0,
            full_text=f"无互动推文 {i}"
        )
        no_engagement_tweets.append(tweet)
    
    no_eng_speeds = analyzer.calculate_propagation_speeds(no_engagement_tweets)
    print(f"无互动推文: {no_eng_speeds}")

if __name__ == '__main__':
    try:
        # 主要测试
        speeds = test_propagation_speed()
        
        # 边界情况测试
        test_edge_cases()
        
        print("\n=== 测试完成 ===")
        
    except Exception as e:
        print(f"测试失败: {e}")
        import traceback
        traceback.print_exc()