#!/usr/bin/env python3
"""
测试智能项目级别时间截止逻辑
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

def test_intelligent_time_logic():
    """测试智能项目级别时间逻辑"""
    logger = get_logger(__name__)
    
    # 测试的list ID
    test_list_id = "1996845120008900840"
    logger.info(f"测试智能项目级别时间截止逻辑: list {test_list_id}")
    
    # 测试不同的时间限制，重点验证项目级别的检测
    time_limits = [8, 10, 12, 15]  # 小时
    
    for hours_limit in time_limits:
        logger.info("=" * 60)
        logger.info(f"测试 {hours_limit} 小时时间限制 (智能项目检测)")
        logger.info("=" * 60)
        
        # 统计数据
        project_tweet_counts = defaultdict(int)
        project_latest_times = defaultdict(list)
        total_tweets = 0
        
        try:
            # 使用智能项目级别检测的API拉取逻辑
            all_tweets = twitter_api.fetch_all_tweets(
                list_id=test_list_id,
                max_pages=20,  # 拉更多页验证智能停止
                page_size=100,
                hours_limit=hours_limit
            )
            
            # 分析推文
            project_users = {}  # {project_type: [user_names]}
            
            for tweet in all_tweets:
                total_tweets += 1
                
                # 提取用户信息
                user_info = tweet.get('user', {})
                user_name = user_info.get('name', 'Unknown')
                screen_name = user_info.get('screen_name', 'unknown')
                user_id = user_info.get('id_str', 'unknown')
                
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
                elif any(keyword in user_name.lower() for keyword in ['doge']):
                    project_type = 'dogecoin'
                
                project_tweet_counts[project_type] += 1
                project_latest_times[project_type].append({
                    'time': created_at,
                    'user': f"{user_name} (@{screen_name})",
                    'user_id': user_id,
                    'tweet_id': tweet_id,
                })
                
                # 记录项目用户
                if project_type not in project_users:
                    project_users[project_type] = set()
                project_users[project_type].add(f"{user_name} ({user_id})")
            
            # 输出统计结果
            logger.info(f"\n智能检测结果 - 时间限制 {hours_limit} 小时:")
            logger.info(f"总推文数: {total_tweets}")
            
            for project, count in project_tweet_counts.items():
                if count > 0:
                    logger.info(f"\n📊 {project.upper()} 项目:")
                    logger.info(f"  推文数: {count} 条")
                    logger.info(f"  用户数: {len(project_users.get(project, set()))} 个")
                    
                    # 显示用户列表
                    users = list(project_users.get(project, set()))[:3]  # 最多显示3个用户
                    for i, user in enumerate(users, 1):
                        logger.info(f"    {i}. {user}")
                    if len(project_users.get(project, set())) > 3:
                        logger.info(f"    ... 还有 {len(project_users.get(project, set())) - 3} 个用户")
                    
                    # 显示时间分布
                    latest_tweets = sorted(project_latest_times[project], 
                                         key=lambda x: x['time'], reverse=True)[:2]
                    
                    logger.info(f"  最新推文:")
                    for i, tweet_info in enumerate(latest_tweets, 1):
                        logger.info(f"    {i}. {tweet_info['time']} - {tweet_info['user']}")
            
            # 关键验证：检查各项目数据完整性
            bitcoin_count = project_tweet_counts.get('bitcoin', 0)
            solana_count = project_tweet_counts.get('solana', 0)
            ethereum_count = project_tweet_counts.get('ethereum', 0)
            doge_count = project_tweet_counts.get('dogecoin', 0)
            
            logger.info(f"\n🔍 智能检测验证结果:")
            
            projects_found = 0
            if bitcoin_count > 0:
                logger.info(f"✅ Bitcoin数据: {bitcoin_count} 条推文")
                projects_found += 1
            else:
                logger.warning(f"⚠️ Bitcoin数据缺失: {bitcoin_count} 条推文")
                
            if solana_count > 0:
                logger.info(f"✅ Solana数据: {solana_count} 条推文")
                projects_found += 1
            else:
                logger.warning(f"⚠️ Solana数据缺失: {solana_count} 条推文")
                
            if ethereum_count > 0:
                logger.info(f"✅ Ethereum数据: {ethereum_count} 条推文")
                projects_found += 1
            else:
                logger.info(f"ℹ️ Ethereum数据: {ethereum_count} 条推文")
                
            if doge_count > 0:
                logger.info(f"✅ Dogecoin数据: {doge_count} 条推文")
                projects_found += 1
            else:
                logger.info(f"ℹ️ Dogecoin数据: {doge_count} 条推文")
            
            logger.info(f"📈 找到 {projects_found} 个活跃项目，总用户 {sum(len(users) for users in project_users.values())} 个")
                
        except Exception as e:
            logger.error(f"测试 {hours_limit} 小时限制时发生异常: {e}")
            import traceback
            logger.error(f"异常堆栈: {traceback.format_exc()}")
    
    logger.info("\n" + "=" * 60)
    logger.info("🎯 智能检测总结:")
    logger.info("新的智能项目级别检测应该能够：")
    logger.info("1. 跟踪每个项目/用户的最新推文时间")
    logger.info("2. 只有当所有项目都超时才停止拉取")
    logger.info("3. 避免因单个项目超时而影响其他项目数据")
    logger.info("4. 提供详细的项目级别时间分析日志")
    logger.info("=" * 60)

if __name__ == '__main__':
    print("开始测试智能项目级别时间逻辑...")
    test_intelligent_time_logic()
    print("\n测试完成!")