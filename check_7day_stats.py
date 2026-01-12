import pymysql
import sys
from datetime import datetime, timedelta

# 配置信息
config = {
    'host': '35.215.99.34',
    'port': 13216,
    'user': 'tele',
    'password': 'tele_sb268fg@cg5wH9dgW',
    'database': 'public_data',
    'charset': 'utf8mb4'
}

table_name = 'twitter_tweet_back_test_cmc300'

def run_check():
    try:
        print(f"正在连接数据库 {config['host']}...")
        conn = pymysql.connect(**config)
        cursor = conn.cursor()
        
        # 计算7天前的时间
        seven_days_ago = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d %H:%M:%S')
        print(f"统计时间起点: {seven_days_ago} (UTC/服务器时间)")
        
        # 1. 统计总量
        sql_total = f"SELECT count(*) FROM {table_name} WHERE created_at_datetime >= %s"
        cursor.execute(sql_total, (seven_days_ago,))
        total_count = cursor.fetchone()[0]
        
        print("-" * 40)
        print(f"【过去 7 天文总量】: {total_count} 条")
        print("-" * 40)
        
        # 2. 按天统计
        sql_daily = f"""
            SELECT DATE(created_at_datetime) as stat_date, count(*) as cnt
            FROM {table_name}
            WHERE created_at_datetime >= %s
            GROUP BY stat_date
            ORDER BY stat_date DESC
        """
        cursor.execute(sql_daily, (seven_days_ago,))
        results = cursor.fetchall()
        
        print("【每日分布详情】:")
        print(f"{'日期':<15} | {'数量':<10}")
        print("-" * 30)
        
        for row in results:
            date_str = str(row[0])
            count = row[1]
            print(f"{date_str:<15} | {count:<10}")
            
        print("-" * 30)
        
        # 3. 成本预估
        # 假设 API 成本 $0.15 / 1000 tweets
        estimated_cost = (total_count / 1000) * 0.15
        print(f"【API 成本预估】")
        print(f"按总量 {total_count} 条计算 (假设 $0.15/1000条):")
        print(f"预计单次全量更新成本: ${estimated_cost:.4f} USD")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"发生错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    run_check()
