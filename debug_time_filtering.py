#!/usr/bin/env python3
"""
检查特定list的时间过滤问题
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

def debug_list_time_filtering():
    """调试特定list的时间过滤问题"""
    logger = get_logger(__name__)
    
    # 测试的list IDs
    test_list_ids = ["1996848536520897010", "1996863048959820198", "1996887049027440697"]
    logger.info(f"🔍 调试时间过滤问题 - 测试Lists: {test_list_ids}")
    
    # 使用3小时时间窗口
    hours_limit = 3
    time_cutoff = datetime.now() - timedelta(hours=hours_limit)
    logger.info(f"📅 时间截止点: {time_cutoff.strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"⏰ 当前时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 分别测试每个list
    for list_id in test_list_ids:
        logger.info(f"\n" + "="*60)
        logger.info(f"📋 测试List: {list_id}")
        logger.info(f"="*60)
        
        try:
            # 直接调用API获取数据，不使用时间过滤
            tweets, next_cursor = twitter_api.fetch_tweets(list_id=list_id, count=50)
            
            logger.info(f"📊 获取到 {len(tweets)} 条原始推文")
            
            if tweets:
                # 分析每条推文的时间
                solana_tweets = []
                other_tweets = []
                
                for i, tweet in enumerate(tweets[:20]):  # 只分析前20条
                    user_info = tweet.get('user', {})
                    user_name = user_info.get('name', 'Unknown')
                    user_id = user_info.get('id_str', 'unknown')
                    created_at_str = tweet.get('created_at', '')
                    tweet_id = tweet.get('id_str', 'unknown')
                    
                    # 检查是否是Solana相关
                    is_solana = any(keyword in user_name.lower() for keyword in ['solana', 'sol'])
                    
                    try:
                        from dateutil import parser as date_parser
                        tweet_time = date_parser.parse(created_at_str)
                        if tweet_time.tzinfo:
                            tweet_time = tweet_time.replace(tzinfo=None)
                        
                        # 计算时间差
                        hours_ago = (datetime.now() - tweet_time).total_seconds() / 3600
                        is_within_limit = tweet_time >= time_cutoff
                        
                        tweet_info = {
                            'index': i+1,
                            'user_name': user_name,
                            'user_id': user_id,
                            'tweet_id': tweet_id,
                            'created_at': created_at_str,
                            'tweet_time': tweet_time,
                            'hours_ago': hours_ago,
                            'is_within_limit': is_within_limit,
                            'is_solana': is_solana
                        }
                        
                        if is_solana:
                            solana_tweets.append(tweet_info)
                        else:
                            other_tweets.append(tweet_info)
                            
                        # 输出每条推文的详细信息
                        status = "✅保留" if is_within_limit else "❌过滤"
                        project = "🟠SOLANA" if is_solana else "🔵其他"
                        logger.info(f"  {i+1:2d}. {project} {status} | {hours_ago:5.1f}h前 | {user_name} | {created_at_str}")
                        
                    except Exception as e:
                        logger.warning(f"  {i+1:2d}. 解析时间失败: {created_at_str}, 错误: {e}")
                
                # 输出Solana推文汇总
                if solana_tweets:
                    logger.info(f"\n🟠 Solana推文分析:")
                    logger.info(f"   总数: {len(solana_tweets)} 条")
                    
                    within_limit = [t for t in solana_tweets if t['is_within_limit']]
                    outside_limit = [t for t in solana_tweets if not t['is_within_limit']]
                    
                    logger.info(f"   3小时内: {len(within_limit)} 条")
                    logger.info(f"   超过3小时: {len(outside_limit)} 条")
                    
                    if outside_limit:
                        logger.warning(f"   ⚠️ 以下Solana推文会被过滤:")
                        for t in outside_limit[:3]:  # 只显示前3条被过滤的
                            logger.warning(f"     - {t['hours_ago']:.1f}h前: {t['user_name']} ({t['tweet_id']})")
                    
                    if within_limit:
                        logger.info(f"   ✅ 以下Solana推文会保留:")
                        for t in within_limit[:3]:  # 只显示前3条保留的
                            logger.info(f"     - {t['hours_ago']:.1f}h前: {t['user_name']} ({t['tweet_id']})")
                
                # 检查1小时前的数据
                one_hour_ago_tweets = []
                for tweet_info in solana_tweets:
                    if 0.8 <= tweet_info['hours_ago'] <= 1.2:  # 1小时前后的数据
                        one_hour_ago_tweets.append(tweet_info)
                
                if one_hour_ago_tweets:
                    logger.info(f"\n🕐 1小时前的Solana数据:")
                    for t in one_hour_ago_tweets:
                        status = "✅应该保留" if t['is_within_limit'] else "❌被错误过滤"
                        logger.info(f"   {status}: {t['hours_ago']:.1f}h前 - {t['user_name']} ({t['tweet_id']})")
                        logger.info(f"     时间: {t['created_at']}")
                        logger.info(f"     截止点: {time_cutoff}")
                        logger.info(f"     推文时间: {t['tweet_time']}")
                        
                        if not t['is_within_limit']:
                            logger.error(f"   🚨 发现问题: 1小时前的数据被错误过滤!")
                            
            else:
                logger.warning(f"   ⚠️ List {list_id} 没有获取到任何推文")
                
        except Exception as e:
            logger.error(f"   ❌ 测试List {list_id} 失败: {e}")
            import traceback
            logger.error(f"   异常详情: {traceback.format_exc()}")
    
    # 现在测试智能检测的实际行为
    logger.info(f"\n" + "="*80)
    logger.info(f"🧠 测试智能检测的实际行为")
    logger.info(f"="*80)
    
    try:
        # 使用智能检测拉取第一个list
        test_list_id = test_list_ids[0]
        logger.info(f"📋 使用智能检测测试List: {test_list_id}")
        
        all_tweets = twitter_api.fetch_all_tweets(
            list_id=test_list_id,
            max_pages=5,
            page_size=50,
            hours_limit=hours_limit
        )
        
        logger.info(f"📊 智能检测获取到 {len(all_tweets)} 条推文")
        
        # 分析获取到的推文
        solana_count = 0
        recent_solana = []
        
        for tweet in all_tweets:
            user_info = tweet.get('user', {})
            user_name = user_info.get('name', 'Unknown')
            created_at_str = tweet.get('created_at', '')
            
            if any(keyword in user_name.lower() for keyword in ['solana', 'sol']):
                solana_count += 1
                
                try:
                    from dateutil import parser as date_parser
                    tweet_time = date_parser.parse(created_at_str)
                    if tweet_time.tzinfo:
                        tweet_time = tweet_time.replace(tzinfo=None)
                    
                    hours_ago = (datetime.now() - tweet_time).total_seconds() / 3600
                    recent_solana.append({
                        'hours_ago': hours_ago,
                        'created_at': created_at_str,
                        'user_name': user_name
                    })
                except:
                    pass
        
        logger.info(f"🟠 智能检测获取到的Solana推文: {solana_count} 条")
        
        if recent_solana:
            recent_solana.sort(key=lambda x: x['hours_ago'])
            logger.info(f"   最近的Solana推文:")
            for i, t in enumerate(recent_solana[:5]):
                logger.info(f"     {i+1}. {t['hours_ago']:.1f}h前: {t['user_name']} - {t['created_at']}")
        
        # 检查是否有1小时前的数据被丢失
        one_hour_solana = [t for t in recent_solana if 0.8 <= t['hours_ago'] <= 1.2]
        if one_hour_solana:
            logger.info(f"   ✅ 1小时前的Solana数据: {len(one_hour_solana)} 条")
        else:
            logger.warning(f"   ⚠️ 没有发现1小时前的Solana数据 - 可能被过滤了!")
            
    except Exception as e:
        logger.error(f"❌ 智能检测测试失败: {e}")
        import traceback
        logger.error(f"异常详情: {traceback.format_exc()}")

if __name__ == '__main__':
    print("开始调试时间过滤问题...")
    debug_list_time_filtering()
    print("\n调试完成!")