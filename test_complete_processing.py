#!/usr/bin/env python3
"""
测试修复后的完整推文处理流程
"""
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.api.twitter_api import twitter_api
from src.utils.tweet_enricher import TweetEnricher
from src.utils.logger import get_logger

def test_complete_tweet_processing():
    """测试完整的推文处理流程"""
    logger = get_logger(__name__)
    
    logger.info("=" * 80)
    logger.info("🔧 测试修复后的完整推文处理流程")
    logger.info("=" * 80)
    
    # 目标推文ID
    target_tweet_ids = ["1998337381150212401", "1998316328139296827"]
    
    # 创建TweetEnricher实例
    try:
        tweet_enricher = TweetEnricher()
        logger.info("✅ TweetEnricher初始化成功")
    except Exception as e:
        logger.error(f"❌ TweetEnricher初始化失败: {e}")
        return
    
    # 使用fetch_all_tweets获取数据（这会模拟完整的服务流程）
    logger.info("📊 使用完整流程获取推文数据...")
    
    try:
        all_tweets = twitter_api.fetch_all_tweets(
            max_pages=5,  # 减少页面数节约时间
            page_size=100,
            hours_limit=3
        )
        
        logger.info(f"📊 总共获取到 {len(all_tweets)} 条推文")
        
        # 检查目标推文是否在结果中
        found_targets = {}
        
        for tweet in all_tweets:
            tweet_id = tweet.get('id_str', '')
            
            if tweet_id in target_tweet_ids:
                user_info = tweet.get('user', {})
                user_name = user_info.get('name', 'Unknown')
                created_at = tweet.get('created_at', '')
                full_text = tweet.get('full_text', '')
                
                found_targets[tweet_id] = {
                    'user_name': user_name,
                    'created_at': created_at,
                    'full_text': full_text
                }
                
                logger.info(f"🎯 找到目标推文: {tweet_id}")
                logger.info(f"   用户: {user_name}")
                logger.info(f"   时间: {created_at}")
                logger.info(f"   内容: {full_text}")
        
        # 如果没有找到，尝试处理收到的推文来测试处理逻辑
        if not found_targets:
            logger.warning("❌ 在智能检测结果中没有找到目标推文")
            logger.warning("🔧 可能原因：UTC时间转换后，推文超出了3小时限制")
            
            # 手动测试推文处理逻辑
            logger.info("\n🧪 手动测试推文处理逻辑...")
            
            # 获取最新数据测试处理
            tweets, _ = twitter_api.fetch_tweets(list_id="1996863048959820198", count=100)
            
            if tweets:
                # 找到Bitcoin或Solana相关推文进行测试
                for tweet in tweets[:10]:  # 只测试前10条
                    user_info = tweet.get('user', {})
                    user_name = user_info.get('name', 'Unknown')
                    tweet_id = tweet.get('id_str', '')
                    
                    # 如果是目标用户或目标推文
                    if any(keyword in user_name.lower() for keyword in ['bitcoin', 'solana']) or tweet_id in target_tweet_ids:
                        logger.info(f"\n🧪 测试推文处理: {tweet_id} - {user_name}")
                        
                        # 手动处理这条推文
                        try:
                            # 创建用户数据映射
                            user_data_map = {tweet_id: user_info}
                            
                            # 处理推文
                            enriched_tweet = tweet_enricher.enrich_single_tweet(tweet, user_data_map)
                            
                            if enriched_tweet:
                                logger.info(f"✅ 推文处理成功:")
                                logger.info(f"   is_valid: {getattr(enriched_tweet, 'is_valid', '未设置')}")
                                logger.info(f"   is_real_project_tweet: {getattr(enriched_tweet, 'is_real_project_tweet', '未设置')}")
                                logger.info(f"   kol_id: {getattr(enriched_tweet, 'kol_id', '未设置')}")
                                logger.info(f"   sentiment: {getattr(enriched_tweet, 'sentiment', '未设置')}")
                                logger.info(f"   project_id: {getattr(enriched_tweet, 'project_id', '未设置')}")
                            else:
                                logger.error(f"❌ 推文处理失败")
                                
                        except Exception as e:
                            logger.error(f"❌ 推文处理异常: {e}")
                        
                        break
        else:
            logger.info(f"\n✅ 在智能检测结果中找到 {len(found_targets)} 个目标推文")
            for tweet_id, tweet_data in found_targets.items():
                logger.info(f"✅ {tweet_id}: {tweet_data['user_name']} - {tweet_data['created_at']}")
    
    except Exception as e:
        logger.error(f"❌ 完整流程测试失败: {e}")

if __name__ == '__main__':
    print("开始测试完整推文处理流程...")
    test_complete_tweet_processing()
    print("\n测试完成!")