#!/usr/bin/env python3
"""
测试用户DAO修复
"""
import sys
import os
from datetime import datetime

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.models.user import TwitterUser
from src.database.user_dao import user_dao
from src.utils.logger import setup_logger


def test_user_creation_with_language():
    """测试包含language字段的用户创建"""
    setup_logger()
    
    print("🧪 测试用户DAO修复")
    print("=" * 60)
    
    # 测试1: 正常用户对象（包含language字段）
    print("1️⃣ 测试正常用户对象")
    user1 = TwitterUser(
        id_str="test_user_1",
        screen_name="test_user",
        name="Test User",
        description="Test description",
        avatar="https://example.com/avatar.jpg",
        created_at="Fri Jan 29 00:19:52 +0000 2021",
        followers_count=1000,
        friends_count=500,
        statuses_count=100,
        language="English",
        update_time=datetime.now()
    )
    
    user1_dict = user1.to_dict()
    print(f"   包含language字段: {'language' in user1_dict}")
    print(f"   language值: {user1_dict['language']}")
    print(f"   字典字段数: {len(user1_dict)}")
    
    # 测试2: 通过from_api_data创建的用户对象（可能没有language字段）
    print(f"\n2️⃣ 测试从API数据创建的用户对象")
    
    # 模拟API数据（不包含language相关信息）
    api_data = {
        "id_str": "test_user_2",
        "screen_name": "api_user",
        "name": "API User",
        "description": "User from API",
        "followers_count": 2000,
        "friends_count": 800
    }
    
    field_mapping = {
        "id_str": "id_str",
        "screen_name": "screen_name", 
        "name": "name",
        "description": "description",
        "followers_count": "followers_count",
        "friends_count": "friends_count"
    }
    
    user2 = TwitterUser.from_api_data(api_data, field_mapping)
    user2_dict = user2.to_dict()
    
    print(f"   包含language字段: {'language' in user2_dict}")
    print(f"   language值: {user2_dict['language']}")
    print(f"   字典字段数: {len(user2_dict)}")
    
    # 测试3: 模拟没有language属性的用户对象
    print(f"\n3️⃣ 测试没有language属性的用户对象")
    
    user3 = TwitterUser(id_str="test_user_3")
    # 删除language属性（模拟旧版本对象）
    if hasattr(user3, 'language'):
        delattr(user3, 'language')
    
    try:
        user3_dict = user3.to_dict()
        print(f"   包含language字段: {'language' in user3_dict}")
        print(f"   language值: {user3_dict['language']}")
        print(f"   ✅ 安全处理缺失language属性")
    except Exception as e:
        print(f"   ❌ 处理缺失language属性失败: {e}")
        return False
    
    # 测试4: 验证DAO插入参数
    print(f"\n4️⃣ 测试DAO插入参数生成")
    
    test_users = [user1, user2, user3]
    for i, user in enumerate(test_users, 1):
        try:
            user_data = user.to_dict()
            
            # 模拟DAO中的参数生成
            params = (
                user_data['id_str'],
                user_data['screen_name'],
                user_data['name'],
                user_data['description'],
                user_data['avatar'],
                user_data['created_at'],
                user_data['followers_count'],
                user_data['friends_count'],
                user_data['statuses_count'],
                user_data.get('language'),  # 使用get方法
                user_data['update_time']
            )
            
            print(f"   用户{i} 参数长度: {len(params)} (期望11)")
            if len(params) == 11:
                print(f"   用户{i} ✅ 参数数量正确")
            else:
                print(f"   用户{i} ❌ 参数数量错误")
                return False
                
        except Exception as e:
            print(f"   用户{i} ❌ 参数生成失败: {e}")
            return False
    
    return True


def test_actual_database_insert():
    """测试实际数据库插入"""
    print(f"\n5️⃣ 测试实际数据库插入")
    
    try:
        # 创建测试用户
        test_user = TwitterUser(
            id_str=f"test_dao_fix_{int(datetime.now().timestamp())}",
            screen_name="dao_test_user",
            name="DAO Test User", 
            description="Testing DAO fix",
            followers_count=100,
            language="English"
        )
        
        print(f"   创建测试用户: {test_user.id_str}")
        
        # 尝试插入数据库
        success = user_dao.upsert_user(test_user)
        
        if success:
            print("   ✅ 数据库插入成功")
            return True
        else:
            print("   ❌ 数据库插入失败")
            return False
            
    except Exception as e:
        print(f"   ❌ 数据库插入异常: {e}")
        return False


def main():
    """主函数"""
    print("🔧 用户DAO参数不匹配修复测试")
    print("=" * 80)
    
    tests = [
        ("用户对象创建和参数生成", test_user_creation_with_language),
        ("实际数据库插入", test_actual_database_insert)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            if result:
                print(f"✅ {test_name} - 通过")
                passed += 1
            else:
                print(f"❌ {test_name} - 失败")
        except Exception as e:
            print(f"❌ {test_name} - 异常: {e}")
    
    print("=" * 80)
    print("🎯 测试总结")
    print("=" * 80)
    print(f"✅ 通过测试: {passed}/{total}")
    print(f"📊 通过率: {passed/total*100:.1f}%")
    
    if passed == total:
        print("🎉 所有测试通过！用户DAO修复成功")
        return True
    else:
        print("⚠️ 部分测试失败，请检查修复")
        return False


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)