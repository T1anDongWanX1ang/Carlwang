#!/usr/bin/env python3
"""
测试Topic修复结果
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


def test_topic_auto_generation():
    """测试Topic自动生成topic_id"""
    setup_logger()
    
    print("🔧 测试Topic自动生成topic_id修复结果")
    print("=" * 60)
    
    # 1. 测试不传topic_id的Topic对象
    print("1. 测试不传topic_id的Topic对象:")
    auto_topic = Topic(
        topic_name="Auto Generated Topic",
        brief="Testing automatic topic_id generation",
        created_at=datetime.now(),
        popularity=3,  # 设置一个非1的值
        update_time=datetime.now()
    )
    
    print(f"   created topic:")
    print(f"   - topic_id: {auto_topic.topic_id}")
    print(f"   - topic_name: {auto_topic.topic_name}")
    print(f"   - popularity: {auto_topic.popularity}")
    print(f"   - validate(): {auto_topic.validate()}")
    
    # 确认topic_id被自动生成且不为None
    if auto_topic.topic_id and auto_topic.topic_id.startswith('topic_'):
        print("   ✅ topic_id自动生成成功!")
    else:
        print("   ❌ topic_id自动生成失败!")
        return False
    
    # 2. 测试数据库插入
    print("\n2. 测试数据库插入:")
    try:
        success = topic_dao.insert(auto_topic)
        print(f"   insert()结果: {success}")
        
        if success:
            # 验证插入结果
            saved_topic = topic_dao.get_topic_by_id(auto_topic.topic_id)
            if saved_topic:
                print("   ✅ 插入成功并验证通过!")
                print(f"   数据库中的数据:")
                print(f"   - topic_id: {saved_topic.topic_id}")
                print(f"   - topic_name: {saved_topic.topic_name}")
                print(f"   - popularity: {saved_topic.popularity}")
                
                # 检查popularity是否正确保存
                if saved_topic.popularity == auto_topic.popularity:
                    print("   ✅ popularity正确保存!")
                    return True
                else:
                    print(f"   ❌ popularity保存错误: 期望{auto_topic.popularity}, 实际{saved_topic.popularity}")
                    return False
            else:
                print("   ❌ 插入成功但验证失败")
                return False
        else:
            print("   ❌ 插入失败")
            return False
            
    except Exception as e:
        print(f"   ❌ 插入时异常: {e}")
        return False


def test_smart_classifier_fix():
    """测试smart_classifier的修复"""
    print("\n3. 测试smart_classifier创建topic:")
    
    try:
        # 测试_create_new_topic方法
        topic_name = "Smart Classifier Test Topic"
        brief = "Testing smart classifier topic creation with fix"
        
        topic_id = smart_classifier._create_new_topic(topic_name, brief)
        print(f"   _create_new_topic返回: {topic_id}")
        
        if topic_id and topic_id.startswith('topic_'):
            print("   ✅ smart_classifier创建topic成功!")
            
            # 验证数据库中的数据
            saved_topic = topic_dao.get_topic_by_id(topic_id)
            if saved_topic:
                print(f"   数据库验证:")
                print(f"   - topic_id: {saved_topic.topic_id}")
                print(f"   - topic_name: {saved_topic.topic_name}")
                print(f"   - popularity: {saved_topic.popularity}")
                return True
            else:
                print("   ❌ 数据库验证失败")
                return False
        else:
            print("   ❌ smart_classifier创建topic失败")
            return False
            
    except Exception as e:
        print(f"   ❌ smart_classifier测试异常: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_complex_topic_creation():
    """测试复杂的topic创建场景"""
    print("\n4. 测试复杂topic创建:")
    
    # 模拟用户报错的复杂数据
    complex_topic = Topic(
        topic_name='DeFi Yield Farming',
        brief='Exploring DeFi protocols and yield farming opportunities reshaping traditional finance.',
        key_entities=None,
        popularity=4,
        propagation_speed_5m=0.0,
        propagation_speed_1h=0.0,
        propagation_speed_4h=0.0,
        kol_opinions=[],  # 空列表而非字符串
        mob_opinion_direction='positive',
        summary='DeFi Yield Farming是DeFi协议通过提供收益农场机会彻底改变传统金融。',
        popularity_history=[{"popularity": 4, "timestamp": "2025-09-11T14:26:55.712731"}],
        created_at=datetime(2025, 9, 11, 14, 15, 4),
        update_time=datetime.now()
    )
    
    print(f"   复杂Topic:")
    print(f"   - topic_id: {complex_topic.topic_id}")
    print(f"   - topic_name: {complex_topic.topic_name}")
    print(f"   - popularity: {complex_topic.popularity}")
    print(f"   - kol_opinions类型: {type(complex_topic.kol_opinions)}")
    print(f"   - popularity_history类型: {type(complex_topic.popularity_history)}")
    
    # 测试插入
    try:
        success = topic_dao.insert(complex_topic)
        print(f"   insert()结果: {success}")
        
        if success:
            print("   ✅ 复杂topic创建成功!")
            return True
        else:
            print("   ❌ 复杂topic创建失败")
            return False
            
    except Exception as e:
        print(f"   ❌ 复杂topic创建异常: {e}")
        return False


def main():
    """主测试函数"""
    print("🧪 Topic修复验证测试")
    print("=" * 80)
    
    results = []
    
    # 运行所有测试
    results.append(("Topic自动生成", test_topic_auto_generation()))
    results.append(("SmartClassifier修复", test_smart_classifier_fix()))
    results.append(("复杂Topic创建", test_complex_topic_creation()))
    
    # 输出结果
    print("\n" + "=" * 80)
    print("🎯 测试结果汇总:")
    
    all_passed = True
    for test_name, passed in results:
        status = "✅ 通过" if passed else "❌ 失败"
        print(f"   {test_name}: {status}")
        if not passed:
            all_passed = False
    
    if all_passed:
        print("\n🎉 所有测试通过!")
        print("✅ topic_id为None的问题已修复")
        print("✅ Topic模型现在会自动生成topic_id")
        print("✅ popularity可以正确保存")
        return True
    else:
        print("\n⚠️ 部分测试失败，需要进一步调试")
        return False


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)