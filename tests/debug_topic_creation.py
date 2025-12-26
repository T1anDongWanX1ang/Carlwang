#!/usr/bin/env python3
"""
调试topic创建问题
"""
import sys
import os

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.models.topic import Topic
from src.database.topic_dao import topic_dao
from src.utils.smart_classifier import smart_classifier
from src.utils.logger import setup_logger
from datetime import datetime


def debug_topic_generation():
    """调试topic ID生成"""
    setup_logger()
    
    print("🔍 调试topic ID生成...")
    print("=" * 60)
    
    # 1. 直接测试Topic.generate_topic_id()
    print("1. 测试Topic.generate_topic_id():")
    for i in range(3):
        topic_id = Topic.generate_topic_id()
        print(f"   生成的topic_id {i+1}: {topic_id}")
    
    # 2. 测试Topic对象创建
    print("\n2. 测试Topic对象创建:")
    topic = Topic(
        topic_id=Topic.generate_topic_id(),
        topic_name="Test Topic",
        brief="This is a test topic",
        created_at=datetime.now(),
        popularity=5,
        update_time=datetime.now()
    )
    
    print(f"   Topic对象:")
    print(f"   - topic_id: {topic.topic_id}")
    print(f"   - topic_name: {topic.topic_name}")
    print(f"   - popularity: {topic.popularity}")
    print(f"   - to_dict()[topic_id]: {topic.to_dict().get('topic_id')}")
    print(f"   - validate(): {topic.validate()}")
    
    # 3. 测试smart_classifier中的_create_new_topic方法
    print("\n3. 测试smart_classifier._create_new_topic():")
    
    # 直接调用_create_new_topic方法
    test_topic_name = "Debug Test Topic"
    test_brief = "This is a debug test topic for troubleshooting"
    
    print(f"   调用参数: topic_name='{test_topic_name}', brief='{test_brief}'")
    
    try:
        # 调用私有方法进行调试
        new_topic_id = smart_classifier._create_new_topic(test_topic_name, test_brief)
        print(f"   返回的topic_id: {new_topic_id}")
        
        if new_topic_id:
            # 验证是否真的插入到了数据库
            saved_topic = topic_dao.get_topic_by_id(new_topic_id)
            if saved_topic:
                print(f"   ✅ 成功创建并保存到数据库")
                print(f"   保存的topic信息:")
                print(f"   - topic_id: {saved_topic.topic_id}")
                print(f"   - topic_name: {saved_topic.topic_name}")
                print(f"   - popularity: {saved_topic.popularity}")
            else:
                print(f"   ❌ 虽然返回了topic_id，但数据库中查询不到")
        else:
            print(f"   ❌ 返回的topic_id为None")
            
    except Exception as e:
        print(f"   ❌ 调用_create_new_topic时出错: {e}")
        import traceback
        traceback.print_exc()


def debug_topic_dao_insert():
    """调试topic_dao的insert方法"""
    print("\n4. 测试topic_dao.insert():")
    
    # 创建一个测试topic
    test_topic = Topic(
        topic_id=Topic.generate_topic_id(),
        topic_name="Direct DAO Test Topic",
        brief="Testing direct DAO insert method",
        created_at=datetime.now(),
        popularity=7,
        update_time=datetime.now()
    )
    
    print(f"   测试Topic:")
    print(f"   - topic_id: {test_topic.topic_id}")
    print(f"   - topic_name: {test_topic.topic_name}")
    print(f"   - popularity: {test_topic.popularity}")
    
    try:
        success = topic_dao.insert(test_topic)
        print(f"   insert()结果: {success}")
        
        if success:
            # 验证插入结果
            saved_topic = topic_dao.get_topic_by_id(test_topic.topic_id)
            if saved_topic:
                print(f"   ✅ 成功插入并验证")
                print(f"   数据库中的数据:")
                print(f"   - topic_id: {saved_topic.topic_id}")
                print(f"   - topic_name: {saved_topic.topic_name}")
                print(f"   - popularity: {saved_topic.popularity}")
            else:
                print(f"   ❌ 插入成功但验证失败")
        else:
            print(f"   ❌ 插入失败")
            
    except Exception as e:
        print(f"   ❌ 调用insert时出错: {e}")
        import traceback
        traceback.print_exc()


def debug_classification_flow():
    """调试完整的分类流程"""
    print("\n5. 测试完整的分类流程:")
    
    # 模拟一个DeFi话题的推文
    test_text = "DeFi protocols are offering amazing yield farming opportunities. Users can earn passive income by providing liquidity to various pools."
    
    print(f"   测试文本: {test_text}")
    
    try:
        # 直接调用AI分类
        classification = smart_classifier._ai_classify_content(test_text)
        print(f"   AI分类结果: {classification}")
        
        if classification and classification.get('type') == 'topic':
            topic_name = classification.get('name', '')
            print(f"   识别的话题名称: {topic_name}")
            
            # 调用话题分类处理
            result = smart_classifier._handle_topic_classification(
                topic_name, 
                classification, 
                "test_tweet_id"
            )
            
            print(f"   分类处理结果:")
            print(f"   - content_type: {result.content_type}")
            print(f"   - topic_id: {result.topic_id}")
            print(f"   - entity_name: {result.entity_name}")
            print(f"   - confidence: {result.confidence}")
            print(f"   - is_new_created: {result.is_new_created}")
            print(f"   - reason: {result.reason}")
            
        else:
            print(f"   ❌ AI分类没有识别为topic类型")
            
    except Exception as e:
        print(f"   ❌ 分类流程出错: {e}")
        import traceback
        traceback.print_exc()


def main():
    """主调试函数"""
    print("🐛 Topic创建和保存问题调试")
    print("=" * 80)
    
    try:
        # 1. 调试topic ID生成
        debug_topic_generation()
        
        # 2. 调试topic_dao插入
        debug_topic_dao_insert()
        
        # 3. 调试完整分类流程
        debug_classification_flow()
        
        print("\n" + "=" * 80)
        print("🎯 调试完成！请检查上述输出，找出问题所在。")
        
    except Exception as e:
        print(f"\n❌ 调试过程出错: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()