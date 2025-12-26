#!/usr/bin/env python3
"""
验证目标推文时间与3小时窗口
"""
import sys
from pathlib import Path
from datetime import datetime, timedelta, timezone

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.api.twitter_api import twitter_api
from src.utils.logger import get_logger

def verify_tweet_times():
    """验证目标推文时间"""
    logger = get_logger(__name__)
    
    logger.info("=" * 80)
    logger.info("🔧 验证目标推文时间与3小时窗口")
    logger.info("=" * 80)
    
    # 目标推文ID
    target_tweet_ids = ["1998337381150212401", "1998316328139296827"]
    
    # 当前时间和3小时前
    now = datetime.now()
    three_hours_ago = now - timedelta(hours=3)
    
    logger.info(f"⏰ 当前时间: {now.strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"⏰ 3小时前: {three_hours_ago.strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 获取数据
    for list_id in ["1996863048959820198", "1996848536520897010"]:
        logger.info(f"\n📋 检查List: {list_id}")
        
        try:
            # 获取更多数据
            tweets, _ = twitter_api.fetch_tweets(list_id=list_id, count=200)
            
            if not tweets:
                logger.warning(f"⚠️ List {list_id} 没有数据")
                continue
            
            logger.info(f"📊 获取到 {len(tweets)} 条推文")
            
            # 查找目标推文
            for tweet in tweets:
                tweet_id = tweet.get('id_str', '')
                
                if tweet_id in target_tweet_ids:
                    user_info = tweet.get('user', {})
                    user_name = user_info.get('name', 'Unknown')
                    created_at_str = tweet.get('created_at', '')
                    
                    logger.info(f"🎯 找到目标推文: {tweet_id}")
                    logger.info(f"   用户: {user_name}")
                    logger.info(f"   原始时间: {created_at_str}")
                    
                    # 解析时间
                    try:
                        from dateutil import parser as date_parser
                        tweet_time = date_parser.parse(created_at_str)
                        
                        # 应用UTC时间转换逻辑（与修复后的代码一致）
                        if tweet_time.tzinfo:
                            tweet_time_local = tweet_time.astimezone().replace(tzinfo=None)
                        elif created_at_str.endswith('+0000') or 'GMT' in created_at_str or 'UTC' in created_at_str:
                            tweet_time_local = tweet_time.replace(tzinfo=timezone.utc).astimezone().replace(tzinfo=None)
                        else:
                            tweet_time_local = tweet_time
                        
                        logger.info(f"   本地时间: {tweet_time_local.strftime('%Y-%m-%d %H:%M:%S')}")
                        
                        # 检查是否在3小时窗口内
                        time_diff = now - tweet_time_local
                        hours_ago = time_diff.total_seconds() / 3600
                        is_within_3h = tweet_time_local >= three_hours_ago
                        
                        logger.info(f"   距离现在: {hours_ago:.1f} 小时")
                        logger.info(f"   在3小时内: {'✅是' if is_within_3h else '❌否'}")
                        
                        if not is_within_3h:
                            logger.warning(f"   ⚠️ 推文超出3小时限制，会被时间过滤器过滤掉")
                            logger.info(f"   💡 建议调整时间限制或手动测试该推文")
                        else:
                            logger.info(f"   ✅ 推文在时间窗口内，应该被处理")
                        
                    except Exception as e:
                        logger.error(f"   ❌ 时间解析失败: {e}")
            
        except Exception as e:
            logger.error(f"❌ 检查List {list_id} 失败: {e}")
    
    logger.info(f"\n" + "=" * 80)
    logger.info(f"💡 如果目标推文超出时间限制，可以:")
    logger.info(f"   1. 调整 --hours-limit 参数为更大值（如6或12小时）")
    logger.info(f"   2. 直接测试修复逻辑是否生效（通过手动构造测试）")
    logger.info(f"=" * 80)

if __name__ == '__main__':
    print("开始验证推文时间...")
    verify_tweet_times()
    print("\n验证完成!")