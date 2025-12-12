#!/usr/bin/env python3
"""
测试 is_retweet 字段映射是否正确工作
"""
import sys
from pathlib import Path
from datetime import datetime

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def test_retweet_detection():
    """测试转发推文检测"""
    print("=" * 60)
    print("测试转发推文检测逻辑")
    print("=" * 60)
    
    from src.models.tweet import Tweet
    
    # 测试案例1: 转发推文（有 retweeted_status）
    retweet_api_data = {
        'id_str': 'test_retweet_12345',
        'full_text': 'RT @original_user: 这是一条被转发的推文 https://example.com',
        'created_at': 'Thu Dec 11 08:23:31 +0000 2025',
        'favorite_count': 5,
        'retweet_count': 2,
        'retweeted_status': {  # 关键：存在 retweeted_status
            'id_str': 'original_12345',
            'full_text': '这是一条被转发的推文 https://example.com',
            'user': {
                'screen_name': 'original_user',
                'id_str': 'original_user_id'
            }
        },
        'user': {
            'id_str': 'retweeter_user_123',
            'screen_name': 'retweeter_user',
            'name': 'Retweeter User'
        }
    }
    
    # 测试案例2: 普通推文（无 retweeted_status）
    normal_api_data = {
        'id_str': 'test_normal_12345', 
        'full_text': '这是一条普通推文，不是转发',
        'created_at': 'Thu Dec 11 08:23:31 +0000 2025',
        'favorite_count': 10,
        'retweet_count': 3,
        'retweeted_status': None,  # 关键：retweeted_status 为 None
        'user': {
            'id_str': 'normal_user_123',
            'screen_name': 'normal_user',
            'name': 'Normal User'
        }
    }
    
    # 测试案例3: 普通推文（无 retweeted_status 字段）
    normal_api_data_no_field = {
        'id_str': 'test_normal_no_field_12345',
        'full_text': '这是一条普通推文，API中没有retweeted_status字段',
        'created_at': 'Thu Dec 11 08:23:31 +0000 2025',
        'favorite_count': 15,
        'retweet_count': 1,
        # 注意：这里完全没有 retweeted_status 字段
        'user': {
            'id_str': 'normal_user_456',
            'screen_name': 'normal_user_2',
            'name': 'Normal User 2'
        }
    }
    
    field_mapping = {
        'id_str': 'id_str',
        'full_text': 'full_text',
        'created_at': 'created_at',
        'favorite_count': 'favorite_count',
        'retweet_count': 'retweet_count'
    }
    
    # 测试转发推文检测
    print("测试案例1: 转发推文 (有 retweeted_status)")
    retweet_tweet = Tweet.from_api_data(retweet_api_data, field_mapping)
    print(f"  推文ID: {retweet_tweet.id_str}")
    print(f"  推文内容: {retweet_tweet.full_text}")
    print(f"  is_retweet: {retweet_tweet.is_retweet}")
    print(f"  tweet_type: {retweet_tweet.tweet_type}")
    print(f"  用户名: {retweet_tweet.user_name}")
    print(f"  预期: is_retweet=1, tweet_type=RETWEET")
    print(f"  结果: {'✅ 正确' if retweet_tweet.is_retweet == 1 and retweet_tweet.tweet_type == 'RETWEET' else '❌ 错误'}")
    
    print(f"\n测试案例2: 普通推文 (retweeted_status=None)")
    normal_tweet = Tweet.from_api_data(normal_api_data, field_mapping)
    print(f"  推文ID: {normal_tweet.id_str}")
    print(f"  推文内容: {normal_tweet.full_text}")
    print(f"  is_retweet: {normal_tweet.is_retweet}")
    print(f"  tweet_type: {normal_tweet.tweet_type}")
    print(f"  用户名: {normal_tweet.user_name}")
    print(f"  预期: is_retweet=0, tweet_type=ORIGINAL")
    print(f"  结果: {'✅ 正确' if normal_tweet.is_retweet == 0 and normal_tweet.tweet_type == 'ORIGINAL' else '❌ 错误'}")
    
    print(f"\n测试案例3: 普通推文 (无 retweeted_status 字段)")
    normal_tweet_no_field = Tweet.from_api_data(normal_api_data_no_field, field_mapping)
    print(f"  推文ID: {normal_tweet_no_field.id_str}")
    print(f"  推文内容: {normal_tweet_no_field.full_text}")
    print(f"  is_retweet: {normal_tweet_no_field.is_retweet}")
    print(f"  tweet_type: {normal_tweet_no_field.tweet_type}")
    print(f"  用户名: {normal_tweet_no_field.user_name}")
    print(f"  预期: is_retweet=0, tweet_type=ORIGINAL")
    print(f"  结果: {'✅ 正确' if normal_tweet_no_field.is_retweet == 0 and normal_tweet_no_field.tweet_type == 'ORIGINAL' else '❌ 错误'}")
    
    # 检查所有测试结果
    results = [
        retweet_tweet.is_retweet == 1 and retweet_tweet.tweet_type == 'RETWEET',
        normal_tweet.is_retweet == 0 and normal_tweet.tweet_type == 'ORIGINAL',
        normal_tweet_no_field.is_retweet == 0 and normal_tweet_no_field.tweet_type == 'ORIGINAL'
    ]
    
    return all(results)

def test_real_api_data_patterns():
    """测试真实API数据的模式"""
    print("\n" + "=" * 60)
    print("分析真实API数据模式")
    print("=" * 60)
    
    # 模拟真实的转发推文API数据（基于Twitter API v1.1格式）
    real_retweet_data = {
        'id_str': '1999032285325303819',
        'full_text': 'RT @POPCATSOLANA: A mystic pop in the midst 🐱🔮 https://pbs.twimg.com/media/G739JGjaMAMIR1p.jpg',
        'created_at': 'Thu Dec 11 08:23:31 +0000 2025',
        'retweeted_status': {  # 这个字段表示它是转发
            'id_str': 'original_pop_tweet_id',
            'full_text': 'A mystic pop in the midst 🐱🔮 https://pbs.twimg.com/media/G739JGjaMAMIR1p.jpg',
            'user': {
                'screen_name': 'POPCATSOLANA',
                'id_str': '1734808822168870912'
            }
        },
        'user': {
            'id_str': 'retweeter_123',
            'screen_name': 'retweeter_account',
            'name': 'Retweeter Account'
        }
    }
    
    # 模拟您看到的普通推文数据  
    real_normal_data = {
        'id_str': '1999014043143778336',
        'full_text': 'The Codex Accessory Design Contest ends tonight!\\n\\nDesign your own accessory...',
        'created_at': 'Thu Dec 11 07:11:02 +0000 2025',
        'retweeted_status': None,  # 或者完全没有这个字段
        'user': {
            'id_str': '957716432430641152',
            'screen_name': 'AxieInfinity',
            'name': 'Axie Infinity'
        }
    }
    
    from src.models.tweet import Tweet
    
    field_mapping = {
        'id_str': 'id_str',
        'full_text': 'full_text',
        'created_at': 'created_at'
    }
    
    print("真实转发数据测试:")
    real_retweet = Tweet.from_api_data(real_retweet_data, field_mapping)
    print(f"  推文内容: {real_retweet.full_text[:50]}...")
    print(f"  is_retweet: {real_retweet.is_retweet}")
    print(f"  用户名: {real_retweet.user_name}")
    print(f"  检测结果: {'✅ 检测为转发' if real_retweet.is_retweet == 1 else '❌ 未检测为转发'}")
    
    print(f"\n真实普通数据测试:")
    real_normal = Tweet.from_api_data(real_normal_data, field_mapping)
    print(f"  推文内容: {real_normal.full_text[:50]}...")
    print(f"  is_retweet: {real_normal.is_retweet}")
    print(f"  用户名: {real_normal.user_name}")
    print(f"  检测结果: {'✅ 检测为普通推文' if real_normal.is_retweet == 0 else '❌ 误检测为转发'}")
    
    return real_retweet.is_retweet == 1 and real_normal.is_retweet == 0

def check_api_data_structure():
    """检查API数据结构的可能问题"""
    print("\n" + "=" * 60)
    print("API数据结构分析")
    print("=" * 60)
    
    print("可能导致 is_retweet 都是 0 的原因:")
    print("1. API数据中没有 'retweeted_status' 字段")
    print("2. API数据中 'retweeted_status' 总是 None 或空")
    print("3. 字段映射逻辑没有被调用")
    print("4. TweetScout API的数据格式与Twitter原生API不同")
    
    print(f"\n检查逻辑:")
    print(f"  if api_data.get('retweeted_status') is not None:")
    print(f"      mapped_data['is_retweet'] = 1")
    print(f"  else:")
    print(f"      mapped_data['is_retweet'] = 0")
    
    print(f"\n调试建议:")
    print(f"  1. 在 Tweet.from_api_data() 方法中添加调试日志")
    print(f"  2. 检查实际API返回的 retweeted_status 字段值")
    print(f"  3. 检查 TweetScout API 文档确认转发推文标识")
    
    return True

def main():
    """主函数"""
    print("is_retweet 字段映射测试")
    print("="*80)
    print("测试目的: 检查转发推文检测逻辑是否正确工作")
    print("当前现象: 所有推文的 is_retweet 都是 0")
    print("="*80)
    
    try:
        # 运行测试
        test1 = test_retweet_detection()
        test2 = test_real_api_data_patterns()
        test3 = check_api_data_structure()
        
        print("\n" + "=" * 60)
        print("测试结果总结")
        print("=" * 60)
        print(f"1. 转发检测逻辑: {'✅ 正确' if test1 else '❌ 有问题'}")
        print(f"2. 真实数据模式: {'✅ 正确' if test2 else '❌ 有问题'}")
        print(f"3. 数据结构分析: {'✅ 完成' if test3 else '❌ 失败'}")
        
        if test1 and test2:
            print(f"\n🔍 检测逻辑正常，问题可能在于:")
            print(f"  1. TweetScout API 数据格式不包含 'retweeted_status' 字段")
            print(f"  2. 需要使用其他字段识别转发推文（如推文内容以'RT @'开头）")
            print(f"  3. 需要检查实际API返回数据的结构")
            
            print(f"\n📝 下一步调试建议:")
            print(f"  1. 添加调试日志查看API数据")
            print(f"  2. 检查 TweetScout API 文档")
            print(f"  3. 考虑使用文本模式检测转发（RT @开头）")
        else:
            print(f"\n❌ 检测逻辑有问题，需要修复")
        
        return test1 and test2
            
    except Exception as e:
        print(f"\n测试异常: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)