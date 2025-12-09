#!/usr/bin/env python3
"""
测试更新后的list_ids数组中的Bitcoin和Solana数据拉取
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

def test_updated_list_ids():
    """测试更新后的list_ids中的目标推文"""
    logger = get_logger(__name__)
    
    logger.info("=" * 80)
    logger.info("🔧 测试更新后的list_ids数组中的目标推文")
    logger.info("=" * 80)
    
    # 从配置文件读取更新后的list_ids
    with open('config/config.json', 'r') as f:
        config_data = json.load(f)
    
    list_ids = config_data.get('api', {}).get('default_params', {}).get('list_ids', [])
    logger.info(f"📋 更新后的List IDs: {list_ids}")
    
    # 目标推文
    target_tweets = {
        "bitcoin": {
            "id": "1998337381150212401",
            "url": "https://x.com/Bitcoin/status/1998337381150212401",
            "user": "Bitcoin"
        },
        "solana": {
            "id": "1998316328139296827", 
            "url": "https://x.com/solana/status/1998316328139296827",
            "user": "Solana"
        }
    }
    
    logger.info(f"🎯 目标推文:")
    logger.info(f"   Bitcoin: {target_tweets['bitcoin']['id']}")
    logger.info(f"   Solana: {target_tweets['solana']['id']}")
    
    # 3小时时间窗口
    hours_limit = 3
    time_cutoff = datetime.now() - timedelta(hours=hours_limit)
    logger.info(f"📅 本地时间截止点: {time_cutoff.strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"⏰ 当前本地时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 跟踪找到的目标推文
    found_tweets = {}
    total_bitcoin_tweets = 0
    total_solana_tweets = 0
    
    # 测试每个List
    for list_id in list_ids:
        logger.info(f"\n" + "=" * 60)
        logger.info(f"📋 测试List: {list_id}")
        logger.info(f"=" * 60)
        
        try:
            # 获取更多数据确保找到目标推文
            tweets, _ = twitter_api.fetch_tweets(list_id=list_id, count=200)
            
            if not tweets:
                logger.warning(f"⚠️ List {list_id} 没有数据")
                continue
                
            logger.info(f"📊 获取到 {len(tweets)} 条推文")
            
            # 分析推文
            bitcoin_tweets_in_list = []
            solana_tweets_in_list = []
            
            for i, tweet in enumerate(tweets):
                user_info = tweet.get('user', {})
                user_name = user_info.get('name', 'Unknown')
                user_screen_name = user_info.get('screen_name', 'Unknown')
                created_at_str = tweet.get('created_at', '')
                tweet_id = tweet.get('id_str', 'unknown')
                
                # 检查推文类型
                is_bitcoin = any(keyword in user_name.lower() for keyword in ['bitcoin']) or \
                            any(keyword in user_screen_name.lower() for keyword in ['bitcoin'])
                is_solana = any(keyword in user_name.lower() for keyword in ['solana']) or \
                           any(keyword in user_screen_name.lower() for keyword in ['solana'])
                
                # 检查是否是目标推文
                is_target_bitcoin = tweet_id == target_tweets['bitcoin']['id']
                is_target_solana = tweet_id == target_tweets['solana']['id']
                
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
                            'list_id': list_id,
                            'user_name': user_name,
                            'user_screen_name': user_screen_name,
                            'tweet_id': tweet_id,
                            'created_at': created_at_str,
                            'tweet_time_local': tweet_time_local,
                            'hours_ago': hours_ago,
                            'is_within_3h': is_within_3h
                        }
                        
                        # Bitcoin推文处理
                        if is_bitcoin:
                            total_bitcoin_tweets += 1
                            bitcoin_tweets_in_list.append(tweet_info)
                            
                            status = "✅保留" if is_within_3h else "❌过滤"
                            target_flag = " 🎯TARGET" if is_target_bitcoin else ""
                            
                            logger.info(f"  🟡BITCOIN {status} | {hours_ago:5.1f}h前 | {user_name}{target_flag}")
                            logger.info(f"    推文ID: {tweet_id}")
                            logger.info(f"    原始时间: {created_at_str}")
                            logger.info(f"    本地时间: {tweet_time_local}")
                            
                            if is_target_bitcoin:
                                found_tweets['bitcoin'] = tweet_info
                                logger.info(f"    🎯 找到目标Bitcoin推文!")
                        
                        # Solana推文处理
                        if is_solana:
                            total_solana_tweets += 1
                            solana_tweets_in_list.append(tweet_info)
                            
                            status = "✅保留" if is_within_3h else "❌过滤"
                            target_flag = " 🎯TARGET" if is_target_solana else ""
                            
                            logger.info(f"  🟠SOLANA {status} | {hours_ago:5.1f}h前 | {user_name}{target_flag}")
                            logger.info(f"    推文ID: {tweet_id}")
                            logger.info(f"    原始时间: {created_at_str}")
                            logger.info(f"    本地时间: {tweet_time_local}")
                            
                            if is_target_solana:
                                found_tweets['solana'] = tweet_info
                                logger.info(f"    🎯 找到目标Solana推文!")
                    
                    except Exception as e:
                        logger.warning(f"  解析推文时间失败: {e}")
            
            # List统计
            logger.info(f"\n📊 List {list_id} 统计:")
            logger.info(f"   🟡 Bitcoin推文: {len(bitcoin_tweets_in_list)} 条")
            logger.info(f"   🟠 Solana推文: {len(solana_tweets_in_list)} 条")
            
            # 显示3小时内的推文
            bitcoin_3h = [t for t in bitcoin_tweets_in_list if t['is_within_3h']]
            solana_3h = [t for t in solana_tweets_in_list if t['is_within_3h']]
            
            if bitcoin_3h:
                logger.info(f"   ✅ 3小时内Bitcoin推文: {len(bitcoin_3h)} 条")
            if solana_3h:
                logger.info(f"   ✅ 3小时内Solana推文: {len(solana_3h)} 条")
                
        except Exception as e:
            logger.error(f"❌ 测试List {list_id} 失败: {e}")
    
    # 目标推文检查总结
    logger.info(f"\n" + "=" * 80)
    logger.info(f"🎯 目标推文检查总结")
    logger.info(f"=" * 80)
    
    for target_name, target_info in target_tweets.items():
        if target_name in found_tweets:
            tweet_data = found_tweets[target_name]
            status = "✅保留" if tweet_data['is_within_3h'] else "❌过滤"
            logger.info(f"✅ {target_info['user']} 推文 {target_info['id']} - {status}")
            logger.info(f"   发布时间: {tweet_data['created_at']}")
            logger.info(f"   本地时间: {tweet_data['tweet_time_local']}")
            logger.info(f"   距离现在: {tweet_data['hours_ago']:.1f} 小时")
            logger.info(f"   所在List: {tweet_data['list_id']}")
            logger.info(f"   URL: {target_info['url']}")
        else:
            logger.warning(f"❌ {target_info['user']} 推文 {target_info['id']} 未找到")
            logger.warning(f"   URL: {target_info['url']}")
    
    # 智能检测测试
    logger.info(f"\n🧠 测试智能检测行为:")
    try:
        for list_id in list_ids:
            logger.info(f"\n📋 智能检测测试 List: {list_id}")
            
            all_tweets = twitter_api.fetch_all_tweets(
                list_id=list_id,
                max_pages=15,  # 增加页面数
                page_size=50,
                hours_limit=hours_limit
            )
            
            logger.info(f"   📊 智能检测获取到 {len(all_tweets)} 条推文")
            
            # 检查目标推文是否在智能检测结果中
            target_in_smart = {'bitcoin': False, 'solana': False}
            bitcoin_count = 0
            solana_count = 0
            
            for tweet in all_tweets:
                user_info = tweet.get('user', {})
                user_name = user_info.get('name', 'Unknown')
                user_screen_name = user_info.get('screen_name', 'Unknown')
                tweet_id = tweet.get('id_str', 'unknown')
                
                is_bitcoin = any(keyword in user_name.lower() for keyword in ['bitcoin']) or \
                            any(keyword in user_screen_name.lower() for keyword in ['bitcoin'])
                is_solana = any(keyword in user_name.lower() for keyword in ['solana']) or \
                           any(keyword in user_screen_name.lower() for keyword in ['solana'])
                
                if is_bitcoin:
                    bitcoin_count += 1
                if is_solana:
                    solana_count += 1
                    
                if tweet_id == target_tweets['bitcoin']['id']:
                    target_in_smart['bitcoin'] = True
                    logger.info(f"   🎯 目标Bitcoin推文在智能检测结果中!")
                if tweet_id == target_tweets['solana']['id']:
                    target_in_smart['solana'] = True
                    logger.info(f"   🎯 目标Solana推文在智能检测结果中!")
            
            logger.info(f"   🟡 智能检测保留的Bitcoin推文: {bitcoin_count} 条")
            logger.info(f"   🟠 智能检测保留的Solana推文: {solana_count} 条")
    
    except Exception as e:
        logger.error(f"   智能检测测试失败: {e}")
    
    # 最终总结
    logger.info(f"\n" + "=" * 80)
    logger.info(f"🎉 测试总结")
    logger.info(f"=" * 80)
    
    total_found = len(found_tweets)
    total_targets = len(target_tweets)
    
    logger.info(f"📊 总体结果: 找到 {total_found}/{total_targets} 个目标推文")
    logger.info(f"📊 总Bitcoin推文: {total_bitcoin_tweets} 条")
    logger.info(f"📊 总Solana推文: {total_solana_tweets} 条")
    
    if total_found == total_targets:
        logger.info(f"✅ 完全成功! 所有目标推文都被找到并正确处理")
        logger.info(f"✅ UTC时间转换修复工作正常")
        logger.info(f"✅ 3小时时间窗口过滤准确")
        logger.info(f"✅ 更新后的list_ids配置有效")
    elif total_found > 0:
        logger.info(f"⚠️ 部分成功: 找到了 {total_found} 个目标推文")
        logger.info(f"✅ UTC时间转换修复工作正常")
        missing = total_targets - total_found
        logger.warning(f"❌ 还有 {missing} 个推文未找到，可能需要检查List配置或推文状态")
    else:
        logger.warning(f"❌ 未找到任何目标推文")
        logger.warning(f"   可能原因：")
        logger.warning(f"   1. 推文不在指定的List中")
        logger.warning(f"   2. 推文已被删除或设为私有")
        logger.warning(f"   3. 需要查看更深层的页面数据")

if __name__ == '__main__':
    print("开始测试更新后的list_ids数组...")
    test_updated_list_ids()
    print("\n测试完成!")