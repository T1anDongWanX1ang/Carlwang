#!/usr/bin/env python3
"""
调试目标推文内容验证问题
"""
import sys
from pathlib import Path
import json

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.api.twitter_api import twitter_api
from src.utils.tweet_enricher import TweetEnricher
from src.utils.logger import get_logger

def debug_content_validation():
    """调试内容验证问题"""
    logger = get_logger(__name__)
    
    logger.info("=" * 80)
    logger.info("🔧 调试目标推文内容验证问题")
    logger.info("=" * 80)
    
    # 目标推文ID
    target_tweet_ids = {
        "Bitcoin": "1998337381150212401",
        "Solana": "1998316328139296827"
    }
    
    # 从配置文件读取list_ids
    with open('config/config.json', 'r') as f:
        config_data = json.load(f)
    
    list_ids = config_data.get('api', {}).get('default_params', {}).get('list_ids', [])
    logger.info(f"📋 测试List IDs: {list_ids}")
    
    # 创建TweetEnricher实例
    try:
        tweet_enricher = TweetEnricher()
        logger.info("✅ TweetEnricher初始化成功")
    except Exception as e:
        logger.error(f"❌ TweetEnricher初始化失败: {e}")
        return
    
    # 搜索目标推文
    found_tweets = {}
    
    for list_id in list_ids:
        logger.info(f"\n📋 搜索List: {list_id}")
        
        try:
            # 获取推文数据
            tweets, _ = twitter_api.fetch_tweets(list_id=list_id, count=200)
            
            if not tweets:
                logger.warning(f"⚠️ List {list_id} 没有数据")
                continue
            
            logger.info(f"📊 获取到 {len(tweets)} 条推文")
            
            # 搜索目标推文
            for tweet in tweets:
                tweet_id = tweet.get('id_str', '')
                
                for project_name, target_id in target_tweet_ids.items():
                    if tweet_id == target_id:
                        found_tweets[project_name] = tweet
                        logger.info(f"🎯 找到目标推文: {project_name} - {target_id}")
                        
                        # 提取推文内容
                        full_text = tweet.get('full_text', '')
                        user_info = tweet.get('user', {})
                        user_name = user_info.get('name', 'Unknown')
                        user_screen_name = user_info.get('screen_name', 'Unknown')
                        
                        logger.info(f"📝 推文内容:")
                        logger.info(f"   用户: {user_name} (@{user_screen_name})")
                        logger.info(f"   内容: {full_text}")
                        logger.info(f"   长度: {len(full_text)} 字符")
                        
                        # 测试内容验证
                        logger.info(f"\n🧪 内容验证测试:")
                        
                        # 测试基于关键词的验证
                        try:
                            keyword_result = tweet_enricher._keyword_validate_content(full_text.lower())
                            logger.info(f"   📝 关键词验证结果: {keyword_result}")
                        except Exception as e:
                            logger.error(f"   ❌ 关键词验证失败: {e}")
                        
                        # 测试AI验证
                        try:
                            ai_result = tweet_enricher._ai_validate_content(full_text)
                            logger.info(f"   🤖 AI验证结果: {ai_result}")
                        except Exception as e:
                            logger.error(f"   ❌ AI验证失败: {e}")
                        
                        # 测试总体验证
                        try:
                            overall_result = tweet_enricher._validate_crypto_content(full_text, use_ai=True)
                            logger.info(f"   ✅ 总体验证结果: {overall_result}")
                        except Exception as e:
                            logger.error(f"   ❌ 总体验证失败: {e}")
                        
                        # 分析为什么被判定为无效
                        logger.info(f"\n🔍 分析:")
                        if len(full_text.strip()) < 10:
                            logger.warning(f"   ⚠️ 推文长度过短: {len(full_text)} < 10")
                        
                        # 检查是否包含加密货币关键词
                        crypto_keywords = [
                            'bitcoin', 'btc', 'ethereum', 'eth', 'crypto', 'cryptocurrency',
                            'blockchain', 'defi', 'nft', 'dao', 'web3', 'altcoin',
                            'doge', 'ada', 'sol', 'matic', 'avax', 'dot', 'link', 'usdt', 'usdc',
                            'binance', 'coinbase', 'trading', 'market', 'price', 'bull', 'bear',
                            'hodl', 'satoshi', 'mining', 'wallet', 'exchange', 'token'
                        ]
                        
                        text_lower = full_text.lower()
                        found_keywords = [kw for kw in crypto_keywords if kw in text_lower]
                        if found_keywords:
                            logger.info(f"   ✅ 找到加密货币关键词: {found_keywords}")
                        else:
                            logger.warning(f"   ⚠️ 未找到明显的加密货币关键词")
                        
                        logger.info("   " + "-" * 60)
                        
        except Exception as e:
            logger.error(f"❌ 搜索List {list_id} 失败: {e}")
    
    # 总结
    logger.info(f"\n" + "=" * 80)
    logger.info(f"📊 调试总结")
    logger.info(f"=" * 80)
    
    logger.info(f"🎯 目标推文: {len(target_tweet_ids)} 个")
    logger.info(f"🔍 找到推文: {len(found_tweets)} 个")
    
    if len(found_tweets) == len(target_tweet_ids):
        logger.info(f"✅ 所有目标推文都被找到")
        logger.info(f"💡 问题应该出在内容验证阶段")
        logger.info(f"🔧 建议检查AI验证的prompt或调整验证逻辑")
    elif len(found_tweets) > 0:
        logger.info(f"⚠️ 部分推文找到: {list(found_tweets.keys())}")
        missing = set(target_tweet_ids.keys()) - set(found_tweets.keys())
        logger.warning(f"❌ 未找到: {list(missing)}")
    else:
        logger.error(f"❌ 未找到任何目标推文")
        logger.error(f"   可能原因：推文不在指定的List中或已被删除")

if __name__ == '__main__':
    print("开始调试内容验证问题...")
    debug_content_validation()
    print("\n调试完成!")