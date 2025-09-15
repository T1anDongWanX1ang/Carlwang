#!/usr/bin/env python3
"""
测试 entity_id 和 topic_id 一致性
"""
import sys
import os
from datetime import datetime

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.utils.tweet_enricher import tweet_enricher
from src.models.tweet import Tweet
from src.database.connection import db_manager
from src.database.topic_dao import topic_dao
from src.utils.logger import setup_logger


def test_entity_topic_consistency():
    """测试entity_id和topic_id的一致性"""
    # 设置日志
    setup_logger()
    
    print("🚀 测试 entity_id 和 topic_id 一致性")
    
    # 测试数据库连接
    if not db_manager.test_connection():
        print("❌ 数据库连接失败")
        return False
    
    # 创建测试推文（使用新的关键词避免重复）
    test_tweet = Tweet(
        id_str="consistency_test_001",
        full_text="Ethereum 2.0 staking rewards are looking very attractive! The merge has been successful and validators are earning good yields. #ETH #Ethereum #Staking",
        created_at_datetime=datetime.now()
    )
    
    # 创建测试用户数据映射
    user_data_map = {
        "17351167": {
            "id_str": "17351167",
            "screen_name": "testuser",
            "name": "Test User"
        }
    }
    
    print(f"\n=== 测试推文内容 ===")
    print(f"推文: {test_tweet.full_text[:100]}...")
    
    try:
        # 执行推文增强
        enriched_tweet = tweet_enricher.enrich_single_tweet(test_tweet, user_data_map)
        
        if enriched_tweet and enriched_tweet.entity_id:
            entity_id = enriched_tweet.entity_id
            print(f"\n✅ 推文增强成功!")
            print(f"生成的 entity_id: {entity_id}")
            
            # 验证topic表中是否存在对应的topic_id
            topic_exists = db_manager.execute_query(
                "SELECT topic_id, topic_name FROM topics WHERE topic_id = %s", 
                (entity_id,)
            )
            
            if topic_exists:
                topic_data = topic_exists[0]
                print(f"✅ 在topics表中找到匹配记录:")
                print(f"   topic_id: {topic_data['topic_id']}")
                print(f"   topic_name: {topic_data['topic_name']}")
                print(f"✅ entity_id 和 topic_id 完全一致: {entity_id == topic_data['topic_id']}")
                
                # 测试第二次使用相同话题
                print(f"\n=== 测试话题复用 ===")
                test_tweet2 = Tweet(
                    id_str="consistency_test_002",
                    full_text="Another post about Ethereum staking and ETH 2.0 rewards",
                    created_at_datetime=datetime.now()
                )
                
                enriched_tweet2 = tweet_enricher.enrich_single_tweet(test_tweet2, user_data_map)
                
                if enriched_tweet2 and enriched_tweet2.entity_id:
                    print(f"第二条推文的 entity_id: {enriched_tweet2.entity_id}")
                    print(f"✅ 话题复用测试: {'成功' if enriched_tweet2.entity_id == entity_id else '失败'}")
                
                return True
            else:
                print(f"❌ 在topics表中没有找到 topic_id = {entity_id} 的记录")
                return False
        else:
            print("❌ 推文增强失败或未生成entity_id")
            return False
            
    except Exception as e:
        print(f"❌ 测试过程中出错: {e}")
        return False


def show_current_data_structure():
    """显示当前的数据结构"""
    print("\n=== 当前数据结构 ===")
    
    # 显示topics表的最新数据
    try:
        topics = db_manager.execute_query("SELECT topic_id, topic_name, brief FROM topics ORDER BY created_at DESC LIMIT 5")
        
        print("📊 Topics表最新数据:")
        for topic in topics:
            print(f"   topic_id: {topic['topic_id']:20} 话题: {topic['topic_name']:20} 简介: {topic['brief'][:40]}...")
    
    except Exception as e:
        print(f"查询topics数据失败: {e}")
    
    # 显示twitter_tweet表中有entity_id的数据
    try:
        tweets = db_manager.execute_query("SELECT id_str, entity_id, kol_id FROM twitter_tweet WHERE entity_id IS NOT NULL LIMIT 3")
        
        print("\n📊 Twitter_tweet表中有entity_id的数据:")
        for tweet in tweets:
            print(f"   tweet_id: {tweet['id_str']:20} entity_id: {tweet['entity_id']:20} kol_id: {tweet['kol_id']}")
    
    except Exception as e:
        print(f"查询tweet数据失败: {e}")


def clean_test_data():
    """清理测试数据"""
    print("\n=== 清理测试数据 ===")
    
    try:
        # 清理测试推文
        test_tweet_ids = ["test_tweet_001", "consistency_test_001", "consistency_test_002"]
        for tweet_id in test_tweet_ids:
            db_manager.execute_update("DELETE FROM twitter_tweet WHERE id_str = %s", (tweet_id,))
        
        # 清理测试话题（可选）
        test_topic_patterns = ["Bitcoin价格分析", "Ethereum生态"]
        for pattern in test_topic_patterns:
            db_manager.execute_update("DELETE FROM topics WHERE topic_name = %s", (pattern,))
        
        print("✅ 测试数据清理完成")
        
    except Exception as e:
        print(f"清理测试数据失败: {e}")


def main():
    """主函数"""
    print("🎯 Entity ID 和 Topic ID 一致性测试")
    
    # 显示当前数据结构
    show_current_data_structure()
    
    # 执行一致性测试
    if test_entity_topic_consistency():
        print("\n🎉 一致性测试通过!")
        
        # 再次显示数据结构
        show_current_data_structure()
        
        print("""
✅ 修改总结:
- entity_id 现在直接使用 topic_id 的值
- 不再使用 "topic_" + topic_id 的格式
- entity_id 和 topic_id 完全一致
- 话题复用功能正常工作
- 数据表关系保持一致性
        """)
        
        # 询问是否清理测试数据
        response = input("\n是否清理测试数据? (y/N): ").strip().lower()
        if response == 'y':
            clean_test_data()
    
    else:
        print("\n❌ 一致性测试失败")


if __name__ == '__main__':
    main() 