#!/usr/bin/env python3
"""
调试Marco处理器的具体查询条件
"""
import sys
import os
from datetime import datetime, timedelta

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.database.tweet_dao import tweet_dao
from src.utils.logger import setup_logger


def check_marco_query_conditions():
    """检查Marco查询的所有条件"""
    setup_logger()
    
    print("🔍 检查Marco查询条件")
    print("=" * 60)
    
    # Marco的时间范围
    start_time = "2025-09-11 16:30:00"
    end_time = "2025-09-11 20:30:00"
    
    print(f"📊 Marco时间范围: {start_time} 到 {end_time}")
    
    try:
        db_manager = tweet_dao.db_manager
        
        # 1. 检查基础推文数量
        print(f"\n1️⃣ 逐步检查查询条件")
        print("-" * 40)
        
        # 基础推文
        base_sql = """
        SELECT COUNT(*) as count
        FROM twitter_tweet
        """
        
        base_result = db_manager.execute_query(base_sql)[0]['count']
        print(f"📊 数据库总推文数: {base_result}")
        
        # 有full_text的推文
        text_sql = """
        SELECT COUNT(*) as count
        FROM twitter_tweet
        WHERE full_text IS NOT NULL
        """
        
        text_result = db_manager.execute_query(text_sql)[0]['count']
        print(f"📊 有full_text的推文: {text_result}")
        
        # 长度>20的推文
        length_sql = """
        SELECT COUNT(*) as count
        FROM twitter_tweet
        WHERE full_text IS NOT NULL
        AND LENGTH(full_text) > 20
        """
        
        length_result = db_manager.execute_query(length_sql)[0]['count']
        print(f"📊 长度>20的推文: {length_result}")
        
        # 有kol_id的推文
        kol_sql = """
        SELECT COUNT(*) as count
        FROM twitter_tweet
        WHERE full_text IS NOT NULL
        AND LENGTH(full_text) > 20
        AND kol_id IS NOT NULL
        """
        
        kol_result = db_manager.execute_query(kol_sql)[0]['count']
        print(f"📊 有kol_id的推文: {kol_result}")
        
        # 检查is_valid字段
        print(f"\n2️⃣ 检查is_valid字段")
        print("-" * 40)
        
        try:
            valid_sql = """
            SELECT 
                COUNT(*) as total,
                COUNT(CASE WHEN is_valid = 1 THEN 1 END) as valid_count,
                COUNT(CASE WHEN is_valid IS NULL THEN 1 END) as null_count,
                COUNT(CASE WHEN is_valid = 0 THEN 1 END) as invalid_count
            FROM twitter_tweet
            WHERE full_text IS NOT NULL
            AND LENGTH(full_text) > 20
            AND kol_id IS NOT NULL
            """
            
            valid_result = db_manager.execute_query(valid_sql)[0]
            print(f"📊 is_valid字段统计:")
            print(f"   总数: {valid_result['total']}")
            print(f"   is_valid=1: {valid_result['valid_count']}")
            print(f"   is_valid=NULL: {valid_result['null_count']}")
            print(f"   is_valid=0: {valid_result['invalid_count']}")
            
        except Exception as e:
            print(f"❌ is_valid字段检查失败: {e}")
            print("⚠️ is_valid字段可能不存在")
        
        # 3. 检查时间字段
        print(f"\n3️⃣ 检查时间字段问题")
        print("-" * 40)
        
        # 检查created_at_datetime的范围
        datetime_range_sql = """
        SELECT 
            MIN(created_at_datetime) as min_time,
            MAX(created_at_datetime) as max_time,
            COUNT(*) as total_with_datetime
        FROM twitter_tweet
        WHERE created_at_datetime IS NOT NULL
        """
        
        datetime_range = db_manager.execute_query(datetime_range_sql)[0]
        print(f"📅 created_at_datetime范围:")
        print(f"   最早: {datetime_range['min_time']}")
        print(f"   最晚: {datetime_range['max_time']}")
        print(f"   总数: {datetime_range['total_with_datetime']}")
        
        # 检查2025-09-11的推文
        today_sql = """
        SELECT 
            id_str, created_at_datetime, kol_id, is_valid
        FROM twitter_tweet
        WHERE DATE(created_at_datetime) = '2025-09-11'
        AND kol_id IS NOT NULL
        LIMIT 5
        """
        
        today_tweets = db_manager.execute_query(today_sql)
        
        if today_tweets:
            print(f"\n📋 2025-09-11的KOL推文样本:")
            for tweet in today_tweets:
                valid_status = f"valid:{tweet.get('is_valid')}" 
                print(f"   {tweet['id_str']} - {tweet['created_at_datetime']} - KOL:{tweet['kol_id']} - {valid_status}")
        else:
            print(f"\n❌ 2025-09-11没有找到KOL推文")
        
        # 4. 尝试Marco的完整查询（去掉时间限制）
        print(f"\n4️⃣ 尝试Marco的完整查询（无时间限制）")
        print("-" * 40)
        
        full_marco_sql = """
        SELECT COUNT(*) as count
        FROM twitter_tweet t
        LEFT JOIN twitter_user u ON t.kol_id = u.id_str
        WHERE t.full_text IS NOT NULL
        AND LENGTH(t.full_text) > 20
        AND t.kol_id IS NOT NULL
        """
        
        # 尝试不同的is_valid条件
        try:
            with_valid_sql = full_marco_sql + " AND t.is_valid = 1"
            with_valid_result = db_manager.execute_query(with_valid_sql)[0]['count']
            print(f"📊 完整条件+is_valid=1: {with_valid_result}")
        except:
            print(f"⚠️ is_valid=1 条件查询失败")
        
        try:
            without_valid_sql = full_marco_sql
            without_valid_result = db_manager.execute_query(without_valid_sql)[0]['count']
            print(f"📊 完整条件(无is_valid): {without_valid_result}")
        except Exception as e:
            print(f"❌ 查询失败: {e}")
        
        # 5. 问题总结
        print(f"\n5️⃣ 问题诊断")
        print("-" * 40)
        
        if kol_result == 0:
            print("❌ 核心问题：没有符合条件的KOL推文")
            print("   原因可能：")
            print("   1. kol_id字段没有正确设置")
            print("   2. 推文长度都<=20")
            print("   3. full_text字段为空")
        elif valid_result and valid_result['valid_count'] == 0:
            print("❌ 核心问题：is_valid字段都不等于1")
            print("   原因：推文的is_valid字段可能都是NULL或0")
        elif datetime_range['max_time'] and datetime_range['max_time'] < datetime.strptime(start_time, '%Y-%m-%d %H:%M:%S'):
            print("❌ 核心问题：最新推文时间早于Marco查询时间范围")
        else:
            print("⚠️ 问题可能在时间范围查询或其他条件组合")
        
    except Exception as e:
        print(f"❌ 检查异常: {e}")
        import traceback
        traceback.print_exc()


def suggest_fixes():
    """建议修复方案"""
    print(f"\n💡 修复建议")
    print("=" * 60)
    
    print("1. 如果is_valid字段问题：")
    print("   - 方案A: 修改Marco查询去掉is_valid=1条件")
    print("   - 方案B: 更新推文数据设置is_valid=1")
    print()
    
    print("2. 如果kol_id字段问题：")
    print("   - 检查推文enrichment流程是否正确设置了kol_id")
    print("   - 确认KOL识别逻辑是否正常工作")
    print()
    
    print("3. 如果时间范围问题：")
    print("   - 检查created_at_datetime字段的时区")
    print("   - 确认推文数据的实际时间范围")
    print()
    
    print("4. 临时解决方案：")
    print("   - 修改Marco查询条件，放宽限制")
    print("   - 使用较大的时间窗口进行测试")


def main():
    """主函数"""
    print("🚨 Marco查询条件调试")
    print("=" * 80)
    
    check_marco_query_conditions()
    suggest_fixes()


if __name__ == '__main__':
    main()