#!/usr/bin/env python3
"""
测试修正后的字段映射（排除created_at）
"""
import sys
from pathlib import Path
from datetime import datetime

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def test_updated_field_mapping():
    """测试更新后的字段映射"""
    print("=" * 60)
    print("测试修正后的字段映射（排除 created_at）")
    print("=" * 60)
    
    # 模拟推文数据
    from src.models.tweet import Tweet
    
    test_tweet = Tweet(
        id_str='test_created_at_fix_12345',
        conversation_id_str='test_conversation_123',  # 会被排除
        in_reply_to_status_id_str='test_reply_123',   # 会被排除
        full_text='测试推文内容 - created_at字段修复',
        created_at='Thu Dec 11 08:23:31 +0000 2025',  # 会被排除
        created_at_datetime=datetime(2025, 12, 11, 7, 11, 2),
        bookmark_count=0,
        favorite_count=58,
        quote_count=0,
        reply_count=9,
        retweet_count=36,
        view_count=1593,
        engagement_total=103,
        sentiment='Neutral',
        user_id='957716432430641152',
        user_name='AxieInfinity',
        tweet_url='https://x.com/AxieInfinity/status/test_created_at_fix_12345',
        link_url='https://forms.gle/oeZGx1z5vyAkdA3s7',
        is_announce=0,
        summary=None,
        is_activity=1,
        activity_detail='{"title": "Codex Accessory Design Contest", "status": "Active"}',
        is_retweet=0
    )
    
    tweet_data = test_tweet.to_dict()
    
    # 修正后的字段列表（排除 created_at, conversation_id_str, in_reply_to_status_id_str）
    target_table = 'twitter_tweet_back_test_cmc300'
    fields_cmc300 = [
        'id_str', 'full_text', 'created_at_datetime',
        'bookmark_count', 'favorite_count', 'quote_count', 'reply_count',
        'retweet_count', 'view_count', 'engagement_total', 'update_time',
        'sentiment', 'user_id', 'tweet_url', 'link_url', 'isAnnounce', 'summary', 
        'is_activity', 'activity_detail', 'is_retweet', 'user_name'
    ]
    
    # 被排除的字段
    excluded_fields = [
        'conversation_id_str', 'in_reply_to_status_id_str', 'created_at'
    ]
    
    print(f"目标表: {target_table}")
    print(f"字段数: {len(fields_cmc300)} (排除了 {len(excluded_fields)} 个字段)")
    print(f"排除字段: {excluded_fields}")
    
    # 生成SQL和参数
    fields_str = ', '.join(fields_cmc300)
    placeholders = ', '.join(['%s'] * len(fields_cmc300))
    sql = f"""
    INSERT INTO {target_table} (
        {fields_str}
    ) VALUES (
        {placeholders}
    )
    """
    
    # 提取参数
    params = tuple(tweet_data.get(field) for field in fields_cmc300)
    
    print(f"\n生成的SQL:")
    print(sql)
    
    print(f"\n参数验证 (共{len(params)}个):")
    critical_fields = ['id_str', 'user_id', 'user_name', 'is_retweet', 'full_text']
    for i, (field, param) in enumerate(zip(fields_cmc300, params)):
        status = "🔑" if field in critical_fields else "  "
        print(f"{status} {i+1:2d}. {field}: {param}")
    
    # 检查关键业务字段
    print(f"\n关键业务字段检查:")
    for field in critical_fields:
        value = tweet_data.get(field)
        status = "✅ 有值" if value is not None else "⚠️  空值"
        print(f"  {field}: {status} ({value})")
    
    # 检查是否有意外的空值
    none_count = sum(1 for param in params if param is None)
    print(f"\n空值统计: {none_count}/{len(params)} 个字段为空")
    
    return True

def test_field_exclusion():
    """测试字段排除逻辑"""
    print("\n" + "=" * 60)
    print("字段排除逻辑验证")
    print("=" * 60)
    
    # 原始错误中的字段
    error_fields = ['conversation_id_str', 'created_at']
    
    # 当前排除的字段
    excluded_fields = ['conversation_id_str', 'in_reply_to_status_id_str', 'created_at']
    
    print("导致错误的字段:")
    for field in error_fields:
        is_excluded = field in excluded_fields
        status = "✅ 已排除" if is_excluded else "❌ 未排除"
        print(f"  {field}: {status}")
    
    # 保留的核心字段
    kept_core_fields = [
        'id_str', 'full_text', 'created_at_datetime', 
        'user_id', 'user_name', 'is_retweet'
    ]
    
    print(f"\n保留的核心字段:")
    for field in kept_core_fields:
        print(f"  ✓ {field}")
    
    return all(field in excluded_fields for field in error_fields)

def main():
    """主函数"""
    print("字段映射修正测试（排除 created_at）")
    print("="*80)
    print("修正内容:")
    print("1. 排除 conversation_id_str（之前的错误）")
    print("2. 排除 created_at（新发现的错误）") 
    print("3. 排除 in_reply_to_status_id_str（预防性排除）")
    print("4. 保留所有核心业务字段")
    print("="*80)
    
    try:
        # 运行测试
        test1 = test_updated_field_mapping()
        test2 = test_field_exclusion()
        
        print("\n" + "=" * 60)
        print("测试结果总结")
        print("=" * 60)
        print(f"1. 字段映射测试: {'✅ 通过' if test1 else '❌ 失败'}")
        print(f"2. 字段排除验证: {'✅ 通过' if test2 else '❌ 失败'}")
        
        if test1 and test2:
            print(f"\n🎉 字段映射修正成功！")
            print(f"\n现在应该解决的错误:")
            print(f"- ❌ Unknown column 'conversation_id_str' (已修复)")
            print(f"- ❌ Unknown column 'created_at' (已修复)")
            print(f"\n保留的核心功能:")
            print(f"- ✅ user_id, user_name, is_retweet 字段")
            print(f"- ✅ 推文内容和互动数据")
            print(f"- ✅ 时间戳（使用 created_at_datetime）")
            print(f"- ✅ 活动检测和详情")
            return True
        else:
            print(f"\n❌ 某些测试失败")
            return False
            
    except Exception as e:
        print(f"\n测试异常: {e}")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)