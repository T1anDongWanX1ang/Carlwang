#!/usr/bin/env python3
"""
专门调试topic_id为None的问题
根据用户提供的错误信息进行针对性调试
"""
import sys
import os

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.models.topic import Topic
from src.database.topic_dao import topic_dao
from src.utils.logger import setup_logger
from datetime import datetime


def debug_none_topic_id_issue():
    """调试topic_id为None的具体问题"""
    setup_logger()
    
    print("🔍 调试topic_id为None的问题")
    print("=" * 60)
    
    # 基于用户提供的错误信息，模拟相同的数据
    print("1. 模拟用户报错的场景...")
    
    # 创建一个topic_id为None的Topic对象 (模拟可能的错误情况)
    problematic_topic = Topic(
        topic_id=None,  # 故意设置为None
        topic_name='DeFi Yield Farming',
        created_at=datetime(2025, 9, 11, 14, 15, 4),
        brief='Exploring DeFi protocols and yield farming opportunities reshaping traditional finance.',
        key_entities=None,
        popularity=4,
        propagation_speed_5m=0.0,
        propagation_speed_1h=0.0,
        propagation_speed_4h=0.0,
        kol_opinions='[]',
        mob_opinion_direction='positive',
        summary='DeFi Yield Farming是DeFi协议通过提供收益农场机会彻底改变传统金融。这种新型金融模式允许用户通过提供流动性或参与其他活动来获得收益，同时推动DeFi生态系统的发展。市场关注点集中在收益率的稳定性、项目的可靠性和安全性，以及参与者的风险管理策略。争议主要集中在项目的透明度、智能合约的安全性以及市场操纵的风险。随着DeFi行业的快速发展，DeFi Yield Farming将继续受到关注，并可能面临监管挑战和技术难题。',
        popularity_history='[{"popularity": 4, "timestamp": "2025-09-11T14:26:55.712731"}]',
        update_time=datetime.now()
    )
    
    print(f"   problematic_topic.topic_id: {problematic_topic.topic_id}")
    print(f"   problematic_topic.topic_name: {problematic_topic.topic_name}")
    print(f"   problematic_topic.popularity: {problematic_topic.popularity}")
    print(f"   problematic_topic.validate(): {problematic_topic.validate()}")
    
    # 尝试调用to_dict()
    topic_dict = problematic_topic.to_dict()
    print(f"   to_dict()['topic_id']: {topic_dict.get('topic_id')}")
    print(f"   to_dict()['popularity']: {topic_dict.get('popularity')}")
    
    # 2. 测试Topic的validate方法对topic_id的处理
    print("\n2. 测试Topic.validate()对None topic_id的处理...")
    
    # Topic模型的validate方法检查
    print(f"   Topic对象validate结果: {problematic_topic.validate()}")
    
    # 检查Topic.validate()的实现
    if not problematic_topic.topic_name:
        print("   ❌ topic_name为空")
    else:
        print(f"   ✅ topic_name不为空: {problematic_topic.topic_name}")
        
    # 3. 测试topic_dao.insert对None topic_id的处理
    print("\n3. 测试topic_dao.insert对None topic_id的处理...")
    
    try:
        success = topic_dao.insert(problematic_topic)
        print(f"   insert()结果: {success}")
        
        if not success:
            print("   ❌ 插入失败 - 这可能就是问题所在!")
        else:
            print("   ✅ 插入成功 - 但topic_id为None应该是不被允许的")
            
    except Exception as e:
        print(f"   ❌ 插入时出现异常: {e}")
        print("   这可能就是问题的根源!")
    
    # 4. 检查数据库表的topic_id字段约束
    print("\n4. 检查数据库表的topic_id字段约束...")
    
    try:
        # 尝试查询表结构
        sql = f"DESCRIBE {topic_dao.table_name}"
        result = topic_dao.db_manager.execute_query(sql)
        
        if result:
            print("   数据库表结构:")
            for row in result:
                field_name = row.get('Field', row.get('field', ''))
                field_type = row.get('Type', row.get('type', ''))
                field_null = row.get('Null', row.get('null', ''))
                field_key = row.get('Key', row.get('key', ''))
                
                if 'topic_id' in field_name.lower():
                    print(f"   - {field_name}: {field_type}, Null={field_null}, Key={field_key}")
                    
                    if field_null.upper() == 'NO':
                        print("     ⚠️  topic_id字段不允许NULL - 这是问题根源!")
                    else:
                        print("     topic_id字段允许NULL")
        else:
            print("   ❌ 无法查询表结构")
            
    except Exception as e:
        print(f"   ❌ 查询表结构失败: {e}")
    
    # 5. 测试Topic对象在topic_id为None时的行为
    print("\n5. 分析Topic模型的问题...")
    
    # 检查Topic的__init__方法是否应该自动生成topic_id
    print("   检查Topic模型是否应该自动生成topic_id...")
    
    # 创建一个没有指定topic_id的Topic对象
    auto_topic = Topic(
        topic_name='Auto Generate Test',
        brief='Testing automatic topic_id generation',
        created_at=datetime.now(),
        popularity=1,
        update_time=datetime.now()
    )
    
    print(f"   未指定topic_id的Topic对象:")
    print(f"   - topic_id: {auto_topic.topic_id}")
    print(f"   - topic_name: {auto_topic.topic_name}")
    
    if auto_topic.topic_id is None:
        print("   ❌ Topic模型没有自动生成topic_id!")
        print("   🔧 这可能需要在Topic.__post_init__中添加自动生成逻辑")
    else:
        print("   ✅ Topic模型自动生成了topic_id")


def propose_fixes():
    """提出修复方案"""
    print("\n" + "=" * 60)
    print("🔧 问题分析和修复建议:")
    print("=" * 60)
    
    print("问题1: topic_id为None导致数据库插入失败")
    print("  原因: Topic对象在创建时topic_id可能未被正确设置")
    print("  解决方案:")
    print("    1. 在Topic.__post_init__方法中自动生成topic_id")
    print("    2. 或在smart_classifier._create_new_topic()中确保topic_id不为None")
    print("    3. 在topic_dao.insert()中添加topic_id验证")
    
    print("\n问题2: popularity始终为1")
    print("  原因: 可能是默认值设置问题或缓存问题")
    print("  解决方案:")
    print("    1. 检查Topic模型的popularity字段默认值")
    print("    2. 检查smart_classifier中的popularity设置逻辑")
    print("    3. 验证数据库中的实际存储值")
    
    print("\n问题3: 数据库字段约束")
    print("  原因: topic_id字段可能有NOT NULL约束但代码未验证")
    print("  解决方案:")
    print("    1. 确保所有Topic对象都有有效的topic_id")
    print("    2. 在插入前进行数据验证")


def main():
    """主函数"""
    print("🚨 专项调试: topic_id为None的问题")
    print("=" * 80)
    
    debug_none_topic_id_issue()
    propose_fixes()
    
    print("\n" + "=" * 80)
    print("🎯 调试完成!")


if __name__ == '__main__':
    main()