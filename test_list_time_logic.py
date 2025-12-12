#!/usr/bin/env python3
"""
测试list拉取时间截止逻辑
验证在同一个list中，是否会因为某个项目的推文时间到达截止点而影响其他项目的数据拉取
"""
import sys
from pathlib import Path
from datetime import datetime, timedelta
import json
from collections import defaultdict

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.api.twitter_api import twitter_api
from src.utils.logger import get_logger

def test_list_time_logic():
    """测试list时间逻辑"""
    logger = get_logger(__name__)
    
    # 测试的list ID（用户提供的）
    test_list_id = "1996845120008900840"
    logger.info(f"开始测试list {test_list_id} 的时间截止逻辑")
    
    # 测试不同的时间限制
    time_limits = [2, 5, 10, 24]  # 小时
    
    for hours_limit in time_limits:
        logger.info("=" * 60)
        logger.info(f"测试 {hours_limit} 小时时间限制")
        logger.info("=" * 60)
        
        # 统计数据
        project_tweet_counts = defaultdict(int)
        project_latest_times = defaultdict(list)
        total_tweets = 0
        
        try:
            # 使用现有的API拉取逻辑
            all_tweets = twitter_api.fetch_all_tweets(
                list_id=test_list_id,
                max_pages=10,  # 多拉几页确保有足够数据
                page_size=100,
                hours_limit=hours_limit
            )
            
            # 分析推文
            for tweet in all_tweets:
                total_tweets += 1
                
                # 提取用户信息
                user_info = tweet.get('user', {})
                user_name = user_info.get('name', 'Unknown')
                screen_name = user_info.get('screen_name', 'unknown')
                
                # 提取推文时间
                created_at = tweet.get('created_at', '')
                tweet_id = tweet.get('id_str', 'unknown')
                
                # 判断是否是Bitcoin或Solana相关
                full_text = tweet.get('full_text', '').lower()
                project_type = 'other'
                
                if any(keyword in user_name.lower() for keyword in ['bitcoin', 'btc']):
                    project_type = 'bitcoin'
                elif any(keyword in user_name.lower() for keyword in ['solana', 'sol']):
                    project_type = 'solana'
                elif any(keyword in full_text for keyword in ['bitcoin', 'btc', '$btc']):
                    project_type = 'bitcoin_mention'
                elif any(keyword in full_text for keyword in ['solana', 'sol', '$sol']):
                    project_type = 'solana_mention'
                
                project_tweet_counts[project_type] += 1
                project_latest_times[project_type].append({
                    'time': created_at,
                    'user': f"{user_name} (@{screen_name})",
                    'tweet_id': tweet_id,
                    'text_preview': full_text[:100] + '...' if len(full_text) > 100 else full_text
                })
            
            # 输出统计结果
            logger.info(f"\n时间限制 {hours_limit} 小时的测试结果:")
            logger.info(f"总推文数: {total_tweets}")
            
            for project, count in project_tweet_counts.items():
                if count > 0:
                    logger.info(f"\n{project} 相关推文: {count} 条")
                    
                    # 显示最新的3条推文
                    latest_tweets = sorted(project_latest_times[project], 
                                         key=lambda x: x['time'], reverse=True)[:3]
                    
                    for i, tweet_info in enumerate(latest_tweets, 1):
                        logger.info(f"  {i}. 时间: {tweet_info['time']}")
                        logger.info(f"     用户: {tweet_info['user']}")
                        logger.info(f"     ID: {tweet_info['tweet_id']}")
                        logger.info(f"     内容: {tweet_info['text_preview']}")
                        logger.info("")
                        
            # 特别检查Bitcoin数据是否存在
            bitcoin_count = project_tweet_counts.get('bitcoin', 0) + project_tweet_counts.get('bitcoin_mention', 0)
            solana_count = project_tweet_counts.get('solana', 0) + project_tweet_counts.get('solana_mention', 0)
            
            if bitcoin_count > 0:
                logger.info(f"✅ Bitcoin数据正常: {bitcoin_count} 条推文")
            else:
                logger.warning(f"❌ Bitcoin数据缺失: 0 条推文")
                
            if solana_count > 0:
                logger.info(f"✅ Solana数据正常: {solana_count} 条推文")
            else:
                logger.warning(f"❌ Solana数据缺失: 0 条推文")
                
        except Exception as e:
            logger.error(f"测试 {hours_limit} 小时限制时发生异常: {e}")
            import traceback
            logger.error(f"异常堆栈: {traceback.format_exc()}")
    
    logger.info("\n" + "=" * 60)
    logger.info("测试总结:")
    logger.info("如果在较短的时间限制下Bitcoin数据缺失，")
    logger.info("而在较长的时间限制下Bitcoin数据正常，")
    logger.info("则说明时间截止逻辑确实存在问题。")
    logger.info("=" * 60)

def analyze_list_structure():
    """分析list结构，检查推文的时间分布"""
    logger = get_logger(__name__)
    
    test_list_id = "1996845120008900840"
    logger.info(f"分析list {test_list_id} 的结构和时间分布")
    
    try:
        # 拉取更多数据进行分析
        all_tweets = twitter_api.fetch_all_tweets(
            list_id=test_list_id,
            max_pages=20,  # 拉取更多页面
            page_size=100,
            hours_limit=72  # 3天，确保拉取到足够多的历史数据
        )
        
        # 按页面分析推文时间分布
        tweets_by_time = []
        
        for tweet in all_tweets:
            user_info = tweet.get('user', {})
            user_name = user_info.get('name', 'Unknown')
            created_at = tweet.get('created_at', '')
            tweet_id = tweet.get('id_str', 'unknown')
            
            try:
                from dateutil import parser as date_parser
                tweet_time = date_parser.parse(created_at)
                if tweet_time.tzinfo:
                    tweet_time = tweet_time.replace(tzinfo=None)
                
                tweets_by_time.append({
                    'time': tweet_time,
                    'time_str': created_at,
                    'user_name': user_name,
                    'tweet_id': tweet_id,
                    'is_bitcoin': any(keyword in user_name.lower() for keyword in ['bitcoin', 'btc']),
                    'is_solana': any(keyword in user_name.lower() for keyword in ['solana', 'sol']),
                })
            except Exception as e:
                logger.warning(f"解析时间失败: {created_at}, 错误: {e}")
        
        # 按时间排序
        tweets_by_time.sort(key=lambda x: x['time'], reverse=True)
        
        logger.info(f"\n找到 {len(tweets_by_time)} 条有效推文")
        logger.info("\n前20条推文的时间分布（按时间倒序）:")
        
        for i, tweet_info in enumerate(tweets_by_time[:20], 1):
            project_tag = ""
            if tweet_info['is_bitcoin']:
                project_tag = "[Bitcoin]"
            elif tweet_info['is_solana']:
                project_tag = "[Solana]"
            else:
                project_tag = "[Other]"
                
            logger.info(f"{i:2d}. {tweet_info['time_str']} {project_tag} {tweet_info['user_name']} (ID: {tweet_info['tweet_id']})")
        
        # 分析不同时间窗口的项目分布
        logger.info("\n不同时间窗口的项目分布分析:")
        time_windows = [2, 5, 10, 24, 72]  # 小时
        
        for hours in time_windows:
            cutoff_time = datetime.now() - timedelta(hours=hours)
            
            bitcoin_count = 0
            solana_count = 0
            other_count = 0
            total_in_window = 0
            
            for tweet_info in tweets_by_time:
                if tweet_info['time'] >= cutoff_time:
                    total_in_window += 1
                    if tweet_info['is_bitcoin']:
                        bitcoin_count += 1
                    elif tweet_info['is_solana']:
                        solana_count += 1
                    else:
                        other_count += 1
            
            logger.info(f"过去 {hours:2d} 小时: 总计{total_in_window:3d}条 | Bitcoin: {bitcoin_count:2d}条 | Solana: {solana_count:2d}条 | Other: {other_count:2d}条")
            
    except Exception as e:
        logger.error(f"分析list结构时发生异常: {e}")
        import traceback
        logger.error(f"异常堆栈: {traceback.format_exc()}")

if __name__ == '__main__':
    print("开始测试list时间截止逻辑...")
    
    # 测试1: 验证时间逻辑问题
    test_list_time_logic()
    
    print("\n" + "="*80 + "\n")
    
    # 测试2: 分析list结构
    analyze_list_structure()
    
    print("\n测试完成!")