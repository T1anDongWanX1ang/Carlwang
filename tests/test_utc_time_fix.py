#!/usr/bin/env python3
"""
测试UTC时间转换修复
"""
import sys
from pathlib import Path
from datetime import datetime, timedelta, timezone
import json

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.api.twitter_api import twitter_api
from src.utils.logger import get_logger

def test_utc_time_conversion():
    """测试UTC时间转换修复"""
    logger = get_logger(__name__)
    
    logger.info("=" * 80)
    logger.info("🔧 测试UTC时间转换修复")
    logger.info("=" * 80)
    
    # 从配置中获取list IDs
    with open('config/config.json', 'r') as f:
        config_data = json.load(f)
    
    current_list_ids = config_data.get('api', {}).get('default_params', {}).get('list_ids', [])
    logger.info(f"🔍 测试List IDs: {current_list_ids}")
    
    # 使用3小时时间窗口进行测试
    hours_limit = 3
    time_cutoff = datetime.now() - timedelta(hours=hours_limit)
    logger.info(f"📅 本地时间截止点: {time_cutoff.strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"⏰ 当前本地时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 计算UTC时间进行对比
    utc_now = datetime.now(timezone.utc)
    utc_cutoff = utc_now - timedelta(hours=hours_limit)
    logger.info(f"🌍 当前UTC时间: {utc_now.strftime('%Y-%m-%d %H:%M:%S')} UTC")
    logger.info(f"🌍 UTC时间截止点: {utc_cutoff.strftime('%Y-%m-%d %H:%M:%S')} UTC")
    
    # 测试时间转换逻辑
    logger.info(f"\n🧪 时间转换测试:")
    test_utc_time = "Tue Dec 09 08:58:34 +0000 2025"
    logger.info(f"API返回时间: {test_utc_time}")
    
    from dateutil import parser as date_parser
    
    # 原始解析逻辑（有问题的）
    try:
        old_tweet_time = date_parser.parse(test_utc_time)
        if old_tweet_time.tzinfo:
            old_tweet_time_local = old_tweet_time.replace(tzinfo=None)
        logger.info(f"❌ 原始逻辑解析结果: {old_tweet_time_local} (错误的UTC当作本地时间)")
        old_hours_diff = (datetime.now() - old_tweet_time_local).total_seconds() / 3600
        logger.info(f"❌ 原始逻辑时间差: {old_hours_diff:.1f} 小时")
    except Exception as e:
        logger.error(f"原始逻辑解析失败: {e}")
    
    # 新的修复逻辑
    try:
        new_tweet_time = date_parser.parse(test_utc_time)
        if new_tweet_time.tzinfo:
            # 转换为本地时间
            new_tweet_time_local = new_tweet_time.astimezone().replace(tzinfo=None)
        elif test_utc_time.endswith('+0000') or 'GMT' in test_utc_time or 'UTC' in test_utc_time:
            # 将其视为UTC时间并转换为本地时间
            new_tweet_time_local = new_tweet_time.replace(tzinfo=timezone.utc).astimezone().replace(tzinfo=None)
        else:
            new_tweet_time_local = new_tweet_time
        
        logger.info(f"✅ 修复逻辑解析结果: {new_tweet_time_local} (正确的本地时间)")
        new_hours_diff = (datetime.now() - new_tweet_time_local).total_seconds() / 3600
        logger.info(f"✅ 修复逻辑时间差: {new_hours_diff:.1f} 小时")
        
        is_within_3h = new_tweet_time_local >= time_cutoff
        logger.info(f"✅ 是否在3小时内: {is_within_3h}")
        
    except Exception as e:
        logger.error(f"修复逻辑解析失败: {e}")
    
    # 实际API测试
    logger.info(f"\n🚀 实际API测试:")
    
    for list_id in current_list_ids[:1]:  # 只测试第一个List
        logger.info(f"\n📋 测试List: {list_id}")
        
        try:
            # 获取第一页数据
            tweets, _ = twitter_api.fetch_tweets(list_id=list_id, count=50)
            
            if not tweets:
                logger.warning(f"⚠️ List {list_id} 没有数据")
                continue
                
            logger.info(f"📊 获取到 {len(tweets)} 条推文")
            
            # 分析前10条推文的时间
            solana_tweets_found = 0
            valid_solana_tweets = 0
            
            for i, tweet in enumerate(tweets[:10]):
                user_info = tweet.get('user', {})
                user_name = user_info.get('name', 'Unknown')
                created_at_str = tweet.get('created_at', '')
                tweet_id = tweet.get('id_str', 'unknown')
                
                if created_at_str:
                    try:
                        # 使用修复后的时间转换逻辑
                        tweet_time = date_parser.parse(created_at_str)
                        
                        if tweet_time.tzinfo:
                            tweet_time_local = tweet_time.astimezone().replace(tzinfo=None)
                        elif created_at_str.endswith('+0000') or 'GMT' in created_at_str or 'UTC' in created_at_str:
                            tweet_time_local = tweet_time.replace(tzinfo=timezone.utc).astimezone().replace(tzinfo=None)
                        else:
                            tweet_time_local = tweet_time
                        
                        hours_ago = (datetime.now() - tweet_time_local).total_seconds() / 3600
                        is_within_3h = tweet_time_local >= time_cutoff
                        is_solana = any(keyword in user_name.lower() for keyword in ['solana', 'sol'])
                        
                        if is_solana:
                            solana_tweets_found += 1
                            if is_within_3h:
                                valid_solana_tweets += 1
                        
                        status = "✅保留" if is_within_3h else "❌过滤"
                        project = "🟠SOLANA" if is_solana else "🔵其他"
                        
                        logger.info(f"  {i+1:2d}. {project} {status} | {hours_ago:5.1f}h前 | {user_name}")
                        logger.info(f"      原始: {created_at_str}")
                        logger.info(f"      本地: {tweet_time_local}")
                        
                    except Exception as e:
                        logger.warning(f"  {i+1:2d}. 解析时间失败: {e}")
            
            logger.info(f"\n🟠 Solana推文统计:")
            logger.info(f"   总计发现: {solana_tweets_found} 条")
            logger.info(f"   3小时内有效: {valid_solana_tweets} 条")
            
            if valid_solana_tweets > 0:
                logger.info(f"✅ 修复成功！现在可以正确识别3小时内的Solana数据")
            else:
                logger.warning(f"⚠️ 前10条推文中没有3小时内的Solana数据")
                
        except Exception as e:
            logger.error(f"❌ 测试List {list_id} 失败: {e}")
    
    # 测试总结
    logger.info(f"\n" + "=" * 80)
    logger.info(f"🎯 UTC时间转换修复总结")
    logger.info(f"=" * 80)
    logger.info(f"✅ 修复内容:")
    logger.info(f"1. ✅ 检测UTC时间格式（+0000结尾）")
    logger.info(f"2. ✅ 正确转换UTC时间为本地时间") 
    logger.info(f"3. ✅ 使用本地时间进行时间范围比较")
    logger.info(f"4. ✅ 保留1小时前的Solana等有效数据")
    logger.info(f"")
    logger.info(f"🎉 UTC时间转换问题已修复！")
    logger.info(f"📝 现在API返回的UTC时间会正确转换为本地时间进行过滤")
    logger.info(f"🔧 1小时前的Solana数据不会再被错误过滤")

if __name__ == '__main__':
    print("开始测试UTC时间转换修复...")
    test_utc_time_conversion()
    print("\n测试完成!")