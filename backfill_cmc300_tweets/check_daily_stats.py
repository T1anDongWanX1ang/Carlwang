#!/usr/bin/env python3
import sys
from pathlib import Path
parent_dir = Path(__file__).parent.parent
sys.path.insert(0, str(parent_dir))

from src.database.connection import db_manager
from datetime import datetime, timedelta

with db_manager.get_cursor() as (conn, cursor):
    # 查询每天的推文数量 (使用 created_at_datetime)
    query = """
    SELECT
        DATE(created_at_datetime) as date,
        COUNT(*) as count
    FROM twitter_tweet_back_test_cmc300
    WHERE created_at_datetime >= '2025-12-22'
    GROUP BY DATE(created_at_datetime)
    ORDER BY date DESC
    """
    cursor.execute(query)
    results = cursor.fetchall()
    
    print('📅 CMC300表数据分布 (从2025-12-22开始):')
    print('=' * 70)
    
    dates_with_data = []
    if results:
        for row in results:
            if isinstance(row, dict):
                date = row['date']
                count = row['count']
            else:
                date = row[0]
                count = row[1]
            
            dates_with_data.append(str(date))
            print(f'{date}: {count:>5,} 条')
    else:
        print('❌ 无数据')
    
    print('=' * 70)
    
    # 查询总体统计
    query2 = """
    SELECT
        COUNT(*) as total,
        MIN(DATE(created_at_datetime)) as earliest_date,
        MAX(DATE(created_at_datetime)) as latest_date,
        COUNT(DISTINCT DATE(created_at_datetime)) as days
    FROM twitter_tweet_back_test_cmc300
    WHERE created_at_datetime >= '2025-12-22'
    """
    cursor.execute(query2)
    summary = cursor.fetchone()
    
    if summary:
        if isinstance(summary, dict):
            total = summary["total"]
            earliest_date = summary["earliest_date"]
            latest_date = summary["latest_date"]
            days = summary["days"]
        else:
            total = summary[0]
            earliest_date = summary[1]
            latest_date = summary[2]
            days = summary[3]
        
        print(f'\n📊 总计: {total:,} 条')
        print(f'📆 覆盖天数: {days} 天')
        print(f'⏰ 日期范围: {earliest_date} 至 {latest_date}')
        
        # 分析缺失的日期
        print('\n🔍 分析缺失日期...')
        start_date = datetime.strptime('2025-12-22', '%Y-%m-%d').date()
        end_date = datetime.now().date()
        
        missing_dates = []
        current_date = start_date
        while current_date <= end_date:
            if str(current_date) not in dates_with_data:
                missing_dates.append(str(current_date))
            current_date += timedelta(days=1)
        
        if missing_dates:
            print(f'\n❌ 缺失的日期 ({len(missing_dates)} 天):')
            for date in missing_dates:
                print(f'   - {date}')
            
            # 建议回填命令
            if len(missing_dates) > 0:
                first_missing = missing_dates[0]
                last_missing = missing_dates[-1]
                print(f'\n💡 建议使用以下命令回填:')
                print(f'   python backfill_project_tweets_sinceTime.py --start-date {first_missing} --end-date {last_missing}')
        else:
            print('\n✅ 没有缺失日期！')
    
    # 查询所有数据的时间范围
    query3 = """
    SELECT
        COUNT(*) as total,
        MIN(created_at_datetime) as earliest,
        MAX(created_at_datetime) as latest
    FROM twitter_tweet_back_test_cmc300
    """
    cursor.execute(query3)
    all_data = cursor.fetchone()
    
    if all_data:
        if isinstance(all_data, dict):
            total = all_data["total"]
            earliest = all_data["earliest"]
            latest = all_data["latest"]
        else:
            total = all_data[0]
            earliest = all_data[1]
            latest = all_data[2]
        
        print(f'\n📋 表中所有数据:')
        print(f'   总计: {total:,} 条')
        print(f'   最早: {earliest}')
        print(f'   最新: {latest}')
