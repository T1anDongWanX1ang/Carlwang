#!/usr/bin/env python3
"""
最终验证测试 - 验证project_id和topic_id正确存储
"""
import sys
import os

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.models.tweet import Tweet
from src.utils.tweet_enricher import tweet_enricher
from src.database.tweet_dao import tweet_dao
from src.utils.logger import setup_logger
from datetime import datetime


def test_project_tweet():
    """测试项目类型推文"""
    print("🔍 测试项目类型推文处理...")
    
    # 创建一个包含具体项目的测试推文
    test_tweet = Tweet(
        id_str="test_project_" + str(int(datetime.now().timestamp())),
        full_text="Bitcoin is showing strong bullish signals! BTC price could reach new all-time highs soon. The recent institutional adoption is driving the momentum. #Bitcoin #BTC #Crypto",
        created_at="Wed Jan 10 12:00:00 +0000 2024",
        created_at_datetime=datetime.now(),
        bookmark_count=5,
        favorite_count=15,
        quote_count=3,
        reply_count=8,
        retweet_count=12,
        view_count=150
    )
    
    # 使用enricher处理推文
    enriched_tweet = tweet_enricher.enrich_single_tweet(test_tweet)
    
    if not enriched_tweet:
        print("❌ 推文enrichment失败")
        return False
        
    print(f"📊 Enriched Tweet结果:")
    print(f"   project_id: {enriched_tweet.project_id}")
    print(f"   topic_id: {enriched_tweet.topic_id}")
    print(f"   entity_id: {enriched_tweet.entity_id}")
    print(f"   is_valid: {enriched_tweet.is_valid}")
    
    # 尝试插入到数据库
    success = tweet_dao.insert_tweet(enriched_tweet)
    if not success:
        print("❌ 推文插入数据库失败")
        return False
        
    # 从数据库查询验证
    saved_tweet = tweet_dao.get_tweet_by_id(enriched_tweet.id_str)
    if not saved_tweet:
        print("❌ 从数据库查询推文失败")
        return False
    
    print(f"💾 数据库存储结果:")
    print(f"   project_id: {saved_tweet.project_id}")
    print(f"   topic_id: {saved_tweet.topic_id}")
    print(f"   entity_id: {saved_tweet.entity_id}")
    
    # 验证project_id是否正确存储
    if enriched_tweet.project_id and saved_tweet.project_id == enriched_tweet.project_id:
        print("✅ 项目ID正确存储到project_id字段！")
        return True
    else:
        print("❌ 项目ID存储验证失败")
        return False


def test_topic_tweet():
    """测试话题类型推文"""
    print("\n🔍 测试话题类型推文处理...")
    
    # 创建一个包含一般话题讨论的测试推文
    test_tweet = Tweet(
        id_str="test_topic_" + str(int(datetime.now().timestamp())),
        full_text="DeFi is revolutionizing traditional finance. The yield farming opportunities are incredible, but always remember to do your own research and understand the risks involved.",
        created_at="Wed Jan 10 12:30:00 +0000 2024",
        created_at_datetime=datetime.now(),
        bookmark_count=8,
        favorite_count=25,
        quote_count=5,
        reply_count=12,
        retweet_count=18,
        view_count=220
    )
    
    # 使用enricher处理推文
    enriched_tweet = tweet_enricher.enrich_single_tweet(test_tweet)
    
    if not enriched_tweet:
        print("❌ 推文enrichment失败")
        return False
        
    print(f"📊 Enriched Tweet结果:")
    print(f"   project_id: {enriched_tweet.project_id}")
    print(f"   topic_id: {enriched_tweet.topic_id}")
    print(f"   entity_id: {enriched_tweet.entity_id}")
    print(f"   is_valid: {enriched_tweet.is_valid}")
    
    # 尝试插入到数据库
    success = tweet_dao.insert_tweet(enriched_tweet)
    if not success:
        print("❌ 推文插入数据库失败")
        return False
        
    # 从数据库查询验证
    saved_tweet = tweet_dao.get_tweet_by_id(enriched_tweet.id_str)
    if not saved_tweet:
        print("❌ 从数据库查询推文失败")
        return False
    
    print(f"💾 数据库存储结果:")
    print(f"   project_id: {saved_tweet.project_id}")
    print(f"   topic_id: {saved_tweet.topic_id}")
    print(f"   entity_id: {saved_tweet.entity_id}")
    
    # 验证topic_id是否正确存储
    if enriched_tweet.topic_id and saved_tweet.topic_id == enriched_tweet.topic_id:
        print("✅ 话题ID正确存储到topic_id字段！")
        return True
    else:
        print("❌ 话题ID存储验证失败")
        return False


def test_database_fields():
    """测试数据库字段是否正确存在"""
    print("\n🔍 验证数据库字段结构...")
    
    try:
        # 查询包含所有新字段的数据
        sql = f"""
        SELECT id_str, project_id, topic_id, entity_id, is_valid, sentiment, tweet_url
        FROM {tweet_dao.table_name} 
        WHERE project_id IS NOT NULL OR topic_id IS NOT NULL
        LIMIT 5
        """
        
        results = tweet_dao.db_manager.execute_query(sql)
        
        if results:
            print("✅ 数据库字段验证成功！")
            print(f"📊 找到 {len(results)} 条包含project_id或topic_id的记录:")
            
            for i, row in enumerate(results, 1):
                print(f"   {i}. id_str: {row.get('id_str')}")
                print(f"      project_id: {row.get('project_id')}")
                print(f"      topic_id: {row.get('topic_id')}")
                print(f"      entity_id: {row.get('entity_id')}")
                print(f"      is_valid: {row.get('is_valid')}")
                print()
            return True
        else:
            print("⚠️ 没有找到包含project_id或topic_id的记录")
            return True
            
    except Exception as e:
        print(f"❌ 数据库字段验证失败: {e}")
        return False


def main():
    """主测试函数"""
    setup_logger()
    
    print("🎯 最终验证测试：project_id和topic_id字段存储")
    print("=" * 80)
    
    try:
        # 1. 测试数据库字段结构
        field_test_success = test_database_fields()
        
        # 2. 测试项目类型推文
        project_test_success = test_project_tweet()
        
        # 3. 测试话题类型推文
        topic_test_success = test_topic_tweet()
        
        # 输出最终结果
        print("\n" + "=" * 80)
        print("🎊 最终测试结果:")
        print(f"   数据库字段验证: {'✅ 通过' if field_test_success else '❌ 失败'}")
        print(f"   项目类型推文测试: {'✅ 通过' if project_test_success else '❌ 失败'}")
        print(f"   话题类型推文测试: {'✅ 通过' if topic_test_success else '❌ 失败'}")
        
        all_success = field_test_success and project_test_success and topic_test_success
        
        if all_success:
            print("\n🎉 所有测试通过！")
            print("✅ project_id和topic_id字段已正确存储到数据库对应字段中")
            print("✅ 智能分类功能正常工作")
            print("✅ 数据库访问层正确处理新字段")
            return True
        else:
            print("\n⚠️ 部分测试失败，请检查具体问题")
            return False
            
    except Exception as e:
        print(f"\n❌ 测试过程出错: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)