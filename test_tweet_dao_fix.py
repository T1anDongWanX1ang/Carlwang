#!/usr/bin/env python3
"""
测试推文DAO修复
"""
import sys
import os
from datetime import datetime

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.models.tweet import Tweet
from src.database.tweet_dao import tweet_dao
from src.utils.logger import setup_logger


def test_tweet_creation_with_link_url():
    """测试包含link_url字段的推文创建"""
    setup_logger()
    
    print("🧪 测试推文DAO修复")
    print("=" * 60)
    
    # 测试1: 正常推文对象（包含link_url字段）
    print("1️⃣ 测试正常推文对象")
    tweet1 = Tweet(
        id_str="test_tweet_1",
        full_text="这是一条测试推文",
        created_at_datetime=datetime.now(),
        favorite_count=10,
        retweet_count=5,
        kol_id="test_kol",
        link_url="https://example.com/image.jpg"
    )
    
    tweet1_dict = tweet1.to_dict()
    print(f"   包含link_url字段: {'link_url' in tweet1_dict}")
    print(f"   link_url值: {tweet1_dict['link_url']}")
    print(f"   字典字段数: {len(tweet1_dict)}")
    
    # 测试2: 通过from_api_data创建的推文对象（可能没有link_url字段）
    print(f"\n2️⃣ 测试从API数据创建的推文对象")
    
    # 模拟API数据（不包含link_url相关信息）
    api_data = {
        "id_str": "test_tweet_2",
        "full_text": "来自API的推文",
        "favorite_count": 20,
        "retweet_count": 10
    }
    
    field_mapping = {
        "id_str": "id_str",
        "full_text": "full_text",
        "favorite_count": "favorite_count",
        "retweet_count": "retweet_count"
    }
    
    tweet2 = Tweet.from_api_data(api_data, field_mapping)
    tweet2_dict = tweet2.to_dict()
    
    print(f"   包含link_url字段: {'link_url' in tweet2_dict}")
    print(f"   link_url值: {tweet2_dict['link_url']}")
    print(f"   字典字段数: {len(tweet2_dict)}")
    
    # 测试3: 模拟没有link_url属性的推文对象
    print(f"\n3️⃣ 测试没有link_url属性的推文对象")
    
    tweet3 = Tweet(id_str="test_tweet_3", full_text="没有link_url的推文")
    # 删除link_url属性（模拟旧版本对象）
    if hasattr(tweet3, 'link_url'):
        delattr(tweet3, 'link_url')
    
    try:
        tweet3_dict = tweet3.to_dict()
        print(f"   包含link_url字段: {'link_url' in tweet3_dict}")
        print(f"   link_url值: {tweet3_dict['link_url']}")
        print(f"   ✅ 安全处理缺失link_url属性")
    except Exception as e:
        print(f"   ❌ 处理缺失link_url属性失败: {e}")
        return False
    
    # 测试4: 验证DAO插入参数
    print(f"\n4️⃣ 测试DAO插入参数生成")
    
    test_tweets = [tweet1, tweet2, tweet3]
    for i, tweet in enumerate(test_tweets, 1):
        try:
            tweet_data = tweet.to_dict()
            
            # 模拟DAO中的参数生成
            params = (
                tweet_data['id_str'],
                tweet_data['conversation_id_str'],
                tweet_data['in_reply_to_status_id_str'],
                tweet_data['full_text'],
                tweet_data['created_at'],
                tweet_data['created_at_datetime'],
                tweet_data['bookmark_count'],
                tweet_data['favorite_count'],
                tweet_data['quote_count'],
                tweet_data['reply_count'],
                tweet_data['retweet_count'],
                tweet_data['view_count'],
                tweet_data['engagement_total'],
                tweet_data['update_time'],
                tweet_data['kol_id'],
                tweet_data['entity_id'],
                tweet_data['project_id'],
                tweet_data['topic_id'],
                tweet_data['is_valid'],
                tweet_data['sentiment'],
                tweet_data['tweet_url'],
                tweet_data.get('link_url')  # 使用get方法
            )
            
            print(f"   推文{i} 参数长度: {len(params)} (期望22)")
            if len(params) == 22:
                print(f"   推文{i} ✅ 参数数量正确")
            else:
                print(f"   推文{i} ❌ 参数数量错误")
                return False
                
        except Exception as e:
            print(f"   推文{i} ❌ 参数生成失败: {e}")
            return False
    
    return True


def test_actual_database_insert():
    """测试实际数据库插入"""
    print(f"\n5️⃣ 测试实际数据库插入")
    
    try:
        # 创建测试推文
        test_tweet = Tweet(
            id_str=f"test_dao_fix_{int(datetime.now().timestamp())}",
            full_text="测试DAO修复的推文",
            created_at_datetime=datetime.now(),
            favorite_count=1,
            retweet_count=0,
            kol_id="test_kol",
            link_url="https://test.com/image.jpg",
            is_valid=1
        )
        
        print(f"   创建测试推文: {test_tweet.id_str}")
        
        # 尝试插入数据库
        success = tweet_dao.upsert_tweet(test_tweet)
        
        if success:
            print("   ✅ 数据库插入成功")
            return True
        else:
            print("   ❌ 数据库插入失败")
            return False
            
    except Exception as e:
        print(f"   ❌ 数据库插入异常: {e}")
        return False


def test_original_error_scenario():
    """测试原始错误场景"""
    print(f"\n6️⃣ 模拟原始错误场景")
    
    try:
        # 模拟原始错误中的推文数据
        problematic_tweet = Tweet(
            id_str="1966384299927904620",
            conversation_id_str="1966384299927904620",
            full_text="$SOL 领涨， 重点关注下9月16日tge的项目 @_portals_ ：\n1、叙事：Sol上的web3游戏和创作者平台，也就是web3版的Roblox ；在此平台，不仅可以发币、也可以发行agent、nft、游戏等，帮助创作者全球营销和",
            created_at_datetime=datetime.now(),
            favorite_count=0,
            retweet_count=0,
            kol_id="test_kol",
            is_valid=1
        )
        
        # 删除link_url属性（模拟问题场景）
        if hasattr(problematic_tweet, 'link_url'):
            delattr(problematic_tweet, 'link_url')
        
        print(f"   问题推文ID: {problematic_tweet.id_str}")
        print(f"   有link_url属性: {hasattr(problematic_tweet, 'link_url')}")
        
        # 测试to_dict方法
        tweet_dict = problematic_tweet.to_dict()
        print(f"   to_dict包含link_url: {'link_url' in tweet_dict}")
        print(f"   link_url值: {tweet_dict.get('link_url')}")
        
        # 测试参数生成
        params = (
            tweet_dict['id_str'],
            tweet_dict['conversation_id_str'],
            tweet_dict['in_reply_to_status_id_str'],
            tweet_dict['full_text'],
            tweet_dict['created_at'],
            tweet_dict['created_at_datetime'],
            tweet_dict['bookmark_count'],
            tweet_dict['favorite_count'],
            tweet_dict['quote_count'],
            tweet_dict['reply_count'],
            tweet_dict['retweet_count'],
            tweet_dict['view_count'],
            tweet_dict['engagement_total'],
            tweet_dict['update_time'],
            tweet_dict['kol_id'],
            tweet_dict['entity_id'],
            tweet_dict['project_id'],
            tweet_dict['topic_id'],
            tweet_dict['is_valid'],
            tweet_dict['sentiment'],
            tweet_dict['tweet_url'],
            tweet_dict.get('link_url')
        )
        
        print(f"   参数数量: {len(params)} (SQL需要22)")
        
        if len(params) == 22:
            # 尝试实际插入
            problematic_tweet.id_str = f"test_fix_scenario_{int(datetime.now().timestamp())}"
            success = tweet_dao.upsert_tweet(problematic_tweet)
            
            if success:
                print("   ✅ 原始错误场景修复成功！")
                return True
            else:
                print("   ❌ 插入仍然失败")
                return False
        else:
            print("   ❌ 参数数量仍然不匹配")
            return False
            
    except Exception as e:
        print(f"   ❌ 原始场景测试异常: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """主函数"""
    print("🔧 推文DAO参数不匹配修复测试")
    print("=" * 80)
    
    tests = [
        ("推文对象创建和参数生成", test_tweet_creation_with_link_url),
        ("实际数据库插入", test_actual_database_insert),
        ("原始错误场景验证", test_original_error_scenario)
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
            import traceback
            traceback.print_exc()
    
    print("=" * 80)
    print("🎯 测试总结")
    print("=" * 80)
    print(f"✅ 通过测试: {passed}/{total}")
    print(f"📊 通过率: {passed/total*100:.1f}%")
    
    if passed == total:
        print("🎉 所有测试通过！推文DAO修复成功")
        return True
    else:
        print("⚠️ 部分测试失败，请检查修复")
        return False


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)