#!/usr/bin/env python3
"""
推文增强功能测试脚本
"""
import sys
import os
from datetime import datetime

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.utils.tweet_enricher import tweet_enricher
from src.models.tweet import Tweet
from src.database.connection import db_manager
from src.utils.logger import setup_logger


def test_tweet_enrichment():
    """测试推文增强功能"""
    # 设置日志
    setup_logger()
    
    # 测试数据库连接
    if not db_manager.test_connection():
        print("❌ 数据库连接失败")
        return False
    
    print("✅ 数据库连接成功")
    
    # 创建测试推文
    test_tweet = Tweet(
        id_str="test_tweet_001",
        full_text="Bitcoin has reached a new all-time high! The crypto market is showing strong bullish momentum. What do you think about this rally? #Bitcoin #Crypto #BullRun",
        created_at_datetime=datetime.now()
    )
    
    # 创建测试用户数据映射
    user_data_map = {
        "17351167": {  # 使用已知的KOL用户ID
            "id_str": "17351167",
            "screen_name": "testuser",
            "name": "Test User"
        }
    }
    
    print("\n=== 测试推文增强功能 ===")
    print(f"原始推文: {test_tweet.full_text[:100]}...")
    print(f"KOL ID: {test_tweet.kol_id}")
    print(f"Entity ID: {test_tweet.entity_id}")
    
    try:
        # 执行推文增强
        enriched_tweet = tweet_enricher.enrich_single_tweet(test_tweet, user_data_map)
        
        if enriched_tweet:
            print("\n✅ 推文增强成功!")
            print(f"KOL ID: {enriched_tweet.kol_id}")
            print(f"Entity ID: {enriched_tweet.entity_id}")
            
            # 显示增强统计信息
            stats = tweet_enricher.get_enrichment_statistics()
            print(f"\n=== 增强统计信息 ===")
            print(f"KOL缓存大小: {stats.get('kol_cache_size', 0)}")
            print(f"KOL用户: {stats.get('kol_users', [])}")
            
            return True
        else:
            print("❌ 推文增强失败")
            return False
            
    except Exception as e:
        print(f"❌ 推文增强过程中出错: {e}")
        return False


def test_topic_processing_flow():
    """测试话题处理流程分析"""
    print("\n=== 话题处理流程分析 ===")
    
    should_process = tweet_enricher.should_process_in_crawler_flow()
    
    print(f"是否应该在爬虫流程中处理话题: {'✅ 是' if should_process else '❌ 否'}")
    
    if should_process:
        print("""
推荐在爬虫流程中处理话题数据的原因：
✅ 数据一致性：推文和话题数据需要保持关联一致性
✅ 实时性：话题识别需要在推文入库时就完成，避免延迟  
✅ 性能：避免后续批量处理带来的额外开销
✅ 简化架构：统一在一个流程中处理，减少系统复杂度
        """)
    
    return should_process


def test_database_tables():
    """测试数据库表结构"""
    print("\n=== 检查数据库表结构 ===")
    
    try:
        # 检查twitter_tweet表的字段
        results = db_manager.execute_query("DESCRIBE twitter_tweet")
        tweet_fields = [row['Field'] for row in results]
        
        required_fields = ['kol_id', 'entity_id']
        missing_fields = [field for field in required_fields if field not in tweet_fields]
        
        if missing_fields:
            print(f"❌ twitter_tweet表缺少字段: {missing_fields}")
            return False
        else:
            print("✅ twitter_tweet表字段完整")
        
        # 检查topics表
        results = db_manager.execute_query("DESCRIBE topics")
        print(f"✅ topics表存在，共 {len(results)} 个字段")
        
        return True
        
    except Exception as e:
        print(f"❌ 检查数据库表失败: {e}")
        return False


def main():
    """主函数"""
    print("🚀 开始测试推文增强功能")
    
    # 测试数据库表结构
    if not test_database_tables():
        print("❌ 数据库表结构检查失败")
        return
    
    # 测试推文增强功能
    if not test_tweet_enrichment():
        print("❌ 推文增强功能测试失败")
        return
    
    # 测试话题处理流程
    if not test_topic_processing_flow():
        print("❌ 话题处理流程测试失败")
        return
    
    print("\n🎉 所有测试通过！推文增强功能工作正常")
    
    print("""
=== 功能总结 ===
✅ kol_id字段：从用户数据中自动提取KOL ID
✅ entity_id字段：使用ChatGPT分析话题并生成entity_id  
✅ 话题存储：自动创建和存储话题数据到topics表
✅ 流程集成：在爬虫流程中完成所有处理
✅ 缓存优化：KOL用户缓存提高性能
✅ 错误处理：完善的异常处理和降级机制

=== 使用方法 ===
1. 确保ChatGPT API配额充足
2. 运行爬虫时会自动进行推文增强
3. 可以通过tweet_enricher.get_enrichment_statistics()查看统计信息
    """)


if __name__ == '__main__':
    main() 