#!/usr/bin/env python3
"""
测试entities字段链接提取功能
"""
import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.models.tweet import Tweet
from src.utils.logger import setup_logger


def test_link_extraction():
    """测试从entities数组中提取链接"""
    setup_logger()
    
    print("🔗 测试entities字段链接提取")
    print("=" * 60)
    
    # 测试用例
    test_cases = [
        {
            "name": "正常的photo类型链接",
            "entities": [
                {"type": "photo", "link": "https://example.com/image1.jpg"},
                {"type": "url", "link": "https://other.com/page2"}
            ],
            "expected": "https://example.com/image1.jpg"
        },
        {
            "name": "多个photo类型，取第一个",
            "entities": [
                {"type": "photo", "link": "https://first.com/image1.jpg"},
                {"type": "photo", "link": "https://second.com/image2.jpg"}
            ],
            "expected": "https://first.com/image1.jpg"
        },
        {
            "name": "没有photo类型",
            "entities": [
                {"type": "url", "link": "https://example.com"},
                {"type": "mention", "text": "@user"}
            ],
            "expected": None
        },
        {
            "name": "空entities数组",
            "entities": [],
            "expected": None
        },
        {
            "name": "entities为None",
            "entities": None,
            "expected": None
        },
        {
            "name": "photo类型但没有link字段",
            "entities": [
                {"type": "photo", "text": "image.jpg"},
                {"type": "url", "link": "https://example.com"}
            ],
            "expected": None
        },
        {
            "name": "photo类型link为空字符串",
            "entities": [
                {"type": "photo", "link": ""},
                {"type": "url", "link": "https://example.com"}
            ],
            "expected": None
        }
    ]
    
    passed = 0
    total = len(test_cases)
    
    for i, test_case in enumerate(test_cases, 1):
        name = test_case["name"]
        entities = test_case["entities"]
        expected = test_case["expected"]
        
        print(f"\n{i}. 测试: {name}")
        print(f"   输入: {entities}")
        
        # 调用提取函数
        result = Tweet._extract_link_from_entities(entities)
        
        print(f"   输出: {result}")
        print(f"   期望: {expected}")
        
        if result == expected:
            print("   ✅ 通过")
            passed += 1
        else:
            print("   ❌ 失败")
    
    print(f"\n{'='*60}")
    print(f"📊 测试结果: {passed}/{total} 通过 ({passed/total*100:.1f}%)")
    
    return passed == total


def test_tweet_creation_with_entities():
    """测试Tweet对象创建时是否正确处理entities字段"""
    print(f"\n🐦 测试Tweet对象创建")
    print("=" * 60)
    
    # 模拟API数据
    api_data = {
        "id_str": "1234567890123456789",
        "full_text": "这是一条测试推文",
        "created_at": "2025-01-01",
        "favorite_count": 10,
        "retweet_count": 5,
        "entities": [
            {"type": "photo", "link": "https://test.com/article"},
            {"type": "url", "link": "https://other.com"}
        ]
    }
    
    # 字段映射配置
    field_mapping = {
        "id_str": "id_str",
        "full_text": "full_text", 
        "created_at": "created_at",
        "favorite_count": "favorite_count",
        "retweet_count": "retweet_count"
    }
    
    print("1. 测试正常entities数据")
    tweet = Tweet.from_api_data(api_data, field_mapping)
    
    print(f"   推文ID: {tweet.id_str}")
    print(f"   推文内容: {tweet.full_text}")
    print(f"   提取的链接: {tweet.link_url}")
    
    if tweet.link_url == "https://test.com/article":
        print("   ✅ 链接提取成功")
        result1 = True
    else:
        print("   ❌ 链接提取失败")
        result1 = False
    
    # 测试没有entities字段的情况
    api_data_no_entities = {
        "id_str": "1234567890123456790",
        "full_text": "没有entities的推文",
        "created_at": "2025-01-01"
    }
    
    print(f"\n2. 测试无entities数据")
    tweet2 = Tweet.from_api_data(api_data_no_entities, field_mapping)
    
    print(f"   推文ID: {tweet2.id_str}")
    print(f"   推文内容: {tweet2.full_text}")
    print(f"   提取的链接: {tweet2.link_url}")
    
    if tweet2.link_url is None:
        print("   ✅ 无链接情况处理正确")
        result2 = True
    else:
        print("   ❌ 无链接情况处理失败")
        result2 = False
    
    return result1 and result2


def test_database_integration():
    """测试数据库集成"""
    print(f"\n💾 测试数据库集成")
    print("=" * 60)
    
    try:
        from src.database.tweet_dao import tweet_dao
        from src.models.tweet import Tweet
        from datetime import datetime
        
        # 创建测试推文
        test_tweet = Tweet(
            id_str="test_link_extraction_123",
            full_text="测试链接提取功能",
            created_at_datetime=datetime.now(),
            link_url="https://test.com/extracted-link"
        )
        
        print("1. 创建测试推文对象")
        print(f"   推文ID: {test_tweet.id_str}")
        print(f"   链接URL: {test_tweet.link_url}")
        
        # 转换为字典格式
        tweet_dict = test_tweet.to_dict()
        
        print(f"\n2. 转换为数据库格式")
        print(f"   包含link_url字段: {'link_url' in tweet_dict}")
        print(f"   link_url值: {tweet_dict.get('link_url')}")
        
        if 'link_url' in tweet_dict and tweet_dict['link_url'] == "https://test.com/extracted-link":
            print("   ✅ 数据库字段映射正确")
            return True
        else:
            print("   ❌ 数据库字段映射失败")
            return False
            
    except Exception as e:
        print(f"   ❌ 数据库集成测试失败: {e}")
        return False


def main():
    """主函数"""
    print("🧪 entities字段链接提取功能测试")
    print("=" * 80)
    
    tests = [
        ("链接提取逻辑", test_link_extraction),
        ("Tweet对象创建", test_tweet_creation_with_entities),
        ("数据库集成", test_database_integration)
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
        print("🎉 所有测试通过！entities链接提取功能正常")
        return True
    else:
        print("⚠️ 部分测试失败，请检查功能实现")
        return False


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)