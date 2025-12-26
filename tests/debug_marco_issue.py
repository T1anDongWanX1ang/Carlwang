#!/usr/bin/env python3
"""
调试Marco数据生成问题
"""
import sys
import os
from datetime import datetime, timedelta

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.database.tweet_dao import tweet_dao
from src.utils.logger import setup_logger


def check_tweet_data_in_timerange():
    """检查指定时间范围内的推文数据"""
    setup_logger()
    
    print("🔍 检查Marco时间范围内的推文数据")
    print("=" * 60)
    
    # Marco日志显示的时间范围: 2025-09-11 16:30:00 到 2025-09-11 20:30:00
    start_time = "2025-09-11 16:30:00"
    end_time = "2025-09-11 20:30:00"
    
    print(f"📊 检查时间范围: {start_time} 到 {end_time}")
    
    try:
        db_manager = tweet_dao.db_manager
        
        # 1. 检查总推文数量
        total_sql = """
        SELECT COUNT(*) as total_count
        FROM twitter_tweet
        WHERE created_at >= %s AND created_at <= %s
        """
        
        total_result = db_manager.execute_query(total_sql, [start_time, end_time])
        total_count = total_result[0]['total_count'] if total_result else 0
        
        print(f"📊 时间范围内总推文数: {total_count}")
        
        # 2. 检查KOL推文数量
        kol_sql = """
        SELECT COUNT(*) as kol_count
        FROM twitter_tweet
        WHERE created_at >= %s AND created_at <= %s
        AND kol_id IS NOT NULL AND kol_id != ''
        """
        
        kol_result = db_manager.execute_query(kol_sql, [start_time, end_time])
        kol_count = kol_result[0]['kol_count'] if kol_result else 0
        
        print(f"📊 时间范围内KOL推文数: {kol_count}")
        
        # 3. 检查推文样本
        if total_count > 0:
            print(f"\n📋 推文样本 (前5条):")
            sample_sql = """
            SELECT id_str, created_at, kol_id, full_text
            FROM twitter_tweet
            WHERE created_at >= %s AND created_at <= %s
            ORDER BY created_at DESC
            LIMIT 5
            """
            
            samples = db_manager.execute_query(sample_sql, [start_time, end_time])
            
            if samples:
                for i, tweet in enumerate(samples, 1):
                    kol_status = f"KOL:{tweet['kol_id']}" if tweet['kol_id'] else "非KOL"
                    print(f"   {i}. [{tweet['created_at']}] [{kol_status}]")
                    print(f"      ID: {tweet['id_str']}")
                    print(f"      内容: {tweet['full_text'][:60]}...")
                    print()
        
        # 4. 检查Marco处理器可能使用的查询逻辑
        print(f"4️⃣ 检查Marco处理器查询逻辑")
        print("-" * 40)
        
        # 检查created_at_datetime字段（如果存在）
        datetime_sql = """
        SELECT COUNT(*) as datetime_count
        FROM twitter_tweet
        WHERE created_at_datetime >= %s AND created_at_datetime <= %s
        """
        
        try:
            datetime_result = db_manager.execute_query(datetime_sql, [start_time, end_time])
            datetime_count = datetime_result[0]['datetime_count'] if datetime_result else 0
            print(f"📊 使用created_at_datetime字段的推文数: {datetime_count}")
        except Exception as e:
            print(f"⚠️ created_at_datetime字段可能不存在或格式不同: {e}")
        
        # 5. 检查时区问题
        print(f"\n5️⃣ 检查时区和时间格式问题")
        print("-" * 40)
        
        # 查看实际的created_at值格式
        format_sql = """
        SELECT created_at, created_at_datetime
        FROM twitter_tweet
        ORDER BY created_at DESC
        LIMIT 3
        """
        
        format_samples = db_manager.execute_query(format_sql)
        
        if format_samples:
            print(f"📅 时间字段格式样本:")
            for sample in format_samples:
                print(f"   created_at: {sample.get('created_at')} (类型: {type(sample.get('created_at'))})")
                if 'created_at_datetime' in sample:
                    print(f"   created_at_datetime: {sample.get('created_at_datetime')} (类型: {type(sample.get('created_at_datetime'))})")
                print()
        
        # 6. 尝试不同的时间查询方式
        print(f"6️⃣ 尝试不同的时间查询方式")
        print("-" * 40)
        
        # 尝试更宽泛的时间范围
        broad_sql = """
        SELECT COUNT(*) as broad_count
        FROM twitter_tweet
        WHERE DATE(created_at) = '2025-09-11'
        """
        
        broad_result = db_manager.execute_query(broad_sql)
        broad_count = broad_result[0]['broad_count'] if broad_result else 0
        
        print(f"📊 2025-09-11整天的推文数: {broad_count}")
        
        # 检查最近4小时的推文
        recent_sql = """
        SELECT COUNT(*) as recent_count
        FROM twitter_tweet
        WHERE created_at >= DATE_SUB(NOW(), INTERVAL 4 HOUR)
        """
        
        recent_result = db_manager.execute_query(recent_sql)
        recent_count = recent_result[0]['recent_count'] if recent_result else 0
        
        print(f"📊 最近4小时的推文数: {recent_count}")
        
        # 7. 分析问题
        print(f"\n7️⃣ 问题分析")
        print("-" * 40)
        
        if total_count == 0 and broad_count > 0:
            print("❌ 问题：时间范围查询有问题，可能是时区或格式问题")
        elif total_count == 0 and recent_count > 0:
            print("❌ 问题：指定时间范围内确实没有推文，但最近有推文")
        elif total_count > 0 and kol_count == 0:
            print("⚠️ 问题：有推文但没有KOL推文，Marco可能需要KOL推文")
        elif total_count > 0 and kol_count > 0:
            print("✅ 数据正常：有推文也有KOL推文，问题可能在Marco处理逻辑")
        else:
            print("❌ 问题：指定时间范围内确实没有推文数据")
        
        return {
            'total_count': total_count,
            'kol_count': kol_count,
            'broad_count': broad_count,
            'recent_count': recent_count
        }
        
    except Exception as e:
        print(f"❌ 检查异常: {e}")
        import traceback
        traceback.print_exc()
        return None


def check_marco_processor_logic():
    """检查Marco处理器的查询逻辑"""
    print(f"\n🔧 检查Marco处理器逻辑")
    print("-" * 40)
    
    try:
        # 查找Marco处理器文件
        marco_files = []
        for root, dirs, files in os.walk("/Users/qmk/Documents/code/twitter-data-product/twitter-crawler/src"):
            for file in files:
                if "marco" in file.lower():
                    marco_files.append(os.path.join(root, file))
        
        if marco_files:
            print(f"📁 找到Marco相关文件:")
            for file in marco_files:
                print(f"   {file}")
            
            # 建议检查第一个文件
            if marco_files:
                print(f"\n💡 建议检查文件: {marco_files[0]}")
                print("   特别关注推文查询的时间字段和条件")
        else:
            print("❌ 没有找到Marco处理器文件")
        
    except Exception as e:
        print(f"❌ 检查Marco文件异常: {e}")


def main():
    """主函数"""
    print("🚨 Marco数据生成失败 - 调试分析")
    print("=" * 80)
    
    # 检查推文数据
    data_status = check_tweet_data_in_timerange()
    
    # 检查Marco处理器
    check_marco_processor_logic()
    
    # 总结建议
    print(f"\n💡 调试建议")
    print("=" * 80)
    
    if data_status:
        if data_status['total_count'] == 0:
            print("1. 检查Marco处理器中的时间字段是否正确（created_at vs created_at_datetime）")
            print("2. 检查时区处理逻辑")
            print("3. 检查时间格式转换")
        
        if data_status['kol_count'] == 0:
            print("4. 检查Marco是否必须需要KOL推文")
            print("5. 如果需要KOL推文，检查kol_id字段的设置逻辑")
        
        if data_status['total_count'] > 0:
            print("6. 检查Marco处理器的其他过滤条件（如is_valid等）")
            print("7. 检查Marco处理器的数据库连接和查询语句")
    
    print("8. 建议运行Marco处理器的调试模式（如果有）")
    print("9. 检查Marco处理器的日志输出详情")


if __name__ == '__main__':
    main()