#!/usr/bin/env python3
"""
测试用户语言检测功能
"""
import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.database.tweet_dao import tweet_dao
from src.utils.language_detector import get_language_detector
from src.utils.logger import setup_logger


def test_language_detection_basic():
    """测试基础语言检测功能"""
    print("🔤 测试基础语言检测")
    print("-" * 40)
    
    language_detector = get_language_detector(tweet_dao.db_manager)
    
    # 测试文本样本
    test_texts = [
        ("Hello, this is a test message in English.", "English"),
        ("这是一条中文测试消息，包含中文字符。", "Chinese"),
        ("Bitcoin price is going up! 🚀", "English"),
        ("比特币价格上涨了！很不错的表现。", "Chinese"),
        ("BTC to the moon! Let's go crypto!", "English"),
        ("加密货币市场今天表现很好，特别是BTC", "Chinese"),
        ("Mixed text: 这里有中文 and English words", "Chinese"),  # 混合文本，中文占比高
        ("Mostly English with 一些 Chinese words", "English"),  # 混合文本，英文占比高
        ("", "English"),  # 空文本，默认英文
        ("123456 !@#$%", "English"),  # 特殊字符，默认英文
    ]
    
    correct = 0
    total = len(test_texts)
    
    for text, expected in test_texts:
        result = language_detector._detect_text_language(text)
        status = "✅" if result == expected else "❌"
        print(f"{status} '{text[:30]}...' -> {result} (期望: {expected})")
        if result == expected:
            correct += 1
    
    accuracy = correct / total * 100
    print(f"\n📊 基础检测准确率: {correct}/{total} ({accuracy:.1f}%)")
    
    return accuracy >= 80  # 期望准确率80%以上


def test_user_language_detection():
    """测试用户语言检测"""
    print("\n👤 测试用户语言检测")
    print("-" * 40)
    
    try:
        language_detector = get_language_detector(tweet_dao.db_manager)
        
        # 1. 查找一些有推文的用户进行测试
        sample_sql = """
        SELECT DISTINCT u.id_str, u.screen_name, u.description,
               COUNT(t.id_str) as tweet_count
        FROM twitter_user u
        INNER JOIN twitter_tweet t ON u.id_str = t.kol_id
        WHERE t.full_text IS NOT NULL
        AND LENGTH(t.full_text) > 20
        GROUP BY u.id_str, u.screen_name, u.description
        HAVING tweet_count >= 3
        ORDER BY tweet_count DESC
        LIMIT 5
        """
        
        sample_users = tweet_dao.db_manager.execute_query(sample_sql)
        
        if not sample_users:
            print("❌ 没有找到足够的用户样本")
            return False
        
        print(f"📋 测试用户样本 ({len(sample_users)} 个):")
        
        success_count = 0
        
        for user in sample_users:
            user_id = user['id_str']
            screen_name = user['screen_name']
            description = user.get('description', '')
            tweet_count = user['tweet_count']
            
            try:
                # 检测语言
                detected_language = language_detector.detect_user_language(
                    user_id=user_id,
                    user_description=description,
                    recent_days=30,
                    min_tweets=2
                )
                
                print(f"✅ {screen_name} ({user_id}): {detected_language} ({tweet_count} 条推文)")
                if description:
                    desc_preview = description[:60] + "..." if len(description) > 60 else description
                    print(f"   描述: {desc_preview}")
                
                success_count += 1
                
            except Exception as e:
                print(f"❌ {screen_name} ({user_id}): 检测失败 - {e}")
        
        success_rate = success_count / len(sample_users) * 100
        print(f"\n📊 用户检测成功率: {success_count}/{len(sample_users)} ({success_rate:.1f}%)")
        
        return success_count > 0
        
    except Exception as e:
        print(f"❌ 用户语言检测测试失败: {e}")
        return False


def test_chinese_ratio_calculation():
    """测试中文字符比例计算"""
    print("\n🔢 测试中文字符比例计算")
    print("-" * 40)
    
    language_detector = get_language_detector()
    
    test_cases = [
        ("这是纯中文文本", 1.0),
        ("This is pure English text", 0.0),
        ("混合 mixed 文本 text", 0.5),  # 4个中文字符，4个英文字符
        ("Bitcoin 比特币 price 价格", 0.5),  # 4个中文，4个英文
        ("主要是中文内容，with some English", 0.64),  # 约64%中文
        ("Mostly English content，加一些中文", 0.27),  # 约27%中文
        ("", 0.0),
        ("123!@#", 0.0),
    ]
    
    passed = 0
    
    for text, expected_ratio in test_cases:
        actual_ratio = language_detector._calculate_chinese_ratio(text)
        tolerance = 0.1  # 10%容差
        
        if abs(actual_ratio - expected_ratio) <= tolerance:
            status = "✅"
            passed += 1
        else:
            status = "❌"
        
        print(f"{status} '{text}' -> {actual_ratio:.2f} (期望: {expected_ratio:.2f})")
    
    accuracy = passed / len(test_cases) * 100
    print(f"\n📊 中文比例计算准确率: {passed}/{len(test_cases)} ({accuracy:.1f}%)")
    
    return accuracy >= 70


def test_batch_detection():
    """测试批量检测"""
    print("\n📦 测试批量语言检测")
    print("-" * 40)
    
    try:
        language_detector = get_language_detector(tweet_dao.db_manager)
        
        # 获取一些用户ID进行批量测试
        sample_sql = """
        SELECT DISTINCT kol_id
        FROM twitter_tweet
        WHERE kol_id IS NOT NULL
        AND full_text IS NOT NULL
        LIMIT 5
        """
        
        user_results = tweet_dao.db_manager.execute_query(sample_sql)
        
        if not user_results:
            print("❌ 没有找到测试用户")
            return False
        
        user_ids = [result['kol_id'] for result in user_results]
        
        # 批量检测
        batch_results = language_detector.batch_detect_user_languages(user_ids)
        
        print(f"📊 批量检测结果 ({len(batch_results)} 个用户):")
        for user_id, language in batch_results.items():
            print(f"  {user_id}: {language}")
        
        return len(batch_results) == len(user_ids)
        
    except Exception as e:
        print(f"❌ 批量检测测试失败: {e}")
        return False


def main():
    """主测试函数"""
    setup_logger()
    
    print("🧪 用户语言检测功能测试")
    print("=" * 60)
    
    tests = [
        ("基础语言检测", test_language_detection_basic),
        ("中文比例计算", test_chinese_ratio_calculation),
        ("用户语言检测", test_user_language_detection),
        ("批量语言检测", test_batch_detection),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n{'='*60}")
        print(f"🧪 {test_name}")
        print("="*60)
        
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
    
    print(f"\n{'='*60}")
    print("🎯 测试总结")
    print("="*60)
    print(f"✅ 通过测试: {passed}/{total}")
    print(f"📊 通过率: {passed/total*100:.1f}%")
    
    if passed == total:
        print("🎉 所有测试通过！语言检测功能正常")
        return True
    else:
        print("⚠️ 部分测试失败，请检查功能实现")
        return False


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)