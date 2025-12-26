#!/usr/bin/env python3
"""
测试修复后的list时间截止逻辑
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

def test_fixed_time_logic():
    """测试修复后的时间逻辑"""
    logger = get_logger(__name__)
    
    # 测试的list ID
    test_list_id = "1996845120008900840"
    logger.info(f"测试修复后的list {test_list_id} 时间截止逻辑")
    
    # 重点测试之前有问题的时间限制
    time_limits = [10, 12, 15]  # 小时
    
    for hours_limit in time_limits:
        logger.info("=" * 60)
        logger.info(f"测试 {hours_limit} 小时时间限制")
        logger.info("=" * 60)
        
        # 统计数据
        project_tweet_counts = defaultdict(int)
        project_latest_times = defaultdict(list)
        total_tweets = 0
        
        try:
            # 使用修复后的API拉取逻辑
            all_tweets = twitter_api.fetch_all_tweets(
                list_id=test_list_id,
                max_pages=15,  # 拉更多页确保充分测试
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
                
                # 判断项目类型
                full_text = tweet.get('full_text', '').lower()
                project_type = 'other'
                
                if any(keyword in user_name.lower() for keyword in ['bitcoin', 'btc']):
                    project_type = 'bitcoin'
                elif any(keyword in user_name.lower() for keyword in ['solana', 'sol']):
                    project_type = 'solana'
                elif any(keyword in user_name.lower() for keyword in ['ethereum', 'eth']):
                    project_type = 'ethereum'
                
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
                    
                    # 显示最新的2条推文
                    latest_tweets = sorted(project_latest_times[project], 
                                         key=lambda x: x['time'], reverse=True)[:2]
                    
                    for i, tweet_info in enumerate(latest_tweets, 1):
                        logger.info(f"  {i}. 时间: {tweet_info['time']}")
                        logger.info(f"     用户: {tweet_info['user']}")
                        logger.info(f"     ID: {tweet_info['tweet_id']}")
                        logger.info("")
            
            # 关键验证：检查Bitcoin和Solana数据
            bitcoin_count = project_tweet_counts.get('bitcoin', 0)
            solana_count = project_tweet_counts.get('solana', 0)
            ethereum_count = project_tweet_counts.get('ethereum', 0)
            
            logger.info(f"\n🔍 关键验证结果:")
            if bitcoin_count > 0:
                logger.info(f"✅ Bitcoin数据正常: {bitcoin_count} 条推文")
            else:
                logger.warning(f"⚠️ Bitcoin数据缺失: {bitcoin_count} 条推文")
                
            if solana_count > 0:
                logger.info(f"✅ Solana数据正常: {solana_count} 条推文")
            else:
                logger.warning(f"⚠️ Solana数据缺失: {solana_count} 条推文")
                
            if ethereum_count > 0:
                logger.info(f"✅ Ethereum数据正常: {ethereum_count} 条推文")
            else:
                logger.info(f"ℹ️ Ethereum数据: {ethereum_count} 条推文（可能正常）")
                
        except Exception as e:
            logger.error(f"测试 {hours_limit} 小时限制时发生异常: {e}")
            import traceback
            logger.error(f"异常堆栈: {traceback.format_exc()}")
    
    logger.info("\n" + "=" * 60)
    logger.info("修复验证总结:")
    logger.info("如果现在Bitcoin和Solana数据都能正常获取，")
    logger.info("说明时间截止逻辑修复成功。")
    logger.info("=" * 60)

if __name__ == '__main__':
    print("开始测试修复后的时间逻辑...")
    test_fixed_time_logic()
    print("\n测试完成!")