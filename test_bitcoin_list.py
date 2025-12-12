#!/usr/bin/env python3
"""
测试特定List中Bitcoin数据的拉取情况
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

def test_bitcoin_list_data():
    """测试Bitcoin List数据拉取"""
    logger = get_logger(__name__)
    
    logger.info("=" * 80)
    logger.info("🔧 测试List 1996863048959820198 中Bitcoin数据的拉取")
    logger.info("=" * 80)
    
    target_list_id = "1996863048959820198"
    target_tweet_id = "1998337381150212401"  # 用户提到的Bitcoin推文ID
    
    # 3小时时间窗口
    hours_limit = 3
    time_cutoff = datetime.now() - timedelta(hours=hours_limit)
    logger.info(f"📅 本地时间截止点: {time_cutoff.strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"⏰ 当前本地时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"🎯 目标Bitcoin推文ID: {target_tweet_id}")
    
    try:
        # 获取数据（增加数量以确保能找到目标推文）
        tweets, _ = twitter_api.fetch_tweets(list_id=target_list_id, count=100)
        
        if not tweets:
            logger.warning(f"⚠️ List {target_list_id} 没有数据")
            return
            
        logger.info(f"📊 获取到 {len(tweets)} 条推文")
        
        # 查找并分析推文
        bitcoin_tweets = []
        target_tweet_found = False
        target_tweet_info = None
        
        for i, tweet in enumerate(tweets):
            user_info = tweet.get('user', {})
            user_name = user_info.get('name', 'Unknown')
            user_screen_name = user_info.get('screen_name', 'Unknown')
            created_at_str = tweet.get('created_at', '')
            tweet_id = tweet.get('id_str', 'unknown')
            
            # 检查是否是Bitcoin相关
            is_bitcoin = any(keyword in user_name.lower() for keyword in ['bitcoin']) or \
                        any(keyword in user_screen_name.lower() for keyword in ['bitcoin'])
            
            # 检查是否是目标推文
            is_target_tweet = tweet_id == target_tweet_id
            
            if created_at_str:
                try:
                    from dateutil import parser as date_parser
                    tweet_time = date_parser.parse(created_at_str)
                    
                    # 使用修复后的时间转换逻辑
                    if tweet_time.tzinfo:
                        tweet_time_local = tweet_time.astimezone().replace(tzinfo=None)
                    elif created_at_str.endswith('+0000') or 'GMT' in created_at_str or 'UTC' in created_at_str:
                        tweet_time_local = tweet_time.replace(tzinfo=timezone.utc).astimezone().replace(tzinfo=None)
                    else:
                        tweet_time_local = tweet_time
                    
                    hours_ago = (datetime.now() - tweet_time_local).total_seconds() / 3600
                    is_within_3h = tweet_time_local >= time_cutoff
                    
                    tweet_info = {
                        'index': i + 1,
                        'user_name': user_name,
                        'user_screen_name': user_screen_name,
                        'tweet_id': tweet_id,
                        'created_at': created_at_str,
                        'tweet_time_local': tweet_time_local,
                        'hours_ago': hours_ago,
                        'is_within_3h': is_within_3h,
                        'is_bitcoin': is_bitcoin,
                        'is_target': is_target_tweet
                    }
                    
                    # 如果是Bitcoin推文，记录
                    if is_bitcoin:
                        bitcoin_tweets.append(tweet_info)
                        status = "✅保留" if is_within_3h else "❌过滤"
                        target_flag = " 🎯TARGET" if is_target_tweet else ""
                        logger.info(f"  🟡BITCOIN {status} | {hours_ago:5.1f}h前 | {user_name}{target_flag}")
                        logger.info(f"    推文ID: {tweet_id}")
                        logger.info(f"    原始时间: {created_at_str}")
                        logger.info(f"    本地时间: {tweet_time_local}")
                        logger.info(f"    用户: @{user_screen_name}")
                    
                    # 如果是目标推文
                    if is_target_tweet:
                        target_tweet_found = True
                        target_tweet_info = tweet_info
                        status = "✅保留" if is_within_3h else "❌过滤"
                        logger.info(f"\n🎯 找到目标Bitcoin推文!")
                        logger.info(f"   状态: {status}")
                        logger.info(f"   发布时间: {created_at_str}")
                        logger.info(f"   本地时间: {tweet_time_local}")
                        logger.info(f"   距离现在: {hours_ago:.1f} 小时")
                        logger.info(f"   用户: {user_name} (@{user_screen_name})")
                        logger.info(f"   推文ID: {tweet_id}")
                        
                        if is_within_3h:
                            logger.info(f"   ✅ 该推文在3小时窗口内，应该被正确保留")
                        else:
                            logger.warning(f"   ❌ 该推文超过3小时窗口，会被过滤")
                    
                except Exception as e:
                    logger.warning(f"  解析推文时间失败: {e}")
        
        # Bitcoin推文统计
        logger.info(f"\n🟡 Bitcoin推文分析:")
        logger.info(f"   总计发现: {len(bitcoin_tweets)} 条")
        
        if bitcoin_tweets:
            within_3h = [t for t in bitcoin_tweets if t['is_within_3h']]
            outside_3h = [t for t in bitcoin_tweets if not t['is_within_3h']]
            
            logger.info(f"   3小时内: {len(within_3h)} 条")
            logger.info(f"   超过3小时: {len(outside_3h)} 条")
            
            if within_3h:
                logger.info(f"   ✅ 3小时内的Bitcoin推文:")
                for t in within_3h:
                    target_flag = " 🎯" if t['is_target'] else ""
                    logger.info(f"     - {t['hours_ago']:.1f}h前: {t['user_name']} ({t['tweet_id']}){target_flag}")
            
            if outside_3h:
                logger.info(f"   ❌ 会被过滤的Bitcoin推文:")
                for t in outside_3h[:3]:  # 只显示前3条
                    target_flag = " 🎯" if t['is_target'] else ""
                    logger.info(f"     - {t['hours_ago']:.1f}h前: {t['user_name']} ({t['tweet_id']}){target_flag}")
        
        # 目标推文检查结果
        logger.info(f"\n🎯 目标推文检查结果:")
        if target_tweet_found:
            logger.info(f"   ✅ 成功找到目标Bitcoin推文 {target_tweet_id}")
            if target_tweet_info['is_within_3h']:
                logger.info(f"   ✅ 该推文在3小时窗口内，修复后的UTC转换逻辑正确工作")
            else:
                logger.warning(f"   ⚠️ 该推文超过3小时窗口，这可能是正常的时间过滤")
        else:
            logger.warning(f"   ❌ 未找到目标Bitcoin推文 {target_tweet_id}")
            logger.info(f"   这可能意味着:")
            logger.info(f"     1. 推文不在当前List中")
            logger.info(f"     2. 推文在更深的页面中（当前只查看前100条）")
            logger.info(f"     3. 推文已被删除或不可访问")
        
        # 智能检测测试
        logger.info(f"\n🧠 测试智能检测行为:")
        try:
            all_tweets = twitter_api.fetch_all_tweets(
                list_id=target_list_id,
                max_pages=10,  # 增加页面数以寻找目标推文
                page_size=50,
                hours_limit=hours_limit
            )
            
            logger.info(f"📊 智能检测获取到 {len(all_tweets)} 条推文")
            
            # 在智能检测结果中查找Bitcoin推文
            bitcoin_count_smart = 0
            target_in_smart = False
            
            for tweet in all_tweets:
                user_info = tweet.get('user', {})
                user_name = user_info.get('name', 'Unknown')
                user_screen_name = user_info.get('screen_name', 'Unknown')
                tweet_id = tweet.get('id_str', 'unknown')
                
                is_bitcoin = any(keyword in user_name.lower() for keyword in ['bitcoin']) or \
                            any(keyword in user_screen_name.lower() for keyword in ['bitcoin'])
                
                if is_bitcoin:
                    bitcoin_count_smart += 1
                    
                if tweet_id == target_tweet_id:
                    target_in_smart = True
                    logger.info(f"   🎯 目标推文在智能检测结果中被保留!")
            
            logger.info(f"   🟡 智能检测保留的Bitcoin推文: {bitcoin_count_smart} 条")
            
            if target_in_smart:
                logger.info(f"   ✅ 目标Bitcoin推文被智能检测正确保留")
            else:
                logger.warning(f"   ❌ 目标Bitcoin推文未在智能检测结果中")
        
        except Exception as e:
            logger.error(f"   智能检测测试失败: {e}")
        
        # 测试总结
        logger.info(f"\n" + "=" * 80)
        logger.info(f"🎯 Bitcoin数据拉取测试总结")
        logger.info(f"=" * 80)
        if target_tweet_found and target_tweet_info['is_within_3h']:
            logger.info(f"✅ 测试成功!")
            logger.info(f"1. ✅ 目标Bitcoin推文被正确识别")
            logger.info(f"2. ✅ UTC时间转换逻辑工作正常")
            logger.info(f"3. ✅ 3小时时间窗口过滤准确")
            logger.info(f"4. ✅ Bitcoin数据能够被正确保留")
        elif target_tweet_found and not target_tweet_info['is_within_3h']:
            logger.info(f"⚠️ 部分成功:")
            logger.info(f"1. ✅ 目标Bitcoin推文被正确识别") 
            logger.info(f"2. ✅ UTC时间转换逻辑工作正常")
            logger.info(f"3. ⚠️ 推文超过3小时窗口，被正常过滤")
        else:
            logger.warning(f"❌ 需要进一步检查:")
            logger.warning(f"1. 目标推文可能不在当前List中")
            logger.warning(f"2. 或需要查看更多页面数据")
            
    except Exception as e:
        logger.error(f"❌ 测试失败: {e}")
        import traceback
        logger.error(f"详细错误: {traceback.format_exc()}")

if __name__ == '__main__':
    print("开始测试Bitcoin List数据拉取...")
    test_bitcoin_list_data()
    print("\n测试完成!")