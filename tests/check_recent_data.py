#!/usr/bin/env python3
"""
专门检查有1小时前数据的list
"""
import sys
from pathlib import Path
from datetime import datetime, timedelta
import json

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.api.twitter_api import twitter_api
from src.utils.logger import get_logger

def check_recent_data():
    """检查最近数据"""
    logger = get_logger(__name__)
    
    # 您提到的list IDs (从配置文件)
    with open('config/config.json', 'r') as f:
        config_data = json.load(f)
    
    current_list_ids = config_data.get('api', {}).get('default_params', {}).get('list_ids', [])
    logger.info(f"🔍 当前配置的List IDs: {current_list_ids}")
    
    # 检查每个当前使用的List
    hours_limit = 3
    time_cutoff = datetime.now() - timedelta(hours=hours_limit)
    
    logger.info(f"📅 时间截止点: {time_cutoff.strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"⏰ 当前时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    for list_id in current_list_ids:
        logger.info(f"\n" + "="*60)
        logger.info(f"📋 检查当前使用的List: {list_id}")
        logger.info(f"="*60)
        
        try:
            # 获取第一页数据
            tweets, _ = twitter_api.fetch_tweets(list_id=list_id, count=100)
            
            if not tweets:
                logger.warning(f"⚠️ List {list_id} 没有数据")
                continue
                
            logger.info(f"📊 获取到 {len(tweets)} 条推文")
            
            # 分析时间分布
            recent_tweets = []
            solana_tweets = []
            
            for tweet in tweets[:30]:  # 分析前30条
                user_info = tweet.get('user', {})
                user_name = user_info.get('name', 'Unknown')
                created_at_str = tweet.get('created_at', '')
                
                if created_at_str:
                    try:
                        from dateutil import parser as date_parser
                        tweet_time = date_parser.parse(created_at_str)
                        # 如果是UTC时间，转换为本地时间进行比较
                        if tweet_time.tzinfo:
                            # 转换为本地时间
                            tweet_time = tweet_time.astimezone().replace(tzinfo=None)
                        # 如果没有时区信息但格式符合UTC标准(+0000结尾)，假设为UTC
                        elif created_at_str.endswith('+0000') or 'GMT' in created_at_str or 'UTC' in created_at_str:
                            from datetime import timezone
                            # 将其视为UTC时间并转换为本地时间
                            tweet_time = tweet_time.replace(tzinfo=timezone.utc).astimezone().replace(tzinfo=None)
                        
                        hours_ago = (datetime.now() - tweet_time).total_seconds() / 3600
                        
                        tweet_info = {
                            'user_name': user_name,
                            'created_at': created_at_str,
                            'hours_ago': hours_ago,
                            'within_3h': hours_ago <= 3,
                            'within_1h': hours_ago <= 1,
                            'is_solana': 'solana' in user_name.lower()
                        }
                        
                        recent_tweets.append(tweet_info)
                        
                        if tweet_info['is_solana']:
                            solana_tweets.append(tweet_info)
                            
                    except Exception as e:
                        logger.warning(f"解析时间失败: {created_at_str}")
            
            # 分析结果
            recent_tweets.sort(key=lambda x: x['hours_ago'])
            
            within_1h = [t for t in recent_tweets if t['within_1h']]
            within_3h = [t for t in recent_tweets if t['within_3h']]
            
            logger.info(f"📊 时间分布分析:")
            logger.info(f"   1小时内: {len(within_1h)} 条")
            logger.info(f"   3小时内: {len(within_3h)} 条")
            logger.info(f"   Solana相关: {len(solana_tweets)} 条")
            
            # 显示最近的推文
            if within_1h:
                logger.info(f"✅ 1小时内的推文:")
                for t in within_1h[:5]:
                    marker = "🟠SOLANA" if t['is_solana'] else "🔵其他"
                    logger.info(f"   {marker} {t['hours_ago']:.1f}h前: {t['user_name']}")
                    
            elif within_3h:
                logger.info(f"✅ 3小时内的推文:")
                for t in within_3h[:5]:
                    marker = "🟠SOLANA" if t['is_solana'] else "🔵其他"
                    logger.info(f"   {marker} {t['hours_ago']:.1f}h前: {t['user_name']}")
            else:
                logger.warning(f"⚠️ 该List没有3小时内的新推文")
                logger.info(f"   最新推文:")
                for t in recent_tweets[:3]:
                    marker = "🟠SOLANA" if t['is_solana'] else "🔵其他"
                    logger.info(f"   {marker} {t['hours_ago']:.1f}h前: {t['user_name']}")
            
            # 特别检查Solana 1小时内数据
            solana_1h = [t for t in solana_tweets if t['within_1h']]
            if solana_1h:
                logger.info(f"🟠 发现1小时内的Solana数据:")
                for t in solana_1h:
                    logger.info(f"   ✅ {t['hours_ago']:.1f}h前: {t['user_name']} - {t['created_at']}")
                    logger.error(f"   🚨 这些数据应该被保留，但可能被3小时限制过滤了!")
                    
        except Exception as e:
            logger.error(f"❌ 检查List {list_id} 失败: {e}")
    
    # 建议
    logger.info(f"\n" + "="*80)
    logger.info(f"💡 分析建议:")
    logger.info(f"="*80)
    logger.info(f"1. 如果确实有1小时前的Solana数据被过滤:")
    logger.info(f"   - 考虑将默认时间窗口从3小时改为6小时")
    logger.info(f"   - 或者检查List配置是否正确")
    logger.info(f"2. 如果没有发现1小时内数据:")
    logger.info(f"   - 可能数据已经过时，当前3小时窗口是合理的")
    logger.info(f"   - 检查是否需要更新List或添加更活跃的List")

if __name__ == '__main__':
    print("开始检查最近数据...")
    check_recent_data()
    print("\n检查完成!")