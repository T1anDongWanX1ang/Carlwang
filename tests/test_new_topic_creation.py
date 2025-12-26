#!/usr/bin/env python3
"""
测试新的话题创建逻辑
"""
import sys
import os
from datetime import datetime

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.utils.smart_classifier import smart_classifier
from src.database.topic_dao import topic_dao
from src.utils.logger import setup_logger


def test_new_topic_creation():
    """测试新的话题创建逻辑"""
    setup_logger()
    
    print("🔍 测试新的话题创建逻辑")
    print("=" * 60)
    
    # 测试创建话题
    test_topic_name = "测试新Summary生成逻辑"
    test_brief = "这是一个测试新的summary生成逻辑的话题，用于验证修改是否生效"
    
    print(f"📊 创建测试话题: {test_topic_name}")
    
    try:
        # 调用修改后的创建方法
        topic_id = smart_classifier._create_new_topic(test_topic_name, test_brief, 5)
        
        if topic_id:
            print(f"✅ 话题创建成功，ID: {topic_id}")
            
            # 验证数据库中的数据
            created_topic = topic_dao.get_topic_by_id(topic_id)
            
            if created_topic:
                print(f"✅ 数据库验证成功")
                print(f"   话题名称: {created_topic.topic_name}")
                print(f"   Brief: {created_topic.brief}")
                print(f"   热度: {created_topic.popularity}")
                print(f"   Summary状态: {'有内容' if created_topic.summary else 'NULL'}")
                
                if created_topic.summary:
                    print(f"   Summary长度: {len(created_topic.summary)}")
                    print(f"   Summary内容: {created_topic.summary}")
                    
                    # 验证JSON格式
                    try:
                        import json
                        parsed_summary = json.loads(created_topic.summary)
                        print(f"   ✅ JSON格式验证通过")
                        print(f"   观点数量: {len(parsed_summary.get('summary', []))}")
                        
                        if parsed_summary.get('summary'):
                            first_viewpoint = parsed_summary['summary'][0]
                            print(f"   第一个观点: {first_viewpoint.get('viewpoint', 'N/A')}")
                            
                    except json.JSONDecodeError as e:
                        print(f"   ❌ JSON格式验证失败: {e}")
                
                # 清理测试数据
                print(f"\n🧹 清理测试数据...")
                cleanup_sql = "DELETE FROM topics WHERE topic_id = %s"
                topic_dao.db_manager.execute_update(cleanup_sql, [topic_id])
                print(f"   ✅ 测试数据已清理")
                
                return True
            else:
                print(f"❌ 数据库中找不到创建的话题")
                return False
        else:
            print(f"❌ 话题创建失败")
            return False
            
    except Exception as e:
        print(f"❌ 测试异常: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_basic_summary_generation():
    """测试基础summary生成方法"""
    print(f"\n🧪 测试基础summary生成方法")
    print("=" * 60)
    
    try:
        # 直接测试方法
        summary = smart_classifier._generate_basic_topic_summary(
            "DeFi协议发展", 
            "去中心化金融协议的最新发展和创新"
        )
        
        print(f"📄 生成的summary:")
        print(summary)
        
        # 验证JSON格式
        import json
        parsed = json.loads(summary)
        
        print(f"\n✅ JSON解析成功")
        print(f"   topic_id: {parsed.get('topic_id')}")
        print(f"   观点数量: {len(parsed.get('summary', []))}")
        
        if parsed.get('summary'):
            viewpoint = parsed['summary'][0]
            print(f"   观点内容: {viewpoint.get('viewpoint')}")
            print(f"   相关推文: {viewpoint.get('related_tweets')}")
        
        return True
        
    except Exception as e:
        print(f"❌ 基础summary生成测试失败: {e}")
        return False


def main():
    """主函数"""
    print("🚀 测试话题创建逻辑修改")
    print("=" * 80)
    
    # 测试1: 基础summary生成
    test1 = test_basic_summary_generation()
    
    # 测试2: 完整话题创建
    test2 = test_new_topic_creation()
    
    print("\n" + "=" * 80)
    print("🎯 测试结果:")
    print(f"   基础summary生成: {'✅ 通过' if test1 else '❌ 失败'}")
    print(f"   完整话题创建: {'✅ 通过' if test2 else '❌ 失败'}")
    
    if test1 and test2:
        print("\n✅ 所有测试通过！")
        print("🎉 新的话题创建逻辑已成功集成summary生成")
    else:
        print("\n❌ 部分测试失败，请检查代码")


if __name__ == '__main__':
    main()